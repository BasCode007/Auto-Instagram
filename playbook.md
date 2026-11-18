# Playbook: faceless GTA 6 clip page

Customized from "Faceless GTA 6 Clipping Page: Full Setup Prompt". GTA 6 only. Nothing else gets posted.

## Account (fill in; see open questions at the bottom)

| | |
|---|---|
| Page name | **TBD** (accounts being created; distinct and searchable, never copy a big page's name) |
| Handle | **TBD**, same on every platform, includes "GTA6" if free |
| Platforms | **Main: Instagram Reels + YouTube Shorts.** TikTok gets the extra clips (bulk uploads). All Creator accounts |
| Time zone | **Sydney, Australia (AEDT, UTC+11).** GTA 6 unlocks here at 00:00 Nov 19 AEDT (13:00 UTC Nov 18) |
| Approval hours | Owner is up through launch night posting live |
| Niche angle | **Every side of GTA 6, as fast as possible.** Launch-week focus: first reactions, map, NPCs, funny moments, hidden details, from the biggest streams and videos |
| Core workflow | **Long video / live stream → many short clips** (`tools/autoclip.py`). One moment = one clip, never cut twice |
| Tools | Clipper: `tools/autoclip.py` + `tools/make_clip.py`. Scheduler: none yet (manual upload). Storage: this repo |

### Content rules from the owner

- **No repeats.** A moment (same source + time range, or the same scene from a different upload) is clipped once. `registry/used.jsonl` enforces it; `autoclip.py cut` refuses repeats.
- **Lengths.** Reels/TikTok: 15 to 45 s. YouTube Shorts: the same clip, or a slightly longer cut (45 to 120 s) when the moment needs it. Never two clips of the same moment, one per platform is fine.
- **Quality bar: better and faster than other clip pages.** 1080x1920, 60 fps, facecam on top / gameplay below, word-by-word captions, a hook in the first second.
- **Sources:** Twitch / Kick launch streams and VODs (download fine from the cloud); YouTube videos (blocked from the cloud; see README for running on your own computer).
- **Creator mix (rough guide, not a quota).** About **50% TheBurntPeanut** (funny, strong engagement), the other **50% split across IShowSpeed, Lacy, xQc and TypicalGamer**. Quality wins: when one creator is having a better or busier stream, clip more of them; never post a weak clip just to hit the mix. Others (Kai Cenat, new discoveries) only when a moment is clearly great. `tools/creator_mix.py` shows the current split.

### Profile setup checklist (both platforms)

- [ ] Bio: `GTA 6 news, tips and the best clips, fast. Fan page, not affiliated with Rockstar Games.` Never "official".
- [ ] Avatar: simple mark that reads small (letter mark, neon palm, map pin). No Rockstar logo or key art.
- [ ] Instagram: switch to a Professional account (Creator or Business). Needed for auto-publishing and insights.
- [ ] TikTok: switch to a Business or Creator account for analytics.
- [ ] Link the accounts (Instagram profile link on TikTok; TikTok link on Instagram).
- [ ] Pin a "what this page is" post, then replace it with the best performer after launch.

## Voice

Hype but clean. Short, punchy headlines. Sentence case in captions, ALL CAPS only for the on-screen hook.
One emoji max as an accent (the 🎥 in the credit line doesn't count). Always write "GTA 6".
Never clickbait anything the clip doesn't deliver. Never sound like Rockstar.

## Daily mix (Instagram + TikTok)

1 to 2 vertical clips a day per platform; the same clip goes to both, with platform-specific captions.

| Slot | Default time (local) | Pillar |
|---|---|---|
| Late morning | 11:00 | Official news recap or HOW TO tip |
| Early evening | 18:00 | Gameplay clip, spotlight, or nostalgia one-liner |
| Launch week only | every 1 to 2 hours in the first 48h after unlock | first-look gameplay, map, hidden details, early tips |

Pillars: official news · tips and tutorials · gameplay clips (credited) · GTA 5 nostalgia · spotlights · countdown/daily recap · questions.
Quality beats volume. Skip a slot rather than post something weak or unverified.

## Clip rules (every clip)

1. Hook on screen in the first second.
2. 7 to 30 seconds. Cut dead air. End on the payoff.
3. Burned-in text, large, inside the safe area (many people watch muted).
4. Add value: a tip, labels, commentary, captions of dialogue. Instagram demotes plain reposts.
5. No story spoilers in the hook or cover during launch week. Label story clips "SPOILER" in the caption.
6. M-rated game: skip nudity frames entirely. Skip strip-club and sexual content.
7. Export 1080x1920, H.264 + AAC, 30 fps, MP4 (`make_clip.py` does this).

## Caption rules

- **Instagram:** hook line, one or two sentences of value, credit line, then 3 to 5 hashtags (Instagram caps posts at 5).
- **TikTok:** short caption plus a few relevant hashtags.
- **X (if added):** no hashtags. Headline, blank line, bullets, credit last.
- Credit every clip on its own line: `🎥 @creator`. Official material: `🎥 @rockstargames`.
- Every fact must be in facts.md. Don't repeat the same caption or one-liner within a week.

## Credit and permission

1. Public posts only. Skip anything protected, deleted, or taken down.
2. Credit is not permission. When a creator is reachable, ask first: "Love this clip, ok if we share it with credit?"
3. Transform it (hook, trim, captions, commentary). Never re-upload a whole video.
4. Takedown request: remove it the same day, log it in takedowns.md, don't use that creator again without permission.
5. Never post leaks, datamined files, leaked builds/maps/tracklists, pirated copies, "play early" tricks, or exploits. If you can't tell whether footage is official or leaked, don't use it.
6. Rockstar's footage is their property and fan pages run on their tolerance. Keep it respectful, never sell their content, never imply we're Rockstar. Read [Rockstar's policy on posting copyrighted material](https://support.rockstargames.com/articles/200153756/Policy-on-posting-copyrighted-Rockstar-Games-material) before monetizing anything.

## Music

Clips keep the trailer's own audio. Licensed songs in trailers can get a Reel muted or region-blocked.
If that happens, mute the original audio in the app and add a trending sound from the platform's own library.

## Launch-day "be first" playbook (Nov 19, 2026)

GTA 6 unlocks at midnight local time, so New Zealand plays first (00:00 NZDT = 11:00 UTC Nov 18),
then Australia and Asia, then Europe, then the Americas.

1. Post `001-out-now` the moment it's visibly live in the first region (first-player posts on X/Reddit, not guesses).
2. Watch early-time-zone streams and posts (watchlist.md). Clip the first strong moments: driving, map, graphics, NPCs, funny moments. **Opening story scenes are spoilers.**
3. Edit fast (hook, trim, captions, credit). Aim to post within 15 to 30 minutes of the moment.
4. Post every 1 to 2 hours through the first 48 hours.
5. Turn every repeated comment question into a HOW TO post the same day.
6. Being first means first after the legit unlock. Never pre-launch leaks.

## Engagement routine (2 to 3 times a day, ~15 minutes)

- Reply to comments on our posts in the first hour with real info.
- Reply under official Rockstar posts and big GTA posts with something useful, in our voice. No "follow me" spam.
- Thank and tag creators we credited.
- Save every good question to idea-bank.md.
- Never argue, never engage with leak drama, never DM people asking for follows.

## Approval rules

Needs your OK before posting: anything outside the normal mix, any rumor (must start with "RUMOR:"), any caption that could read as official,
any sponsorship or paid promo, any plan upgrade or purchase, any change to name or bio.

## Workflow files

| File | What it's for |
|---|---|
| facts.md | verified facts only, each with its official link |
| idea-bank.md | ready-to-go drafts by pillar |
| watchlist.md | official accounts, creators, streamers, subreddits |
| clips/*.json | one spec per clip: source, cuts, hook, labels, captions |
| media/edits/ | finished clips + covers + captions, ready to upload |
| log.md | every post that went out |
| scoreboard.csv | per-post metrics at 12h/24h/72h |
| learning.md | wins, losses, current rules, weekly reviews |
| takedowns.md | removal requests and what we did |

## Open questions for you

Answered: platforms (IG + Shorts main, TikTok extras), angle (every side of GTA 6, fast), time zone (Sydney), workflow (long video → shorts, no repeats).

Still open:
1. Page name and handle (once the accounts exist).
2. Upload: manual for now. Connecting Instagram / YouTube to an API or scheduler lets clips go out the moment you approve them.
3. Posts per day per platform. Launch week suggestion: as many strong clips as we can cut, every 1 to 2 hours.
4. Creators you like or want to avoid.
5. Voiceover style: text-only (current default), AI voice, or your own voice off camera.
