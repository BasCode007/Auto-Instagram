"""Niche content helpers: pillars, hashtag selection and caption assembly.

This sits on top of :mod:`auto_instagram.caption` and turns the raw hashtag
bank in ``config/hashtags.json`` plus a content *pillar* into a ready-to-post
caption. It is the canonical, testable definition of how a caption for this
account is built; the n8n workflow mirrors the same rules in a Code node.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .caption import MAX_HASHTAGS, build_caption, normalize_hashtags

__all__ = [
    "PILLARS",
    "DISCLAIMER",
    "load_hashtag_bank",
    "select_hashtags",
    "build_post_caption",
]

#: Content pillars to rotate across. Keys match ``config/hashtags.json`` and
#: the pillar table in ``config/niche.md``.
PILLARS = (
    "wealth_mindset",
    "money_habits",
    "investing_basics",
    "entrepreneurship",
    "success_psychology",
    "daily_motivation",
)

#: Light disclaimer appended to investing-pillar posts (see config/niche.md).
DISCLAIMER = "Educational only, not financial advice."

_DEFAULT_BANK_PATH = Path(__file__).resolve().parent.parent / "config" / "hashtags.json"


def load_hashtag_bank(path: str | Path | None = None) -> dict:
    """Load the hashtag bank JSON (defaults to ``config/hashtags.json``)."""
    bank_path = Path(path) if path is not None else _DEFAULT_BANK_PATH
    with open(bank_path, encoding="utf-8") as fh:
        return json.load(fh)


def select_hashtags(
    pillar: str,
    *,
    extra: Iterable[str] = (),
    limit: int = MAX_HASHTAGS,
    bank: dict | None = None,
) -> list[str]:
    """Return normalised hashtags for ``pillar``: core + pillar + extras.

    Tags are de-duplicated case-insensitively (order preserved) and capped at
    ``limit`` by :func:`auto_instagram.caption.normalize_hashtags`.
    """
    if pillar not in PILLARS:
        raise ValueError(f"unknown pillar {pillar!r}; expected one of {PILLARS}")

    bank = bank if bank is not None else load_hashtag_bank()
    core = bank.get("core", [])
    pillar_tags = bank.get("pillars", {}).get(pillar, [])
    combined = [*core, *pillar_tags, *extra]
    return normalize_hashtags(combined, max_hashtags=limit)


def build_post_caption(
    hook: str,
    body: str = "",
    pillar: str = "wealth_mindset",
    *,
    cta: str | None = None,
    extra_hashtags: Iterable[str] = (),
    add_disclaimer: bool | None = None,
    limit_hashtags: int = MAX_HASHTAGS,
    bank: dict | None = None,
    **caption_kwargs,
) -> str:
    """Assemble a full caption for a post in ``pillar``.

    The body is the ``body`` text followed (each on its own line) by an
    optional ``cta`` and, for the investing pillar, a short :data:`DISCLAIMER`.
    Hashtags come from :func:`select_hashtags`. Extra keyword arguments (e.g.
    ``truncate=True``) are passed through to
    :func:`auto_instagram.caption.build_caption`.
    """
    if add_disclaimer is None:
        add_disclaimer = pillar == "investing_basics"

    body_lines = [line for line in (body, cta) if line]
    if add_disclaimer:
        body_lines.append(DISCLAIMER)
    body_text = "\n".join(body_lines)

    hashtags = select_hashtags(
        pillar, extra=extra_hashtags, limit=limit_hashtags, bank=bank
    )
    return build_caption(hook, body_text, hashtags, **caption_kwargs)
