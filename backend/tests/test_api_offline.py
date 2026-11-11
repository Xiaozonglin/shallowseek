"""问答接口事件流离线集成测试。

不启动 Flask 服务、不调用真实 DeepSeek API：把 AIEngine 的流式方法替换为假实现，
直接跑 main.py 里的快答/深度事件生成器，验证事件协议与落库字段。
"""

import json
import os
import tempfile
import unittest

_DB_FILE = os.path.join(tempfile.gettempdir(), "xdwe-tests.db")
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
        main.app.config["TESTING"] = True
        with main.app.app_context():
            main.ensure_schema()
            student = main.User.query.filter_by(username="tester").first()
            if student is None:
                student = main.User(
                    username="tester", email="tester@example.com", password="x", role="student"
                )
                main.db.session.add(student)
                main.db.session.commit()
            cls.student_id = student.id

    def setUp(self):
        self._orig_stream_answer = main.ai.stream_answer
        self._orig_agent_run = main.agent_runtime.run
        self._orig_generate_title = main.ai.generate_title
        main.ai.stream_answer = lambda *args, **kwargs: iter(["你", "好"])
        main.ai.generate_title = lambda *args, **kwargs: ""

    def tearDown(self):
        main.ai.stream_answer = self._orig_stream_answer
        main.agent_runtime.run = self._orig_agent_run
        main.ai.generate_title = self._orig_generate_title

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

        def fake_agent_run(question, history_text="", ui_enabled=True, **kwargs):
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

    def test_typed_fast_stream_with_file(self):
        captured = {}

        def fake_stream_answer(system_prompt, user_text, image_data_url=None, max_tokens=None):
            captured["system"] = system_prompt
            captured["user"] = user_text
            return iter(["文件", "要点"])

        main.ai.stream_answer = fake_stream_answer
        with main.app.app_context():
            chunks = list(main._typed_fast_stream(self.student_id, "", None, "note.txt", "文件正文内容"))
            events = _events(chunks)

        self.assertIn("文件正文内容", captured["system"])
        self.assertEqual("请阅读并分析用户上传的文件，提炼关键信息并给出要点。", captured["user"])
        self.assertIn("complete", [event["type"] for event in events])

        with main.app.app_context():
            record = main.Question.query.filter_by(student_id=self.student_id).order_by(main.Question.id.desc()).first()
        self.assertEqual("[文件] note.txt", record.content)

    def test_typed_deep_stream_with_file(self):
        captured = {}

        def fake_agent_run(question, history_text="", ui_enabled=True, **kwargs):
            captured["question"] = question
            yield {"type": "answer_delta", "text": "已阅读文件。"}
            yield {
                "type": "complete",
                "answer": "已阅读文件。",
                "sources": [],
                "trace": [],
                "durationMs": 10,
                "mode": "deep",
            }

        main.agent_runtime.run = fake_agent_run
        with main.app.app_context():
            events = _events(main._typed_deep_stream(self.student_id, "总结要点", "note.txt", "文件正文内容"))

        self.assertIn("总结要点", captured["question"])
        self.assertIn("文件正文内容", captured["question"])
        self.assertIn("done", [event["type"] for event in events])

        with main.app.app_context():
            record = main.Question.query.filter_by(student_id=self.student_id).order_by(main.Question.id.desc()).first()
        self.assertEqual("[文件] note.txt 总结要点", record.content)

    def test_generate_and_update_question_title(self):
        client = main.app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(self.student_id)
            sess["_fresh"] = True

        with main.app.app_context():
            record = main.Question(
                content="二分查找是什么？",
                answer="要求数组有序，每次排除一半。",
                student_id=self.student_id,
                mode="fast",
            )
            main.db.session.add(record)
            main.db.session.commit()
            record_id = record.id

        main.ai.generate_title = lambda *args, **kwargs: "二分查找复杂度"
        response = client.post(f"/api/questions/{record_id}/title")
        self.assertEqual(200, response.status_code)
        self.assertEqual("二分查找复杂度", response.get_json()["title"])

        response = client.patch(f"/api/questions/{record_id}/title", json={"title": "  我的标题  "})
        self.assertEqual(200, response.status_code)
        self.assertEqual("我的标题", response.get_json()["title"])

        with main.app.app_context():
            self.assertEqual("我的标题", main.db.session.get(main.Question, record_id).title)

        history = client.get("/api/student/questions/history").get_json()
        self.assertEqual("我的标题", next(item for item in history if item["id"] == record_id)["title"])

    def test_title_fallback_without_llm(self):
        title = main._generate_question_title("[文件] note.txt 二分查找的时间复杂度", "")
        self.assertEqual("note.txt 二分查找的时间复杂度", title)

    def test_qa_route_accepts_file_payload(self):
        captured = {}

        def fake_stream_answer(system_prompt, user_text, image_data_url=None, max_tokens=None):
            captured["system"] = system_prompt
            captured["user"] = user_text
            return iter(["已阅读文件。"])

        main.ai.stream_answer = fake_stream_answer
        client = main.app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(self.student_id)
            sess["_fresh"] = True

        response = client.post(
            "/api/qa",
            json={
                "question": "",
                "file": {"name": "note.txt", "content": "文件正文内容"},
                "mode": "fast",
                "uiVersion": 1,
            },
        )
        body = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("文件正文内容", captured["system"])
        self.assertEqual("请阅读并分析用户上传的文件，提炼关键信息并给出要点。", captured["user"])
        self.assertIn('"type": "complete"', body)

    def test_deep_error_not_saved(self):
        def failing_agent_run(question, history_text="", ui_enabled=True, **kwargs):
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
