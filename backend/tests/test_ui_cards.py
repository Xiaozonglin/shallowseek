"""卡片协议校验测试（离线，无模型调用）。"""

import unittest

from modules import ui_cards

SOURCES = [
    {"citation": 1, "title": "二分查找", "source": None, "documentId": "algo-wiki/chapter_searching/binary_search.md"},
    {"citation": 2, "title": "哈希表", "source": None, "documentId": "algo-wiki/chapter_hashing/hash_map.md"},
]


class UICardsTest(unittest.TestCase):
    def test_three_valid_cards(self):
        value = {
            "version": 1,
            "cards": [
                {"type": "source_list", "citations": [1, 2]},
                {
                    "type": "guide",
                    "title": "二分查找步骤",
                    "steps": [
                        {"title": "确定区间", "detail": "在有序数组中确定首尾指针。", "citations": [1]},
                        {"title": "折半比较", "detail": "比较中点值与目标值。", "citations": [1]},
                    ],
                },
                {"type": "related_chapters", "chapterIds": ["searching", "hashing"]},
            ],
        }
        envelope, errors = ui_cards.validate_ui(value, SOURCES)
        self.assertIsNotNone(envelope)
        self.assertEqual([], errors)
        self.assertEqual(3, len(envelope.cards))

    def test_invalid_version(self):
        envelope, errors = ui_cards.validate_ui({"version": 2, "cards": []}, SOURCES)
        self.assertIsNone(envelope)
        self.assertEqual(["invalid_envelope"], errors)

    def test_invalid_schema_type(self):
        value = {"version": 1, "cards": [{"type": "html", "html": "<script>alert(1)</script>"}]}
        envelope, errors = ui_cards.validate_ui(value, SOURCES)
        self.assertIsNone(envelope)
        self.assertEqual(["card_0:invalid_schema"], errors)

    def test_invented_citation(self):
        value = {"version": 1, "cards": [{"type": "source_list", "citations": [99]}]}
        envelope, errors = ui_cards.validate_ui(value, SOURCES)
        self.assertIsNone(envelope)
        self.assertEqual(["card_0:invalid_source"], errors)

    def test_boolean_and_string_citation_rejected(self):
        for bad in (True, "1"):
            value = {"version": 1, "cards": [{"type": "source_list", "citations": [bad]}]}
            envelope, errors = ui_cards.validate_ui(value, SOURCES)
            self.assertIsNone(envelope)
            self.assertEqual(["card_0:invalid_schema"], errors)

    def test_markup_in_title_rejected(self):
        value = {
            "version": 1,
            "cards": [{"type": "guide", "title": "<b>步骤</b>", "steps": [{"title": "x", "detail": "y", "citations": [1]}]}],
        }
        envelope, errors = ui_cards.validate_ui(value, SOURCES)
        self.assertIsNone(envelope)
        self.assertEqual(["card_0:invalid_schema"], errors)

    def test_unknown_chapter_id(self):
        value = {"version": 1, "cards": [{"type": "related_chapters", "chapterIds": ["not_a_chapter"]}]}
        envelope, errors = ui_cards.validate_ui(value, SOURCES)
        self.assertIsNone(envelope)
        self.assertEqual(["card_0:unknown_chapter"], errors)

    def test_too_many_cards(self):
        cards = [{"type": "source_list", "citations": [1]} for _ in range(4)]
        envelope, errors = ui_cards.validate_ui({"version": 1, "cards": cards}, SOURCES)
        self.assertIsNone(envelope)
        self.assertEqual(["invalid_envelope"], errors)

    def test_extra_field_rejected(self):
        value = {"version": 1, "cards": [{"type": "source_list", "citations": [1], "unexpected": 1}]}
        envelope, errors = ui_cards.validate_ui(value, SOURCES)
        self.assertIsNone(envelope)
        self.assertEqual(["card_0:invalid_schema"], errors)

    def test_javascript_source_rejected(self):
        sources = [{"citation": 1, "title": "坏链接", "source": "javascript:alert(1)", "documentId": "bad"}]
        value = {"version": 1, "cards": [{"type": "source_list", "citations": [1]}]}
        envelope, errors = ui_cards.validate_ui(value, sources)
        self.assertIsNone(envelope)
        self.assertEqual(["card_0:invalid_source"], errors)

    def test_chapter_catalog_non_empty(self):
        self.assertIn("searching", ui_cards.chapter_ids())
        self.assertGreaterEqual(len(ui_cards.chapter_ids()), 10)


if __name__ == "__main__":
    unittest.main()
