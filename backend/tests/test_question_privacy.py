"""隐私边界测试：问答默认仅学生可见，只有学生主动提交后教师端才能查看/回答/统计。"""

import os
import tempfile
import unittest
import uuid

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test")
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(tempfile.gettempdir(), 'xdwe-tests.db')}",
)

import main  # noqa: E402  (需要先设置环境变量)


def _suffix():
    return uuid.uuid4().hex[:8]


class QuestionPrivacyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.app.config["TESTING"] = True
        with main.app.app_context():
            main.db.create_all()

            def ensure_user(username, role):
                user = main.User.query.filter_by(username=username).first()
                if user is None:
                    suffix = _suffix()
                    user = main.User(
                        username=username,
                        email=f"{username}@example.com",
                        password="x",
                        role=role,
                    )
                    main.db.session.add(user)
                    main.db.session.commit()
                return user.id

            cls.teacher_id = ensure_user(f"pt_{_suffix()}", "teacher")
            cls.student_a_id = ensure_user(f"pa_{_suffix()}", "student")
            cls.student_b_id = ensure_user(f"pb_{_suffix()}", "student")

    def setUp(self):
        self._original_generate_ai_text = main.generate_ai_text
        main.generate_ai_text = lambda *args, **kwargs: "测试学情总结"

    def tearDown(self):
        main.generate_ai_text = self._original_generate_ai_text

    # ========================== 辅助 ==========================
    def _client_as(self, user_id):
        client = main.app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        return client

    def _create_question(self, student_id, content):
        with main.app.app_context():
            question = main.Question(
                content=content,
                answer="AI 初始回答",
                student_id=student_id,
                mode="fast",
            )
            main.db.session.add(question)
            main.db.session.commit()
            return question.id

    def _history_record(self, client, question_id):
        history = client.get("/api/student/questions/history").get_json()
        return next((item for item in history if item["id"] == question_id), None)

    def _pending_ids(self, client):
        return [item["id"] for item in client.get("/api/questions/pending").get_json()]

    def _stats_questions(self, client):
        stats = client.get("/api/questions/stats").get_json()
        return [item["question"] for items in stats.get("questions_by_student", {}).values() for item in items]

    # ========================== 用例 ==========================
    def test_private_question_invisible_to_teacher(self):
        content = f"私有问题-{_suffix()}"
        question_id = self._create_question(self.student_a_id, content)
        teacher = self._client_as(self.teacher_id)

        self.assertNotIn(question_id, self._pending_ids(teacher))
        self.assertNotIn(content, self._stats_questions(teacher))

    def test_share_then_teacher_can_view_and_answer(self):
        content = f"课程求助-{_suffix()}"
        question_id = self._create_question(self.student_a_id, content)
        student = self._client_as(self.student_a_id)
        teacher = self._client_as(self.teacher_id)

        response = student.post(f"/api/questions/{question_id}/share")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.get_json()["shared"])

        record = self._history_record(student, question_id)
        self.assertTrue(record["shared"])
        self.assertTrue(record["shared_at"])

        self.assertIn(question_id, self._pending_ids(teacher))
        self.assertIn(content, self._stats_questions(teacher))

        response = teacher.post(
            f"/api/questions/{question_id}/authoritative", json={"answer": "老师权威解答"}
        )
        self.assertEqual(200, response.status_code)

        # 老师已回复后不允许撤回
        response = student.delete(f"/api/questions/{question_id}/share")
        self.assertEqual(409, response.status_code)

    def test_unshare_before_teacher_reply(self):
        question_id = self._create_question(self.student_a_id, f"可以撤回-{_suffix()}")
        student = self._client_as(self.student_a_id)
        teacher = self._client_as(self.teacher_id)

        self.assertEqual(200, student.post(f"/api/questions/{question_id}/share").status_code)
        self.assertIn(question_id, self._pending_ids(teacher))

        response = student.delete(f"/api/questions/{question_id}/share")
        self.assertEqual(200, response.status_code)
        self.assertFalse(response.get_json()["shared"])
        self.assertNotIn(question_id, self._pending_ids(teacher))
        self.assertFalse(self._history_record(student, question_id)["shared"])

    def test_only_owner_can_share(self):
        question_id = self._create_question(self.student_a_id, f"别人的问题-{_suffix()}")
        other_student = self._client_as(self.student_b_id)

        self.assertEqual(403, other_student.post(f"/api/questions/{question_id}/share").status_code)
        self.assertEqual(403, other_student.delete(f"/api/questions/{question_id}/share").status_code)

    def test_teacher_cannot_answer_or_delete_private_question(self):
        question_id = self._create_question(self.student_a_id, f"未提交-{_suffix()}")
        teacher = self._client_as(self.teacher_id)

        response = teacher.post(
            f"/api/questions/{question_id}/authoritative", json={"answer": "越权回答"}
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(403, teacher.delete(f"/api/questions/{question_id}").status_code)

    def test_teacher_can_delete_shared_question(self):
        question_id = self._create_question(self.student_a_id, f"可删除-{_suffix()}")
        student = self._client_as(self.student_a_id)
        teacher = self._client_as(self.teacher_id)

        self.assertEqual(200, student.post(f"/api/questions/{question_id}/share").status_code)
        self.assertEqual(200, teacher.delete(f"/api/questions/{question_id}").status_code)
        self.assertFalse(any(item["id"] == question_id for item in student.get("/api/student/questions/history").get_json()))


if __name__ == "__main__":
    unittest.main()
