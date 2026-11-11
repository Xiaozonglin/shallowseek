"""多轮会话：会话 CRUD、/api/qa 归属、多轮上下文与权限。"""

import json
import os
import tempfile
import unittest
import uuid

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test")
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(tempfile.gettempdir(), 'xdwe-tests.db')}",
)

import main  # noqa: E402


def _events(response):
    events = []
    for line in response.data.decode("utf-8").splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


class ConversationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.app.config["TESTING"] = True
        main.ensure_schema()
        with main.app.app_context():
            def ensure_user(username, role):
                user = main.User.query.filter_by(username=username).first()
                if user is None:
                    user = main.User(
                        username=username, email=f"{username}@example.com", password="x", role=role
                    )
                    main.db.session.add(user)
                    main.db.session.commit()
                return user.id

            suffix = uuid.uuid4().hex[:6]
            cls.student_id = ensure_user(f"cv_{suffix}", "student")
            cls.other_student_id = ensure_user(f"cv2_{suffix}", "student")
            cls.teacher_id = ensure_user(f"ct_{suffix}", "teacher")

    def setUp(self):
        self._original_stream_answer = main.ai.stream_answer
        self._original_authority = main.get_authoritative_context
        self.prompts = []
        main.get_authoritative_context = lambda query: ""

        def fake_stream_answer(system_prompt, user_text, image_data_url=None, max_tokens=None):
            self.prompts.append(system_prompt)
            return iter(["回答"])

        main.ai.stream_answer = fake_stream_answer

    def tearDown(self):
        main.ai.stream_answer = self._original_stream_answer
        main.get_authoritative_context = self._original_authority

    def _client_as(self, user_id):
        client = main.app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        return client

    def _ask(self, client, question, conversation_id=None):
        payload = {"question": question, "mode": "fast", "uiVersion": 1}
        if conversation_id is not None:
            payload["conversationId"] = conversation_id
        response = client.post("/api/qa", json=payload)
        self.assertEqual(200, response.status_code)
        return _events(response)

    # ========================== 用例 ==========================
    def test_first_question_creates_conversation(self):
        client = self._client_as(self.student_id)
        events = self._ask(client, "什么是栈？")
        start = next(item for item in events if item["type"] == "start")
        done = next(item for item in events if item["type"] == "done")
        self.assertIsNotNone(start["conversationId"])
        self.assertEqual(start["conversationId"], done["conversationId"])

        conversations = client.get("/api/conversations").get_json()
        target = next(item for item in conversations if item["id"] == done["conversationId"])
        self.assertEqual(1, target["turn_count"])

        messages = client.get(f"/api/conversations/{done['conversationId']}/messages").get_json()
        self.assertEqual(1, len(messages["turns"]))
        self.assertEqual("什么是栈？", messages["turns"][0]["question"])
        self.assertEqual("回答", messages["turns"][0]["answer"])

    def test_follow_up_turn_uses_same_conversation_and_context(self):
        client = self._client_as(self.student_id)
        first = self._ask(client, "什么是栈？")
        conversation_id = next(item for item in first if item["type"] == "done")["conversationId"]
        prompts_after_first = len(self.prompts)

        second = self._ask(client, "那队列呢？", conversation_id=conversation_id)
        done = next(item for item in second if item["type"] == "done")
        self.assertEqual(conversation_id, done["conversationId"])

        # 第二次请求的 system prompt 带上了第一轮问答（会话级上下文）
        follow_up_prompt = self.prompts[prompts_after_first]
        self.assertIn("什么是栈？", follow_up_prompt)
        self.assertIn("回答", follow_up_prompt)

        conversations = client.get("/api/conversations").get_json()
        target = next(item for item in conversations if item["id"] == conversation_id)
        self.assertEqual(2, target["turn_count"])

        messages = client.get(f"/api/conversations/{conversation_id}/messages").get_json()
        self.assertEqual(["什么是栈？", "那队列呢？"], [turn["question"] for turn in messages["turns"]])

    def test_manual_new_conversation(self):
        client = self._client_as(self.student_id)
        created = client.post("/api/conversations", json={}).get_json()
        self.assertEqual(0, created["turn_count"])
        events = self._ask(client, "新的会话问题", conversation_id=created["id"])
        done = next(item for item in events if item["type"] == "done")
        self.assertEqual(created["id"], done["conversationId"])
        messages = client.get(f"/api/conversations/{created['id']}/messages").get_json()
        self.assertEqual(1, messages["turn_count"])

    def test_rename_and_delete_conversation(self):
        client = self._client_as(self.student_id)
        events = self._ask(client, "待重命名的会话")
        conversation_id = next(item for item in events if item["type"] == "done")["conversationId"]

        renamed = client.patch(f"/api/conversations/{conversation_id}", json={"title": "栈与队列复习"})
        self.assertEqual(200, renamed.status_code)
        self.assertEqual("栈与队列复习", renamed.get_json()["title"])

        self.assertEqual(200, client.delete(f"/api/conversations/{conversation_id}").status_code)
        self.assertEqual(404, client.get(f"/api/conversations/{conversation_id}/messages").status_code)
        conversations = client.get("/api/conversations").get_json()
        self.assertFalse(any(item["id"] == conversation_id for item in conversations))

    def test_conversation_is_private(self):
        owner = self._client_as(self.student_id)
        other = self._client_as(self.other_student_id)
        teacher = self._client_as(self.teacher_id)

        events = self._ask(owner, "私有会话")
        conversation_id = next(item for item in events if item["type"] == "done")["conversationId"]

        self.assertEqual(403, other.get(f"/api/conversations/{conversation_id}/messages").status_code)
        self.assertEqual(
            403,
            other.patch(f"/api/conversations/{conversation_id}", json={"title": "偷改"}).status_code,
        )
        self.assertEqual(403, other.delete(f"/api/conversations/{conversation_id}").status_code)
        self.assertEqual(403, teacher.get("/api/conversations").status_code)

        response = other.post(
            "/api/qa",
            json={"question": "越权", "mode": "fast", "uiVersion": 1, "conversationId": conversation_id},
        )
        self.assertEqual(403, response.status_code)


if __name__ == "__main__":
    unittest.main()
