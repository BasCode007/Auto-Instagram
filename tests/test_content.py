"""Unit tests for :mod:`auto_instagram.content`."""

from __future__ import annotations

import unittest

from auto_instagram.caption import count_hashtags
from auto_instagram.content import (
    DISCLAIMER,
    PILLARS,
    build_post_caption,
    load_hashtag_bank,
    select_hashtags,
)

# A small self-contained bank so tests don't depend on the shipped JSON.
_BANK = {
    "core": ["#wealth", "#moneymindset"],
    "pillars": {
        "wealth_mindset": ["#abundancemindset", "#wealth"],  # note: dup of core
        "investing_basics": ["#investing", "#compoundinterest"],
    },
}


class HashtagBankTests(unittest.TestCase):
    def test_shipped_bank_covers_every_pillar(self):
        bank = load_hashtag_bank()
        self.assertTrue(bank["core"])
        for pillar in PILLARS:
            self.assertIn(pillar, bank["pillars"], f"missing pillar {pillar}")
            self.assertTrue(bank["pillars"][pillar], f"empty pillar {pillar}")


class SelectHashtagsTests(unittest.TestCase):
    def test_combines_core_and_pillar_without_duplicates(self):
        tags = select_hashtags("wealth_mindset", bank=_BANK)
        self.assertEqual(tags, ["#wealth", "#moneymindset", "#abundancemindset"])

    def test_appends_extra_tags(self):
        tags = select_hashtags(
            "wealth_mindset", extra=["custom", "#wealth"], bank=_BANK
        )
        self.assertIn("#custom", tags)
        self.assertEqual(tags.count("#wealth"), 1)

    def test_respects_limit(self):
        tags = select_hashtags("wealth_mindset", limit=2, bank=_BANK)
        self.assertEqual(len(tags), 2)

    def test_unknown_pillar_raises(self):
        with self.assertRaises(ValueError):
            select_hashtags("not_a_pillar", bank=_BANK)


class BuildPostCaptionTests(unittest.TestCase):
    def test_assembles_hook_body_cta_and_hashtags(self):
        caption = build_post_caption(
            "The habit that builds wealth",
            "Automate a transfer the day you get paid.",
            "wealth_mindset",
            cta="Save this for payday.",
            bank=_BANK,
        )
        self.assertTrue(caption.startswith("The habit that builds wealth"))
        self.assertIn("Automate a transfer", caption)
        self.assertIn("Save this for payday.", caption)
        self.assertIn("#abundancemindset", caption)

    def test_investing_pillar_adds_disclaimer_by_default(self):
        caption = build_post_caption(
            "Compounding explained",
            "Small amounts grow over decades.",
            "investing_basics",
            bank=_BANK,
        )
        self.assertIn(DISCLAIMER, caption)

    def test_disclaimer_can_be_forced_off(self):
        caption = build_post_caption(
            "Compounding explained",
            "Small amounts grow over decades.",
            "investing_basics",
            add_disclaimer=False,
            bank=_BANK,
        )
        self.assertNotIn(DISCLAIMER, caption)

    def test_non_investing_pillar_has_no_disclaimer(self):
        caption = build_post_caption(
            "Mindset shift", "Think in decades.", "wealth_mindset", bank=_BANK
        )
        self.assertNotIn(DISCLAIMER, caption)

    def test_result_stays_within_hashtag_limit(self):
        caption = build_post_caption(
            "Hook", "Body", "wealth_mindset", limit_hashtags=2, bank=_BANK
        )
        self.assertLessEqual(count_hashtags(caption), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
