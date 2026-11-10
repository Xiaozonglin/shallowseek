"""词法检索模块（替代原 FAISS + BGE 向量检索）。

迁移背景
--------
项目不再加载任何本地神经网络模型。知识库检索与「教师权威答案」匹配改为
中文分词 + BM25 / 词元余弦相似度实现，完全运行在 CPU 与纯 Python 上。

- 索引由 ``backend/build_index.py`` 生成，默认写入 ``backend/bm25_index/index.json``；
- 索引文件包含切好的片段与分词结果，启动时只做 JSON 读取与 BM25 建表，毫秒级完成；
- ``jieba`` 缺失时自动退化为「CJK 单字 + 双字 + 英文词」的字符 n-gram 分词，保证脚本仍可运行。
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

try:  # jieba 在 requirements.txt 中；无网络/无依赖时退化为字符 n-gram
    import jieba

    jieba.setLogLevel(logging.WARNING)
    _HAS_JIEBA = True
except ImportError:  # pragma: no cover - 仅在没有安装 jieba 时触发
    jieba = None
    _HAS_JIEBA = False

INDEX_VERSION = 2
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_K = 3

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_WORD_RE = re.compile(r"[a-z][a-z0-9_+\-#.]*")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HTML_RE = re.compile(r"<[^>]+>")
_TOKEN_CHAR_RE = re.compile(r"[0-9a-z\u4e00-\u9fff]")

STOPWORDS = frozenset(
    {
        # 中文高频虚词 / 提问套话
        "的", "了", "和", "是", "在", "我", "你", "他", "她", "它", "我们", "你们", "他们",
        "这", "那", "这个", "那个", "一个", "什么", "怎么", "如何", "为什么", "请问", "一下",
        "可以", "吗", "呢", "吧", "啊", "呀", "与", "及", "或", "而", "但", "因为", "所以",
        "如果", "就", "都", "也", "还", "又", "很", "更", "最", "不", "没", "没有", "有",
        "会", "能", "要", "对", "从", "到", "为", "以", "于", "之", "其", "中", "上", "下",
        "后", "前", "等", "个", "里", "外", "把", "被", "让", "给", "着", "过", "得", "地",
        # 英文高频词
        "the", "a", "an", "of", "in", "on", "at", "is", "are", "was", "were", "be", "to",
        "and", "or", "for", "with", "as", "by", "from", "this", "that", "these", "those",
        "it", "its", "we", "you", "they", "he", "she", "i",
    }
)


# ========================== 文本清洗与分词 ==========================
def normalize_text(text: str) -> str:
    """去掉 Markdown 图片、链接语法与 HTML 标签，保留可检索文字。"""
    if not text:
        return ""
    text = _MD_IMAGE_RE.sub(" ", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _HTML_RE.sub(" ", text)
    return text


def cjk_bigrams(text: str) -> List[str]:
    """按连续中文段切双字，提升中文词法匹配召回。"""
    tokens: List[str] = []
    for chunk in _CJK_RE.findall(text):
        for index in range(len(chunk) - 1):
            tokens.append(chunk[index : index + 2])
    return tokens


def _fallback_tokens(text: str) -> List[str]:
    """无 jieba 时的退化分词：英文词 + 中文单字 + 中文双字。"""
    tokens = [word for word in _ASCII_WORD_RE.findall(text.lower()) if len(word) > 1]
    for chunk in _CJK_RE.findall(text):
        tokens.extend(chunk)
        tokens.extend(chunk[index : index + 2] for index in range(len(chunk) - 1))
    return tokens


def tokenize(text: str) -> List[str]:
    """分词入口：jieba 搜索模式分词 + 中文双字，过滤停用词与纯符号。"""
    if not text:
        return []

    text = normalize_text(text)
    if not text.strip():
        return []

    if _HAS_JIEBA:
        raw_tokens = jieba.lcut_for_search(text)
        tokens = [token.strip().lower() for token in raw_tokens if token.strip()]
        tokens.extend(cjk_bigrams(text))
    else:
        tokens = _fallback_tokens(text)

    result: List[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if len(token) > 40:
            continue
        if not _TOKEN_CHAR_RE.search(token):
            continue
        result.append(token)
    return result


# ========================== 文档分块 ==========================
def chunk_markdown(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """把 Markdown 正文切成带重叠的文本块。"""
    if not text:
        return []

    blocks: List[str] = []
    buffer = ""

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if buffer:
                blocks.append(buffer)
                buffer = ""
            continue
        if stripped.startswith("<!--"):
            continue
        if _MD_IMAGE_RE.fullmatch(stripped):
            continue
        if len(stripped) > chunk_size:  # 超长行（代码等）硬切
            if buffer:
                blocks.append(buffer)
                buffer = ""
            for start in range(0, len(stripped), chunk_size):
                blocks.append(stripped[start : start + chunk_size])
            continue
        if buffer and len(buffer) + 1 + len(stripped) > chunk_size:
            blocks.append(buffer)
            buffer = stripped
        else:
            buffer = f"{buffer}\n{stripped}" if buffer else stripped

    if buffer:
        blocks.append(buffer)

    chunks: List[str] = []
    previous_tail = ""
    for block in blocks:
        content = f"{previous_tail}\n{block}" if previous_tail else block
        if content.strip():
            chunks.append(content.strip())
        previous_tail = block[-overlap:] if overlap > 0 else ""
    return chunks


def _iter_markdown_files(docs_dir: str) -> Iterable[str]:
    for root, _dirs, files in os.walk(docs_dir):
        for name in sorted(files):
            if name.lower().endswith(".md"):
                yield os.path.join(root, name)


def build_chunks(
    docs_dir: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """遍历目录下所有 .md，返回 ``[{"text", "source", "chunk"}]``。"""
    chunks: List[Dict[str, Any]] = []
    docs_dir = os.path.abspath(docs_dir)

    for path in _iter_markdown_files(docs_dir):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            logger.warning("读取文档失败: %s", path)
            continue

        source = os.path.relpath(path, docs_dir).replace(os.sep, "/")
        for index, content in enumerate(chunk_markdown(text, chunk_size, overlap)):
            chunks.append({"text": content, "source": source, "chunk": index})

    return chunks


# ========================== BM25 ==========================
class BM25:
    """轻量 BM25（k1=1.5, b=0.75），实现与 rank_bm25 的结果口径一致。"""

    def __init__(self, tokenized_docs: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs = [Counter(tokens) for tokens in tokenized_docs]
        self.doc_len = [sum(freqs.values()) for freqs in self.doc_freqs]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.doc_count = len(self.doc_freqs)

        term_doc_freq: Counter = Counter()
        for freqs in self.doc_freqs:
            term_doc_freq.update(freqs.keys())

        self.idf = {
            term: math.log(1.0 + (self.doc_count - freq + 0.5) / (freq + 0.5))
            for term, freq in term_doc_freq.items()
        }

    def score(self, query_tokens: List[str], doc_index: int) -> float:
        freqs = self.doc_freqs[doc_index]
        doc_len = self.doc_len[doc_index] or 1
        avgdl = self.avgdl or 1.0
        total = 0.0

        for term in query_tokens:
            freq = freqs.get(term)
            if not freq:
                continue
            idf = self.idf.get(term)
            if idf is None:
                continue
            denominator = freq + self.k1 * (1.0 - self.b + self.b * doc_len / avgdl)
            total += idf * freq * (self.k1 + 1.0) / denominator
        return total

    def top_k(self, query_tokens: List[str], k: int) -> List[tuple]:
        if not query_tokens or not self.doc_freqs:
            return []
        scored = [(self.score(query_tokens, index), index) for index in range(self.doc_count)]
        scored.sort(reverse=True)
        return [(index, score) for score, index in scored[:k] if score > 0.0]


# ========================== 索引持久化与检索器 ==========================
def default_index_path() -> str:
    """默认索引路径: ``backend/bm25_index/index.json``。"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(backend_dir, "bm25_index", "index.json")


