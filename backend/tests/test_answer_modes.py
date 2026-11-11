"""回答效果（模板 × 交流方式）的提示词、事件与落库测试。"""

import json
import os
import tempfile
import unittest
import uuid
from types import SimpleNamespace

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test")
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(tempfile.gettempdir(), 'xdwe-tests.db')}",
)

import main  # noqa: E402
from modules import answer_modes  # noqa: E402
from modules.agent import AgentRuntime  # noqa: E402


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


class AnswerModeMetaTest(unittest.TestCase):
    def test_defaults_and_validation(self):
        self.assertEqual("free", answer_modes.normalize_template(None))
        self.assertEqual("free", answer_modes.normalize_template("unknown"))
        self.assertEqual("long_form", answer_modes.normalize_style(""))
        self.assertEqual("short_round", answer_modes.normalize_style("short_round"))
        self.assertTrue(answer_modes.is_valid_template("review_old"))
        self.assertTrue(answer_modes.is_valid_template("free"))
        self.assertFalse(answer_modes.is_valid_template("nope"))
        self.assertTrue(answer_modes.is_valid_style("short_round"))
        self.assertFalse(answer_modes.is_valid_style("nope"))

    def test_metadata_and_instructions(self):
        meta = answer_modes.metadata()
        self.assertEqual(4, len(meta["templates"]))
        self.assertEqual(2, len(meta["styles"]))
        self.assertEqual(
            {"free", "learn_new", "review_old", "explore_new"}, {item["id"] for item in meta["templates"]}
        )
        self.assertEqual({"short_round", "long_form"}, {item["id"] for item in meta["styles"]})

        learn_new = answer_modes.mode_instructions("learn_new", "short_round")
        self.assertIn("学习新知", learn_new)
        self.assertIn("逐轮短对话", learn_new)
        self.assertIn("变式题", learn_new)

        free = answer_modes.mode_instructions("free", "long_form")
        self.assertIn("自由回答", free)
        self.assertIn("不要硬加", free)
        self.assertIn("长对话", free)

        fast = answer_modes.fast_mode_instructions("short_round")
        self.assertIn("不套用回答模板", fast)
        self.assertIn("逐轮短对话", fast)
        self.assertNotIn("学习新知", fast)
        self.assertIn("不要附加例子", fast)


class AnswerModeRuntimeTest(unittest.TestCase):
    def test_agent_prompt_contains_template_and_style(self):
        engine = _FakeEngine()
        runtime = AgentRuntime(engine, max_rounds=1, timeout_seconds=30)
        list(
            runtime.run(
                "二分查找怎么学？",
                ui_enabled=False,
                template="explore_new",
                style="short_round",
            )
        )
        calls = engine.client.chat.completions.calls
        self.assertTrue(calls)
        system_content = calls[0]["messages"][0]["content"]
        self.assertIn("探索未知", system_content)
        self.assertIn("逐轮短对话", system_content)
        self.assertIn("200 字以内", system_content)
        # 短对话模式限制单次输出 token
        self.assertLessEqual(calls[0]["max_tokens"], 900)

    def test_long_form_keeps_full_max_tokens(self):
        engine = _FakeEngine()
        runtime = AgentRuntime(engine, max_rounds=1, timeout_seconds=30, max_output_tokens=2048)
        list(runtime.run("问题", ui_enabled=False, template="learn_new", style="long_form"))
        self.assertEqual(2048, engine.client.chat.completions.calls[0]["max_tokens"])


class AnswerModeStreamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.app.config["TESTING"] = True
        with main.app.app_context():
            main.ensure_schema()
            username = f"am_{uuid.uuid4().hex[:8]}"
            student = main.User(
                username=username,
                email=f"{username}@example.com",
                password="x",
                role="student",
            )
            main.db.session.add(student)
            main.db.session.commit()
            cls.student_id = student.id

    def setUp(self):
        self._original_stream_answer = main.ai.stream_answer
        self._original_agent_run = main.agent_runtime.run
        self._original_authority = main.get_authoritative_context
        main.get_authoritative_context = lambda query: ""

    def tearDown(self):
        main.ai.stream_answer = self._original_stream_answer
        main.agent_runtime.run = self._original_agent_run
        main.get_authoritative_context = self._original_authority

    def test_fast_stream_injects_mode_and_persists(self):
        captured = {}

        def fake_stream_answer(system_prompt, user_text, image_data_url=None, max_tokens=None):
            captured["system"] = system_prompt
            return iter(["回答"])

        main.ai.stream_answer = fake_stream_answer
        with main.app.app_context():
            events = _events(
                list(
                    main._typed_fast_stream(
                        self.student_id,
                        "复习一下栈",
                        None,
                        file_name="",
                        file_context="",
                        template="review_old",
                        style="short_round",
                    )
                )
            )

        # 快答模式不套用模板：即使前端选了复习旧知，也不会注入模板框架
        self.assertNotIn("复习旧知", captured["system"])
        self.assertIn("快速回答", captured["system"])
        self.assertIn("逐轮短对话", captured["system"])

        complete = next(event for event in events if event["type"] == "complete")
        self.assertEqual("free", complete["template"])
        self.assertEqual("short_round", complete["style"])

        with main.app.app_context():
            record = (
                main.Question.query.filter_by(student_id=self.student_id)
                .order_by(main.Question.id.desc())
                .first()
            )
        self.assertEqual("free", record.template)
        self.assertEqual("short_round", record.style)

    def test_deep_stream_passes_mode_to_agent_and_events(self):
        captured = {}

        def fake_agent_run(question, history_text="", ui_enabled=True, **kwargs):
            captured.update(kwargs)
            yield {
                "type": "complete",
                "answer": "深度回答",
                "sources": [],
                "trace": [],
                "durationMs": 8,
                "mode": "deep",
            }

        main.agent_runtime.run = fake_agent_run
        with main.app.app_context():
            events = _events(
                list(
                    main._typed_deep_stream(
                        self.student_id,
                        "什么是动态规划",
                        template="explore_new",
                        style="long_form",
                    )
                )
            )

        self.assertEqual("explore_new", captured.get("template"))
        self.assertEqual("long_form", captured.get("style"))
        complete = next(event for event in events if event["type"] == "complete")
        self.assertEqual("explore_new", complete["template"])
        self.assertEqual("long_form", complete["style"])


if __name__ == "__main__":
    unittest.main()
