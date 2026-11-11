"""教师权威答案在快答/深度两条路径都必须生效。

覆盖：
1. 深度模式 system prompt 注入教师权威答案；
2. AgentRuntime 把 authority 上下文带进模型消息；
3. /api/qa 深度事件流发出命中状态、complete/done 标记并落库；
4. 快答事件流同样带命中标记。
"""

import json
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test")
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(tempfile.gettempdir(), 'xdwe-tests.db')}",
)

import main  # noqa: E402  (需要先设置环境变量)
from modules import agent_prompts  # noqa: E402
from modules.agent import AgentRuntime  # noqa: E402

AUTHORITY_TEXT = "\n【历史权威参考】来自张老师的解答：\n二分查找必须先保证数组有序，再折半比较。\n"


# ========================== 假模型 ==========================
def _text_chunk(text):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text, tool_calls=None))])


class _CaptureCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return iter([_text_chunk("好的。")])


class _FakeEngine:
    model = "fake-model"

    def __init__(self):
        self.retriever = None
        self.client = SimpleNamespace(chat=SimpleNamespace(completions=_CaptureCompletions()))

    def extra_body(self):
        return {}

    def safe_math(self, query):
        return ""

    def friendly_error(self, exc):
        return f"AI 服务调用失败：{exc}"


def _events(chunks):
    events = []
    for chunk in chunks:
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


class AuthorityPromptTest(unittest.TestCase):
    def test_prompt_contains_authority_block(self):
        prompt = agent_prompts.deep_system_prompt(ui_enabled=False, authoritative_context=AUTHORITY_TEXT)
        self.assertIn("教师权威答案", prompt)
        self.assertIn("二分查找必须先保证数组有序", prompt)

        plain = agent_prompts.deep_system_prompt(ui_enabled=False)
        self.assertNotIn("教师权威答案", plain)

    def test_runtime_injects_authority_into_system_message(self):
        engine = _FakeEngine()
        runtime = AgentRuntime(engine, max_rounds=1, timeout_seconds=30)
        list(runtime.run("二分查找怎么用？", ui_enabled=False, authoritative_context=AUTHORITY_TEXT))

        calls = engine.client.chat.completions.calls
        self.assertTrue(calls)
        system_content = calls[0]["messages"][0]["content"]
        self.assertIn("教师权威答案", system_content)
        self.assertIn("二分查找必须先保证数组有序", system_content)


class AuthorityStreamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.app.config["TESTING"] = True
        with main.app.app_context():
            main.ensure_schema()
            student = main.User.query.filter_by(username="authority_probe").first()
            if student is None:
                student = main.User(
                    username="authority_probe",
                    email="authority_probe@example.com",
                    password="x",
                    role="student",
                )
                main.db.session.add(student)
                main.db.session.commit()
            cls.student_id = student.id

    def setUp(self):
        self._original_authority = main.get_authoritative_context
        self._original_agent_run = main.agent_runtime.run
        self._original_stream_answer = main.ai.stream_answer
        self.agent_kwargs = {}

    def tearDown(self):
        main.get_authoritative_context = self._original_authority
        main.agent_runtime.run = self._original_agent_run
        main.ai.stream_answer = self._original_stream_answer

    def test_deep_stream_uses_teacher_answer(self):
        main.get_authoritative_context = lambda query: AUTHORITY_TEXT
        captured = self.agent_kwargs

        def fake_agent_run(question, history_text="", ui_enabled=True, **kwargs):
            captured.update(kwargs)
            captured["question"] = question
            yield {
                "type": "complete",
                "answer": "二分查找要求数组有序。",
                "sources": [],
                "trace": [],
                "durationMs": 12,
                "mode": "deep",
            }

        main.agent_runtime.run = fake_agent_run
        with main.app.app_context():
            events = _events(list(main._typed_deep_stream(self.student_id, "二分查找怎么用？")))
        types = [event["type"] for event in events]

        self.assertIn("status", types)
        status = next(event for event in events if event["type"] == "status")
        self.assertEqual("authority", status["stage"])
        self.assertEqual(AUTHORITY_TEXT.strip(), captured.get("authoritative_context", "").strip())

        complete = next(event for event in events if event["type"] == "complete")
        self.assertTrue(complete["authorityMatched"])

        done = next(event for event in events if event["type"] == "done")
        self.assertTrue(done["authorityMatched"])

        with main.app.app_context():
            record = (
                main.Question.query.filter_by(student_id=self.student_id)
                .order_by(main.Question.id.desc())
                .first()
            )
        self.assertIsNotNone(record)
        trace = json.loads(record.trace_json or "{}")
        self.assertTrue(trace.get("authorityMatched"))

    def test_deep_stream_without_teacher_answer(self):
        main.get_authoritative_context = lambda query: ""

        def fake_agent_run(question, history_text="", ui_enabled=True, **kwargs):
            yield {"type": "complete", "answer": "普通回答", "sources": [], "trace": [], "durationMs": 5, "mode": "deep"}

        main.agent_runtime.run = fake_agent_run
        with main.app.app_context():
            events = _events(list(main._typed_deep_stream(self.student_id, "普通问题")))
        complete = next(event for event in events if event["type"] == "complete")
        self.assertFalse(complete["authorityMatched"])
        self.assertFalse(any(event.get("stage") == "authority" for event in events))

    def test_fast_stream_reports_authority_match(self):
        main.get_authoritative_context = lambda query: AUTHORITY_TEXT
        main.ai.stream_answer = lambda *args, **kwargs: iter(["回答"])

        with main.app.app_context():
            events = _events(list(main._typed_fast_stream(self.student_id, "二分查找怎么用？", None)))
        complete = next(event for event in events if event["type"] == "complete")
        self.assertTrue(complete["authorityMatched"])
        done = next(event for event in events if event["type"] == "done")
        self.assertTrue(done["authorityMatched"])


if __name__ == "__main__":
    unittest.main()
