"""构建知识库 BM25 词法索引（替代原 FAISS 向量索引）。

用法（在 backend 目录下）::

    python build_index.py
    python build_index.py --query 二分查找          # 构建后自检索，检查效果
    python build_index.py --docs-dir ../docs --out bm25_index/index.json

索引文件默认输出到 ``backend/bm25_index/index.json``（已加入 .gitignore），
可以随时删除重建；没有索引时服务仍可启动，只是知识库检索功能关闭。
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from modules import retrieval


def main() -> int:
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="构建知识库 BM25 词法索引")
    parser.add_argument("--docs-dir", default=os.path.join(backend_dir, "..", "docs"),
                        help="Markdown 知识库目录（默认仓库根 docs/）")
    parser.add_argument("--out", default=retrieval.default_index_path(),
                        help="索引输出路径（默认 backend/bm25_index/index.json）")
    parser.add_argument("--chunk-size", type=int, default=retrieval.DEFAULT_CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=retrieval.DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--query", default=None, help="可选：构建完成后立即用该问题做自检索")
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"[错误] 文档目录不存在: {docs_dir}")
        return 1

    started = time.time()
    chunks = retrieval.build_chunks(docs_dir, chunk_size=args.chunk_size, overlap=args.overlap)
    if not chunks:
        print(f"[错误] 在 {docs_dir} 下没有找到可索引的 .md 文档")
        return 1

    retrieval.save_index(chunks, args.out)
    elapsed = time.time() - started
    print(f"[完成] 共索引 {len(chunks)} 个片段，耗时 {elapsed:.1f}s")
    print(f"[完成] 索引文件: {os.path.abspath(args.out)}")

    if args.query:
        retriever = retrieval.LexicalRetriever.load(args.out)
        hits = retriever.search(args.query, k=3) if retriever else []
        print(f"\n[自检] 查询: {args.query}")
        if not hits:
            print("  未命中任何片段（换一个更具体的词试试）")
        for rank, hit in enumerate(hits, 1):
            snippet = hit["text"].replace("\n", " ")[:120]
            print(f"  {rank}. {hit['source']} (score={hit['score']:.2f}) {snippet}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
