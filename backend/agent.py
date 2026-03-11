from qwen_agent import Retrieval
from qwen_agent.agents import Assistant
import os

# 构建知识库
retrieve.build_index(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs"))

class DocQA(Assistant):
    def _preprocess(self, query):
        contexts = retrieve.search(query)
        return f"根据文档：{contexts}\n回答：{query}"

qa = DocQA(llm={'model': 'qwen-max-longcontext'})
qa.run("栈是什么？")