def save_index(chunks: List[Dict[str, Any]], path: str) -> None:
    payload = {
        "version": INDEX_VERSION,
        "tokenizer": "jieba" if _HAS_JIEBA else "char_ngram",
        "chunks": [{"text": item["text"], "source": item["source"]} for item in chunks],
        "tokens": [tokenize(item["text"]) for item in chunks],
    }
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


class LexicalRetriever:
    """BM25 检索器：加载索引后可对 query 取 top-k 片段。"""

    def __init__(self, chunks: List[Dict[str, Any]], bm25: BM25):
        self.chunks = chunks
        self.bm25 = bm25

    @classmethod
    def load(cls, path: Optional[str] = None) -> Optional["LexicalRetriever"]:
        path = path or default_index_path()
        if not os.path.exists(path):
            logger.warning(
                "未找到 BM25 索引（%s），知识库检索功能暂时关闭；"
                "可在 backend 目录运行 `python build_index.py` 生成。",
                path,
            )
            return None

        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            logger.exception("BM25 索引读取失败: %s", path)
            return None

        if payload.get("version") != INDEX_VERSION:
            logger.warning("BM25 索引版本不匹配（期望 %s，实际 %s），请重新运行 build_index.py 重建",
                           INDEX_VERSION, payload.get("version"))
            return None

        chunks = payload.get("chunks") or []
        tokens = payload.get("tokens") or []
        if not chunks or len(chunks) != len(tokens):
            logger.warning("BM25 索引内容不完整，请重新运行 build_index.py 重建")
            return None

        return cls(chunks, BM25(tokens))

    def search(self, query: str, k: int = DEFAULT_K) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        results: List[Dict[str, Any]] = []
        for index, score in self.bm25.top_k(query_tokens, k):
            chunk = self.chunks[index]
            results.append(
                {
                    "text": chunk.get("text", ""),
                    "source": chunk.get("source", ""),
                    "score": score,
                }
            )
        return results


