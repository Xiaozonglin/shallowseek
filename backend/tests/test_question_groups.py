"""共性问题合并：自动聚类建议、一次回复多人受益、学生可见合并回复、RAG 注入。"""

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


class QuestionGroupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main.app.config["TESTING"] = True
        with main.app.app_context():
            main.ensure_schema()
            # 本文件的相似度 / 统计断言要求干净的问答数据
            main.QuestionGroup.query.delete()
            main.Question.query.delete()
            main.db.session.commit()

            def ensure_user(username, role):
                user = main.User.query.filter_by(username=username).first()
                if user is None:
                    user = main.User(
                        username=username,
                        email=f"{username}@example.com",
                        password="x",
                        role=role,
                    )
                    main.db.session.add(user)
                    main.db.session.commit()
                return user.id

            suffix = uuid.uuid4().hex[:6]
            cls.teacher_id = ensure_user(f"gt_{suffix}", "teacher")
            cls.student_ids = [ensure_user(f"gs{a}_{suffix}", "student") for a in ("a", "b", "c")]

    def _client_as(self, user_id):
        client = main.app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        return client

    def _create_question(self, student_id, content, shared=True):
        with main.app.app_context():
            question = main.Question(
                content=content,
                answer="AI 初始回答",
                student_id=student_id,
                mode="fast",
                shared=shared,
            )
            main.db.session.add(question)
            main.db.session.commit()
            return question.id

    def _pending_ids(self, client):
        return [item["id"] for item in client.get("/api/questions/pending").get_json()]

    def _history_record(self, client, question_id):
        history = client.get("/api/student/questions/history").get_json()
        return next((item for item in history if item["id"] == question_id), None)

    def _create_similar_batch(self, contents=None):
        contents = contents or [
            "二分查找的时间复杂度怎么推导？",
            "二分查找的时间复杂度如何推导？",
            "二分查找的时间复杂度是多少？",
        ]
        return [
            self._create_question(student_id, content)
            for student_id, content in zip(self.student_ids, contents)
        ]

    # ========================== 用例 ==========================
    def test_suggestions_cluster_similar_questions(self):
        ids = self._create_similar_batch()
        teacher = self._client_as(self.teacher_id)
        suggestions = teacher.get("/api/questions/groups/suggestions").get_json()
        clustered = {
            item["id"]
            for suggestion in suggestions
            for item in suggestion["questions"]
            if suggestion["questions"] and any(question["id"] in ids for question in suggestion["questions"])
        }
        # 至少建议组覆盖到这批问题中的 2 条以上
        self.assertGreaterEqual(len(clustered & set(ids)), 2)

    def test_merge_reply_benefits_all_and_rag(self):
        ids = self._create_similar_batch(
            [
                "动态规划的解题步骤是什么？",
                "动态规划的解题步骤如何总结？",
                "动态规划的解题步骤有哪些？",
            ]
        )
        teacher = self._client_as(self.teacher_id)
        student = self._client_as(self.student_ids[0])

        response = teacher.post(
            "/api/questions/groups",
            json={
                "question_ids": ids,
                "title": "动态规划解题步骤",
                "answer": "动态规划的步骤是：定义状态、写转移、初始化、遍历求解。",
            },
        )
        self.assertEqual(201, response.status_code)
        group = response.get_json()
        self.assertEqual(len(ids), group["member_count"])

        # 合并后：待处理不再出现，学生历史能看到老师合并回复
        pending = self._pending_ids(teacher)
        self.assertFalse(set(ids) & set(pending))
        for student_id, question_id in zip(self.student_ids, ids):
            record = self._history_record(self._client_as(student_id), question_id)
            self.assertIn("定义状态", record["authoritative_answer"])
            self.assertEqual(group["id"], record["merged_group"]["id"])

        # 原问题不再允许单独设置权威答案
        self.assertEqual(
            409,
            teacher.post(f"/api/questions/{ids[0]}/authoritative", json={"answer": "重复回答"}).status_code,
        )

        # 新问的相似问题能命中合并回复（RAG 注入）
        with main.app.app_context():
            context = main.get_authoritative_context("动态规划的解题步骤是什么？")
        self.assertIn("同类问题合并参考", context)
        self.assertIn("定义状态", context)

        # 更新合并回复：组内学生都会看到新内容
        response = teacher.put(f"/api/questions/groups/{group['id']}", json={"answer": "更新后的合并回复"})
        self.assertEqual(200, response.status_code)
        record = self._history_record(student, ids[0])
        self.assertEqual("更新后的合并回复", record["authoritative_answer"])

        # 解除合并：问题回到待处理，学生历史不再显示合并回复
        self.assertEqual(200, teacher.delete(f"/api/questions/groups/{group['id']}").status_code)
        self.assertIn(ids[0], self._pending_ids(teacher))
        record = self._history_record(student, ids[0])
        self.assertIsNone(record["authoritative_answer"])
        self.assertIsNone(record["merged_group"])

    def test_only_teacher_and_shared_questions_can_merge(self):
        shared_ids = self._create_similar_batch()[:2]
        private_id = self._create_question(self.student_ids[0], "私密问题", shared=False)
        student = self._client_as(self.student_ids[0])
        teacher = self._client_as(self.teacher_id)

        self.assertEqual(
            403,
            student.post("/api/questions/groups", json={"question_ids": shared_ids}).status_code,
        )
        self.assertEqual(
            403,
            teacher.post(
                "/api/questions/groups", json={"question_ids": [shared_ids[0], private_id]}
            ).status_code,
        )

    def test_group_list_and_member_count(self):
        ids = self._create_similar_batch()[:2]
        teacher = self._client_as(self.teacher_id)
        created = teacher.post(
            "/api/questions/groups",
            json={"question_ids": ids, "title": "合并测试", "answer": "统一回复"},
        ).get_json()
        groups = teacher.get("/api/questions/groups").get_json()
        target = next(item for item in groups if item["id"] == created["id"])
        self.assertEqual(2, target["member_count"])
        self.assertEqual("合并测试", target["title"])


if __name__ == "__main__":
    unittest.main()
