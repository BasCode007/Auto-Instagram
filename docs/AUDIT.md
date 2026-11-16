# Audit — November 2026

A full review of the system by **running it**, not reading it. Until this audit
no part of the pipeline had ever been executed: every earlier check was a
syntax check or a mock. The result was a stack that could not have worked.

## Showstoppers found (all fixed)

Each of these alone meant zero videos would ever have been produced.

| # | Problem | How it was found | Fix |
|---|---|---|---|
| 1 | **Docker image did not build.** `n8nio/n8n:latest` is now 2.x on a hardened base with no `apk`; the Dockerfile's first `RUN` exited 127. | `docker build` | No custom n8n image. Rendering moved to its own `renderer` container. |
| 2 | **Render nodes could not load.** n8n 2.x disables the Execute Command node: `Unrecognized node type`. | ran it on n8n 2.47.3 | n8n calls the renderer over HTTP; no Execute Command. |
| 3 | **Every credential lookup was denied.** n8n 2.x blocks `$env` in expressions: `access to env vars denied`. | ran it | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` in compose. |
| 4 | **Render commands were never evaluated.** The command strings embedded `={{ }}` mid-string, so n8n passed the template text literally. | read the JSON, confirmed by run | Removed with the Execute Command nodes. |
| 5 | **A rejected video looped forever.** The status poll only looked for `FINISHED`; `ERROR`/`EXPIRED` waited eternally. | mock returning `ERROR` | Bounded poll (20 tries); `ERROR`/`EXPIRED` stops with a clear message. |

## Would have published, badly (all fixed)

| Problem | Evidence | Fix |
|---|---|---|
| Captions carried 8–18 hashtags; Instagram's limit has been **5** since December 2025. | Instagram announcement; prompts asked for 8–15 | Capped at 5 in the library, tag bank, prompts and workflow. |
| On-screen hook was cut off on both sides. | rendered frame | Hook and captions rendered with libass, which wraps. |
| Narrated Reels had no captions after the first 3.5s. | rendered frame | Word-timed burned-in captions from ElevenLabs timestamps. |
| Quote text filled the whole frame and sat under Instagram's own buttons and caption overlay. | rendered frame | Sized by length; laid out inside the Reels safe zone. |
| Quote cards had no audio stream. | `ffprobe` | Always an AAC track; optional licensed music from `assets/music/`. |
| Same stock clip for the same keyword every time; three long clips per video. | read the code | Shuffled picks; a cut roughly every 4–5 seconds; 1080-wide renditions rather than 4K. |
| Pinned Graph API **v21.0 — now the oldest supported version**, next to be retired. | live: v19/v20 answer as v21 | Default v27.0, configurable. |

## Would have decayed over time (all fixed)

| Problem | Fix |
|---|---|
| No memory: the same prompt each day meant the same few posts on a loop. | The workflow remembers recent hooks and tells the model not to repeat them; 7 angles × 6 pillars rotate. |
| Failures were silent. | A second workflow alerts via Telegram on any failure; the main one retries flaky calls. |
| No compliance backstop beyond the prompt. | Posts containing "guaranteed returns", "risk-free" etc. are refused before rendering. |
| Setup needed ~10 manual steps in the n8n UI. | Zero: workflows import and activate themselves; all settings come from `.env`. |
| A public URL, tunnel and Access policy were required. | Only for Telegram approve buttons. Autopilot is outbound-only. |

## Still open — decisions and limits, not bugs

- **Token expiry.** Instagram Login tokens last 60 days and must be refreshed.
  The verifier warns; nothing refreshes it automatically yet. A Facebook Login
  System User token does not expire.
- **Voice quota.** One narrated Reel is ~700 characters. The verifier now
  reports remaining quota; check it covers your posting rate on your plan.
- **Music.** The API cannot attach Instagram's music library. Supply your own
  licensed tracks or videos are voice-only / silent.
- **Content quality.** The engine guarantees variety and compliance, not
  distinctiveness. Faceless finance content is a crowded field; the voice in
  `config/niche.md` and the prompts in `n8n/build_workflow.py` decide results.
- **Unverified here:** real Instagram, ElevenLabs, Pexels and Cloudinary calls
  (no credentials in the audit environment — exercised against mocks that
  follow each API's documented shape), and the Telegram approval round trip.

## How it is tested now

- `python -m unittest discover -s tests` — library and verifier.
- `tests/e2e/run.sh` — boots real n8n and the real renderer against mock APIs
  and runs the whole workflow: script → render → container → poll → publish.
