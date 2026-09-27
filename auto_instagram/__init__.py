"""Auto-Instagram: tools for sourcing and posting Instagram content.

Only the caption-building utilities are implemented so far; the sourcing and
publishing pieces below need external services (and credentials) and are
tracked as TODOs.
"""

from __future__ import annotations

from .caption import (
    MAX_CAPTION_LENGTH,
    MAX_HASHTAGS,
    build_caption,
    count_hashtags,
    normalize_hashtag,
    normalize_hashtags,
    validate_caption,
)
from .content import (
    DISCLAIMER,
    PILLARS,
    build_post_caption,
    load_hashtag_bank,
    select_hashtags,
)

__all__ = [
    "MAX_CAPTION_LENGTH",
    "MAX_HASHTAGS",
    "build_caption",
    "count_hashtags",
    "normalize_hashtag",
    "normalize_hashtags",
    "validate_caption",
    "DISCLAIMER",
    "PILLARS",
    "build_post_caption",
    "load_hashtag_bank",
    "select_hashtags",
]

__version__ = "0.1.0"

# TODO: content sourcing — pull candidate posts (images/videos + metadata) from
#       a source such as a local folder, an RSS feed, or a third-party API.
# TODO: publishing — authenticate and push a built caption + media to Instagram
#       (e.g. via the Graph API or a client library). Needs credentials, so it
#       lives behind this interface rather than being called directly here.
# TODO: scheduling — queue built posts and publish them at configured times.
