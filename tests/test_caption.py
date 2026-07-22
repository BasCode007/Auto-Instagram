"""Unit tests for :mod:`auto_instagram.caption`."""

from __future__ import annotations

import unittest

from auto_instagram.caption import (
    MAX_CAPTION_LENGTH,
    build_caption,
    count_hashtags,
    normalize_hashtag,
    normalize_hashtags,
    validate_caption,
)


class NormalizeHashtagTests(unittest.TestCase):
    def test_adds_missing_hash(self):
        self.assertEqual(normalize_hashtag("travel"), "#travel")

    def test_strips_hash_and_whitespace(self):
        self.assertEqual(normalize_hashtag("  #Travel  "), "#Travel")

    def test_removes_non_tag_characters(self):
        # A space (or punctuation) ends a real Instagram tag, so we fold the
        # remainder into a single tag rather than silently keeping the space.
        self.assertEqual(normalize_hashtag("#foo bar!"), "#foobar")

    def test_returns_none_when_nothing_usable(self):
        self.assertIsNone(normalize_hashtag("###"))
        self.assertIsNone(normalize_hashtag("   "))
        self.assertIsNone(normalize_hashtag("!!!"))


class NormalizeHashtagsTests(unittest.TestCase):
    def test_dedupes_case_insensitively_preserving_order(self):
        self.assertEqual(
            normalize_hashtags(["#Sun", "sea", "#sun", "sand"]),
            ["#Sun", "#sea", "#sand"],
        )

    def test_drops_blank_entries(self):
        self.assertEqual(normalize_hashtags(["#a", "  ", "###", "b"]), ["#a", "#b"])

    def test_caps_at_max(self):
        self.assertEqual(
            normalize_hashtags(["#a", "#b", "#c"], max_hashtags=2), ["#a", "#b"]
        )


class CountHashtagsTests(unittest.TestCase):
    def test_counts_tags_including_underscores(self):
        self.assertEqual(count_hashtags("#a #b some text #c_d"), 3)

    def test_no_tags(self):
        self.assertEqual(count_hashtags("just a plain caption"), 0)


class BuildCaptionTests(unittest.TestCase):
    def test_stacks_sections_with_blank_lines(self):
        caption = build_caption("Title", "Body", ["#a", "b", "#a"])
        self.assertEqual(caption, "Title\n\nBody\n\n#a #b")

    def test_omits_empty_sections(self):
        self.assertEqual(build_caption("", "Body", []), "Body")
        self.assertEqual(build_caption("Title", "", []), "Title")

    def test_respects_max_hashtags(self):
        caption = build_caption("T", "", ["#a", "#b", "#c"], max_hashtags=2)
        self.assertEqual(count_hashtags(caption), 2)

    def test_raises_when_over_limit_without_truncate(self):
        with self.assertRaises(ValueError):
            build_caption("x" * 10, max_length=5)

    def test_truncates_body_keeping_title_and_hashtags(self):
        caption = build_caption(
            "Hi", "abcdefghijklmnopqrstuvwxyz", ["#x"], max_length=20, truncate=True
        )
        self.assertLessEqual(len(caption), 20)
        self.assertTrue(caption.startswith("Hi\n\n"))
        self.assertTrue(caption.endswith("\n\n#x"))
        self.assertIn("…", caption)

    def test_raises_when_scaffold_alone_too_long_even_with_truncate(self):
        with self.assertRaises(ValueError):
            build_caption("LongTitle", "body", max_length=5, truncate=True)

    def test_truncation_fits_default_limit(self):
        caption = build_caption(
            "Trip", "word " * 1000, ["#travel", "#wanderlust"], truncate=True
        )
        self.assertLessEqual(len(caption), MAX_CAPTION_LENGTH)
        self.assertEqual(validate_caption(caption), [])


class ValidateCaptionTests(unittest.TestCase):
    def test_valid_caption_has_no_problems(self):
        self.assertEqual(validate_caption("A tidy caption #ok"), [])

    def test_flags_over_length(self):
        problems = validate_caption("x" * (MAX_CAPTION_LENGTH + 5))
        self.assertEqual(len(problems), 1)
        self.assertIn("over", problems[0])

    def test_flags_too_many_hashtags(self):
        caption = " ".join(f"#tag{i}" for i in range(31))
        problems = validate_caption(caption)
        self.assertTrue(any("hashtag" in p for p in problems))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
