# Auto-Instagram: GTA 6 clip page

Sourcing, clipping and posting for a faceless GTA 6 fan page: Instagram Reels and YouTube Shorts first, TikTok for the extras. GTA 6 only.
Takes long videos and live streams and cuts them into short-form clips, never the same moment twice.

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
| `tools/autoclip.py` | long video / live stream → scored moments → cut + captioned shorts |
| `tools/registry.py`, `registry/used.jsonl` | no-repeat registry (time ranges + scene fingerprints) |
| `tools/make_clip.py` | renders a clip spec into an upload-ready vertical MP4 |
| `tools/transcribe.py` | speech → timed caption labels (Whisper) |
| `tools/post_instagram.py` | publishes a clip as a Reel via the Instagram Graph API (dry run unless `--confirm`) |
| `tools/fetch_official.sh` | downloads the official trailers from Rockstar's media page |

## Long video / live stream → shorts (main workflow)

```bash
# 1. Score a stream: pulls audio only, transcribes, ranks moments, skips anything already clipped
python3 tools/autoclip.py scan https://www.twitch.tv/videos/<id> --last 45 --creator <handle> --thumbs
#    -> media/raw/<source>/candidates.md (+ thumbs/ frame strips)

# 2. Cut a moment: downloads just that part in 1080p60, checks for repeats, captions it, renders
python3 tools/autoclip.py cut twitch-<id> --start 7010.5 --end 7049 \
    --facecam 0,0,0.258,0.256 --hook "FIRST LOOK AT THE *FULL GTA 6 MAP*" --line "One sentence for the caption."
```

- `--facecam x,y,w,h` is where the webcam sits, as fractions of the frame (top-left 25% → `0,0,0.25,0.25`). It gives the facecam-top / gameplay-bottom layout. Leave it out for no-facecam videos.
- Moments with nudity or sexual content are dropped from the shortlist automatically. Still watch every clip before posting.
- `registry/used.jsonl` records every moment we've cut (source + time + scene fingerprint). `cut` refuses a repeat.
- Works with anything yt-dlp supports: Twitch VODs (including a broadcast that's still live), Kick, YouTube, local files (`scan --file video.mp4`).

### YouTube sources: run it on your own computer

YouTube blocks downloads from cloud servers ("confirm you're not a bot"), but it works from a home connection. On a Mac or PC with Python 3.10+:

```bash
pip install -U "yt-dlp[default]" faster-whisper pillow numpy
```

Plus ffmpeg (`brew install ffmpeg` on Mac, `winget install ffmpeg` on Windows) and Node.js. Then run the same `scan` / `cut` commands with a YouTube URL.
Or connect your computer to the Claude session (Claude desktop app → Settings → Claude Code → Remote Control) so Claude can run it there.

## Make a clip from a spec

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
