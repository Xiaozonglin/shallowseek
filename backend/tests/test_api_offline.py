"""问答接口事件流离线集成测试。

不启动 Flask 服务、不调用真实 DeepSeek API：把 AIEngine 的流式方法替换为假实现，
直接跑 main.py 里的快答/深度事件生成器，验证事件协议与落库字段。
"""

import json
import os
import tempfile
import unittest

_DB_FILE = os.path.join(tempfile.gettempdir(), "xdwe-api-offline.db")
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_FILE}")

import main  # noqa: E402  (需要先设置环境变量)


def _events(raw_chunks):
    events = []
    for chunk in raw_chunks:
        line = chunk.strip()
        if not line.startswith("data: "):
            continue
        events.append(json.loads(line[len("data: "):]))
    return events


class QaEventStreamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(_DB_FILE):
            os.unlink(_DB_FILE)
        main.app.config["TESTING"] = True
        with main.app.app_context():
            main.db.create_all()
            student = main.User(username="tester", email="tester@example.com", password="x", role="student")
            main.db.session.add(student)
            main.db.session.commit()
            cls.student_id = student.id

    def setUp(self):
        self._orig_stream_answer = main.ai.stream_answer
        self._orig_agent_run = main.agent_runtime.run
        main.ai.stream_answer = lambda *args, **kwargs: iter(["你", "好"])

    def tearDown(self):
        main.ai.stream_answer = self._orig_stream_answer
        main.agent_runtime.run = self._orig_agent_run

    def test_typed_fast_stream_and_persist(self):
        with main.app.app_context():
            chunks = list(main._typed_fast_stream(self.student_id, "什么是栈？", None))
            events = _events(chunks)
            types = [event["type"] for event in events]

        self.assertEqual("start", types[0])
        self.assertIn("answer_delta", types)
        self.assertIn("complete", types)
        self.assertIn("done", types)
        complete = next(event for event in events if event["type"] == "complete")
        self.assertEqual("你好", complete["answer"])
        self.assertEqual("fast", complete["mode"])

        with main.app.app_context():
            record = main.Question.query.filter_by(student_id=self.student_id).order_by(main.Question.id.desc()).first()
        self.assertIsNotNone(record)
        self.assertEqual("fast", record.mode)
        self.assertIsNotNone(record.trace_json)

    def test_typed_deep_stream_and_cards(self):
        ui_payload = {
            "version": 1,
            "cards": [{"type": "source_list", "citations": [1]}],
        }

        def fake_agent_run(question, history_text="", ui_enabled=True):
            yield {"type": "status", "stage": "thinking", "message": "正在检索…"}
            yield {"type": "answer_delta", "text": "二分查找要求数组有序。"}
            yield {"type": "ui", "ui": ui_payload}
            yield {
                "type": "complete",
                "answer": "二分查找要求数组有序。",
                "sources": [{"citation": 1, "title": "二分查找", "source": None, "documentId": "algo-wiki/a.md"}],
                "trace": [{"name": "retrieve_knowledge", "ok": True, "arguments": "{}", "ms": 3}],
                "durationMs": 120,
                "mode": "deep",
            }

        main.agent_runtime.run = fake_agent_run
        with main.app.app_context():
            chunks = list(main._typed_deep_stream(self.student_id, "二分查找是什么？"))
            events = _events(chunks)
            types = [event["type"] for event in events]

        self.assertIn("ui", types)
        self.assertIn("done", types)
        ui_event = next(event for event in events if event["type"] == "ui")
        self.assertEqual("source_list", ui_event["ui"]["cards"][0]["type"])

        with main.app.app_context():
            record = main.Question.query.filter_by(student_id=self.student_id).order_by(main.Question.id.desc()).first()
        self.assertEqual("deep", record.mode)
        self.assertIsNotNone(record.ui_json)
        ui_json = json.loads(record.ui_json)
        self.assertEqual("source_list", ui_json["cards"][0]["type"])
        trace_json = json.loads(record.trace_json)
        self.assertEqual(1, len(trace_json["sources"]))

    def test_deep_error_not_saved(self):
        def failing_agent_run(question, history_text="", ui_enabled=True):
            yield {"type": "error", "code": "ai_error", "message": "模型不可用"}

        main.agent_runtime.run = failing_agent_run
        with main.app.app_context():
            before = main.Question.query.count()
            events = _events(main._typed_deep_stream(self.student_id, "问题"))
            after = main.Question.query.count()

        self.assertEqual("error", events[-1]["type"])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
