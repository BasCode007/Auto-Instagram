# Auto-Instagram

An automatic system for sourcing content and posting it to Instagram.

## Status

Early scaffold. The first self-contained piece — building well-formed post
captions — is implemented and tested. Sourcing, publishing and scheduling are
still to come (see the roadmap).

## Project structure

```
auto_instagram/      # package
  caption.py         # build & validate Instagram captions (implemented)
tests/
  test_caption.py    # unit tests for the caption builder
```

## Usage

The caption builder is pure standard library — no credentials or network
access required.

```python
from auto_instagram import build_caption, validate_caption

caption = build_caption(
    "Sunset over the harbour",
    "Golden hour never disappoints.",
    ["#sunset", "Sunset", "golden hour"],   # deduped, normalised for you
)
print(caption)
# Sunset over the harbour
#
# Golden hour never disappoints.
#
# #sunset #goldenhour

validate_caption(caption)  # [] means it fits Instagram's limits
```

It enforces Instagram's published limits (2,200 characters, 30 hashtags),
normalises tags (strips stray `#`/whitespace, folds out illegal characters,
de-duplicates case-insensitively), and can truncate an over-long body to fit
while preserving the title and hashtags (`build_caption(..., truncate=True)`).

## Running the tests

```bash
python -m unittest discover -s tests
```

## Roadmap

- [ ] **Content sourcing** — pull candidate posts (media + metadata) from a
      source such as a local folder, an RSS feed, or a third-party API.
- [ ] **Publishing** — authenticate and push a built caption + media to
      Instagram (e.g. via the Graph API or a client library).
- [ ] **Scheduling** — queue built posts and publish them at configured times.
