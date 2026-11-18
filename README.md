# Auto-Instagram: GTA 6 clip page

Sourcing, clipping and posting for a faceless GTA 6 fan page on Instagram and TikTok. GTA 6 only.

**Start here:** [`media/edits/QUEUE.md`](media/edits/QUEUE.md) (clips ready to upload) · [`playbook.md`](playbook.md) (rules, mix, launch plan, open questions)

## What's here

| Path | Purpose |
|---|---|
| `playbook.md` | account setup, voice, daily mix, clip/caption/credit rules, launch-day plan |
| `facts.md` | verified facts only, each linked to Rockstar/PlayStation/Xbox |
| `idea-bank.md` | drafts by pillar (ready / draft / post-launch) |
| `watchlist.md` | official sources, creators, subreddits to monitor |
| `clips/*.json` | one spec per clip: source, cuts, hook, labels, captions |
| `media/edits/` | finished 1080x1920 MP4s + covers + captions |
| `media/raw/` | source footage (not committed; see `SOURCES.md`) |
| `log.md`, `scoreboard.csv`, `learning.md`, `takedowns.md` | tracking and the learning loop |
| `tools/make_clip.py` | renders a clip spec into an upload-ready vertical MP4 |
| `tools/transcribe.py` | speech → timed caption labels (Whisper) |
| `tools/post_instagram.py` | publishes a clip as a Reel via the Instagram Graph API (dry run unless `--confirm`) |
| `tools/fetch_official.sh` | downloads the official trailers from Rockstar's media page |

## Make a clip

```bash
pip install pillow                     # faster-whisper too, for transcribe.py
bash tools/fetch_official.sh           # ~3 GB of 4K trailers into media/raw/
python3 tools/make_clip.py clips/001-out-now.json
python3 tools/make_clip.py clips/*.json --preview   # fast low-quality check
```

Requires `ffmpeg`. Copy an existing spec in `clips/` to start a new one. In hook text, wrap words in `*asterisks*` to colour them.
Layouts: `fit` (blurred background + 4:3 shot, default) or `full` (9:16 crop; set `"x"` per segment to frame the subject).
Letterbox bars in the source are detected and cropped automatically. Render one clip at a time on small machines; 4K decoding is memory-hungry.

## Rules that don't bend

- Credit every clip. Official footage: `🎥 @rockstargames`.
- No leaks, datamines, piracy, exploits or "play early" tricks. Ever.
- Not affiliated with Rockstar. Never imply otherwise.
- Same-day takedowns on request.
- Nothing gets posted without approval of the exact clip and caption.

Fonts: Inter (SIL Open Font License, `tools/fonts/LICENSE-Inter-OFL.txt`).