def format_context(results: List[Dict[str, Any]]) -> str:
    """把检索结果拼成可注入 system prompt 的上下文文本。"""
    if not results:
        return ""
    sections = []
    for item in results:
        source = item.get("source") or "未知来源"
        sections.append(f"（来源: {source}）\n{item.get('text', '')}")
    return "\n【本地参考资料】:\n" + "\n---\n".join(sections)


# ========================== 短文本相似度（权威答案/邮件去重） ==========================
def _bigram_set(text: str) -> set:
    normalized = normalize_text(text)
    return {
        chunk[index : index + 2]
        for chunk in _CJK_RE.findall(normalized)
        for index in range(len(chunk) - 1)
    }


def text_similarity(text_a: str, text_b: str) -> float:
    """短文本相似度（0~1）：词元余弦与中文双字 Jaccard 取较大值。

    替代原 BGE embedding 余弦相似度，用于：
    1. 判断学生提问是否命中某条教师权威答案；
    2. 24 小时内留言去重，避免重复邮件骚扰。
    """
    if not text_a or not text_b:
        return 0.0

    tokens_a = Counter(tokenize(text_a))
    tokens_b = Counter(tokenize(text_b))
    cosine = 0.0
    if tokens_a and tokens_b:
        dot = sum(value * tokens_b.get(term, 0) for term, value in tokens_a.items())
        norm_a = math.sqrt(sum(value * value for value in tokens_a.values()))
        norm_b = math.sqrt(sum(value * value for value in tokens_b.values()))
        if norm_a and norm_b:
            cosine = dot / (norm_a * norm_b)

    grams_a = _bigram_set(text_a)
    grams_b = _bigram_set(text_b)
    jaccard = 0.0
    if grams_a and grams_b:
        union = grams_a | grams_b
        if union:
            jaccard = len(grams_a & grams_b) / len(union)

    return max(cosine, jaccard)
