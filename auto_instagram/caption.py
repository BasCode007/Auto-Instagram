"""Build and validate Instagram post captions.

This module is intentionally dependency-free (standard library only) so it can
be used and tested without Instagram credentials or network access. It handles
the small-but-fiddly job of turning a title, body and a set of tags into a
well-formed caption that respects Instagram's published limits:

* Captions may be at most 2,200 characters long.
* A post may contain at most 30 hashtags.
* Hashtags may only contain letters, numbers and underscores; a space (or any
  other character) ends the tag, so ``"foo bar"`` is really the tag ``foo``.

The functions here normalise tags into that shape, assemble the caption, and
(optionally) truncate an over-long body so the caption still fits.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = [
    "MAX_CAPTION_LENGTH",
    "MAX_HASHTAGS",
    "normalize_hashtag",
    "normalize_hashtags",
    "count_hashtags",
    "build_caption",
    "validate_caption",
]

#: Maximum number of characters Instagram allows in a caption.
MAX_CAPTION_LENGTH = 2_200

#: Maximum number of hashtags Instagram counts on a single post.
MAX_HASHTAGS = 30

_SECTION_SEPARATOR = "\n\n"
_ELLIPSIS = "…"  # single-character "…"

# A hashtag body is a run of word characters (letters, digits, underscore).
# ``re.UNICODE`` is the default for ``str`` patterns, so non-Latin tags work.
_NON_TAG_CHARS = re.compile(r"[^\w]", re.UNICODE)
_HASHTAG = re.compile(r"#\w+", re.UNICODE)


def normalize_hashtag(tag: str) -> str | None:
    """Return ``tag`` as a canonical ``#hashtag`` string, or ``None``.

    Leading ``#`` and surrounding whitespace are stripped, then every
    character that Instagram would not treat as part of the tag is removed
    (so ``"# Sun set!"`` becomes ``"#Sunset"``). ``None`` is returned when
    nothing usable remains.
    """
    cleaned = _NON_TAG_CHARS.sub("", tag.strip())
    if not cleaned:
        return None
    return f"#{cleaned}"


def normalize_hashtags(
    tags: Iterable[str], *, max_hashtags: int = MAX_HASHTAGS
) -> list[str]:
    """Normalise an iterable of tags, dropping blanks and duplicates.

    Order is preserved, comparison for de-duplication is case-insensitive
    (Instagram hashtags are not case-sensitive), and the result is capped at
    ``max_hashtags`` entries.
    """
    result: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = normalize_hashtag(tag)
        if normalized is None:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if len(result) >= max_hashtags:
            break
    return result


def count_hashtags(text: str) -> int:
    """Count the hashtags present in an arbitrary block of text."""
    return len(_HASHTAG.findall(text))


def _assemble(title: str, body: str, hashtag_block: str) -> str:
    """Join the non-empty caption sections with blank lines between them."""
    return _SECTION_SEPARATOR.join(
        section for section in (title, body, hashtag_block) if section
    )


def build_caption(
    title: str,
    body: str = "",
    hashtags: Iterable[str] = (),
    *,
    max_length: int = MAX_CAPTION_LENGTH,
    max_hashtags: int = MAX_HASHTAGS,
    truncate: bool = False,
) -> str:
    """Assemble a caption from a title, body and hashtags.

    The pieces are stacked as ``title`` / ``body`` / hashtag block, separated
    by blank lines, with any empty section omitted. Hashtags are normalised
    (see :func:`normalize_hashtags`) and capped at ``max_hashtags``.

    If the assembled caption exceeds ``max_length``:

    * with ``truncate=False`` (the default) a :class:`ValueError` is raised;
    * with ``truncate=True`` the *body* is shortened with a trailing ellipsis
      so the caption fits, keeping the title and hashtags intact.

    A :class:`ValueError` is still raised when the title and hashtags alone do
    not fit, because there is nothing left to trim.
    """
    if max_length <= 0:
        raise ValueError("max_length must be positive")

    title = title.strip()
    body = body.strip()
    hashtag_block = " ".join(normalize_hashtags(hashtags, max_hashtags=max_hashtags))

    caption = _assemble(title, body, hashtag_block)
    if len(caption) <= max_length:
        return caption

    if not truncate:
        raise ValueError(
            f"caption is {len(caption)} characters, exceeding the "
            f"{max_length}-character limit"
        )

    # Scaffolding = everything except the body. Truncation only touches the
    # body, so if the scaffolding already overflows there is nothing to do.
    scaffold = _assemble(title, "", hashtag_block)
    if len(scaffold) > max_length:
        raise ValueError(
            f"title and hashtags are {len(scaffold)} characters, exceeding the "
            f"{max_length}-character limit; cannot fit by truncating the body"
        )

    # Adding a non-empty body also introduces one section separator whenever
    # another section is present.
    separator_cost = len(_SECTION_SEPARATOR) if scaffold else 0
    budget = max_length - len(scaffold) - separator_cost
    if budget <= 0:
        # No room for any body once the separator is accounted for; drop it.
        return scaffold

    keep = max(0, budget - len(_ELLIPSIS))
    truncated_body = body[:keep].rstrip() + _ELLIPSIS
    return _assemble(title, truncated_body, hashtag_block)


def validate_caption(
    caption: str,
    *,
    max_length: int = MAX_CAPTION_LENGTH,
    max_hashtags: int = MAX_HASHTAGS,
) -> list[str]:
    """Return a list of human-readable problems with ``caption``.

    An empty list means the caption is within Instagram's limits. This is
    handy for surfacing warnings in a UI or CLI without raising.
    """
    problems: list[str] = []

    length = len(caption)
    if length > max_length:
        problems.append(
            f"caption is {length} characters, {length - max_length} over the "
            f"{max_length}-character limit"
        )

    tag_count = count_hashtags(caption)
    if tag_count > max_hashtags:
        problems.append(
            f"caption has {tag_count} hashtags, {tag_count - max_hashtags} over "
            f"the {max_hashtags}-hashtag limit"
        )

    return problems
