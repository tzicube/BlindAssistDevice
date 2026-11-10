import unittest

from Backend.navigation import (
    extract_destination_query,
    normalize_navigation_text,
    resolve_destination,
)


class NavigationResolverTest(unittest.TestCase):
    def setUp(self):
        self.home = {
            "id": 1,
            "name": "Home",
            "address": "1 Home Road",
            "lat": 24.98,
            "lng": 121.35,
            "aliases": ["家", "回家", "我的家", "my home"],
        }
        self.school = {
            "id": 2,
            "name": "School",
            "address": "1 School Road",
            "lat": 24.99,
            "lng": 121.36,
            "aliases": ["學校", "学校"],
        }

    def test_normalizes_unicode_case_and_punctuation(self):
        self.assertEqual("navigate to home", normalize_navigation_text("Navigate to HOME!"))

    def test_extracts_chinese_without_spaces_and_english_destination(self):
        self.assertEqual("學校", extract_destination_query("請帶我去學校"))
        self.assertEqual("学校", extract_destination_query("请带我去学校谢谢"))
        self.assertEqual("school", extract_destination_query("Navigate to School please"))

    def test_matches_traditional_chinese_alias(self):
        result = resolve_destination("帶我回家", [self.home, self.school])
        self.assertEqual("saved_place", result["matchType"])
        self.assertEqual(1, result["destination"]["id"])
        self.assertEqual("回家", result["matchedText"])

    def test_matches_simplified_chinese_alias(self):
        result = resolve_destination("带我去学校", [self.home, self.school])
        self.assertEqual("saved_place", result["matchType"])
        self.assertEqual(2, result["destination"]["id"])

    def test_matches_small_stt_typo(self):
        result = resolve_destination("Navigate to schol", [self.home, self.school])
        self.assertEqual("saved_place", result["matchType"])
        self.assertEqual(2, result["destination"]["id"])

    def test_does_not_match_short_alias_inside_unrelated_query(self):
        place = {**self.home, "aliases": ["gym"]}
        result = resolve_destination("Navigate to gymnasium", [place])
        self.assertEqual("not_found", result["matchType"])

    def test_returns_ambiguous_for_equal_matches(self):
        second_home = {
            **self.home,
            "id": 3,
            "name": "Parents Home",
            "aliases": ["家"],
        }
        result = resolve_destination("去家", [self.home, second_home])
        self.assertEqual("ambiguous", result["matchType"])
        self.assertEqual([1, 3], [place["id"] for place in result["candidates"]])


if __name__ == "__main__":
    unittest.main()
