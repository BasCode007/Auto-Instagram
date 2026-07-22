# Auto-Instagram

An automated pipeline that **creates** short vertical videos for a finance /
wealth / success / positive-mindset account and **publishes** them to Instagram
through the official Graph API — with a human approval step before anything goes
live.

- **Publishing:** official Instagram Graph API (ToS-safe; Business/Creator
  account + linked Facebook Page).
- **Content:** two rotated formats — faceless **narrated Reels** and motion
  **quote cards**.
- **Control:** **review before posting** via Telegram approve/skip.
- **Runs on:** self-hosted **n8n** + local **ffmpeg**/**ImageMagick**, ElevenLabs
  voice, free Pexels footage and Cloudinary hosting. ~AUD 9–21/month.

## How it works

```
schedule → pick format+pillar → LLM script/quote + caption
        → render (narrated Reel | quote card) → upload to public URL
        → Telegram approve/skip → Graph API publish
```

See **[docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)** for the architecture,
flow diagram, and cost breakdown, and **[docs/SETUP.md](docs/SETUP.md)** for the
full setup (Meta app + tokens, API keys, host, and importing the workflow).

## Repository layout

```
n8n/              auto-instagram-workflow.json  ← import this into n8n
scripts/          render_narrated_reel.sh, render_quote_card.sh, upload_public.sh
prompts/          LLM system prompts for each format
config/           niche.md (brand + compliance), hashtags.json (tag bank)
auto_instagram/   caption + content library (canonical caption/hashtag rules)
tests/            unit tests for the library
docs/             SYSTEM_DESIGN.md, SETUP.md
```

## The caption/content library

`auto_instagram/` is the canonical, tested definition of how captions are built
(the n8n workflow mirrors the same rules in a Code node). It's pure standard
library — no credentials or network needed.

```python
from auto_instagram import build_post_caption

print(build_post_caption(
    "The habit that quietly builds wealth",
    "Automate a transfer the day you get paid. Pay yourself first, always.",
    "money_habits",
    cta="Save this for payday. 👇",
))
```

It enforces Instagram's limits (2,200 chars, 30 hashtags), normalises and
de-duplicates hashtags, pulls the right tag set for each content pillar, and
appends an "educational only, not financial advice" disclaimer on investing
posts.

## Running the tests

```bash
python -m unittest discover -s tests
```

## Compliance

Publishing is only via the official Graph API on an account you own. Content is
education/motivation, **not financial advice** — the prompts ban
guaranteed-return / risk-free / individual buy-sell language, and the
review-before-posting step keeps you in control of everything that ships. See
[config/niche.md](config/niche.md).
