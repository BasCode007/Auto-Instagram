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

### Creator on screen, no watermark (owner, 20 Nov)

- **The creator must be visible in every clip.** Use the stack layout: their cam on top, gameplay below. Lacy: facecam `0,0,0.258,0.256`. TheBurntPeanut has no webcam but shows a peanut avatar bottom-left: day-2+ footage `--facecam 0.14,0.66,0.31,0.34 --facecam-h 640`; day-1 footage `0.10,0.70,0.285,0.30`. Check a frame first; the avatar can move between streams.
- **No on-screen "@creator on Twitch" credit.** `make_clip.py` no longer draws it (set `"credit_on_screen": true` to bring it back). The credit lives in the caption/description: "🎥 Name, twitch.tv/channel".
- Fact videos keep their full-screen phone shots but drop the watermark too.

### Content mix: reactions + "did you know" facts (owner, 20 Nov)

Mostly reactions and funny stream moments (they win: 1.2k to 1.6k views per Peanut Reel), plus **about 1 fact video for every 3 reactions**.

Fact video recipe (`clips/fact-*.json`):
1. A real discovery seen on stream (a feature, app, price, rule, mechanic). Every fact must be readable on screen in the footage or in an official Rockstar source; list them in the spec's `facts`. No rumours, no story or mission spoilers.
2. Background footage from the creator's Twitch stream/VOD, credited on screen and in the caption exactly like a clip. Not other pages' reposts, and no YouTube downloads.
3. Script: hook "Did you know..." line, 4 to 6 short lines, payoff, "Follow for more GTA 6 secrets." About 30 to 40 s.
4. Voice: vidIQ `vidiq_voiceover_generate` with `scriptLines` (Liam, TX3LPaxmHKxFdv7VOQHJ; ~28 credits per video). Line timings set the scene cuts.
5. Render picture with `make_clip.py` (no words, `caption_y` 1640 so captions sit under phone screens), then burn voiceover captions (`write_ass` on a whisper transcript of the MP3) and mix: game audio at 15%, voice on top, loudnorm -14 LUFS.
6. Instagram topic tag `#GTA6Tips`; TikTok `#gta6tips`.

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
| Launch week only | **every 30 minutes per account** (owner's call, 19 Nov), as long as the clips are good | first-look gameplay, map, hidden details, funny moments, new features |

Pillars: official news · tips and tutorials · gameplay clips (credited) · GTA 5 nostalgia · spotlights · countdown/daily recap · questions.
Quality beats volume. Skip a slot rather than post something weak or unverified.

## TikTok: staying eligible for the For You feed

TikTok keeps four kinds of content out of For You (the "FYF eligibility standards"): behavioural health, sensitive and mature themes, integrity and authenticity, regulated goods. For a GTA clip page that means:

- **No clip built around guns, gun shops, armed robbery, drugs or alcohol** on TikTok. Fictional or not, weapons and drugs are "regulated goods". Those clips go to YouTube and Instagram only (`"platforms": {"tiktok": false}` in the clip spec).
- **Swear words are muted in the audio** (`make_clip.py` does it automatically from the word timings) as well as masked in the captions. No slurs, sexual jokes, nudity or self-harm jokes ("I'll kill myself") at all.
- **Add something original to every clip**: our hook, captions, a tight cut, the credit. A plain re-upload of someone else's stream counts as "unoriginal content" (integrity and authenticity).
- **New accounts:** use the account like a person for the first days (watch and like GTA videos, finish the bio and avatar, post one or two clips natively from the phone with a trending sound) before scheduling lots of posts through vidIQ. Space posts at least 90 minutes apart.
- **Never Promote clips of other creators' streams.** Ads must be original content, so Promote rejects them (the refund goes back to the Promote balance).
- **Keep "Audience controls" off.** If the profile says "This creator turned on audience controls" to logged-out viewers, the account or its videos are limited to adults (18+) and get almost no For You reach.
- If a video shows "not eligible for recommendation" in its analytics, appeal it from the video's analytics page, then check Settings and privacy → Account → Account status.

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

### Narrated story Shorts: main format (owner said "go", 21 Nov)

Based on research/competitor-vicepulse.md (VicePulse: 18.4M views in 8 weeks with 14-25 s narrated Shorts).

1. **Length:** narrated stories 15-25 s; reactions 20-35 s max; nothing over 40 s.
2. **Hook in the first 2 s:** narrator line plus top banner that challenges or teases: "There's a ... in GTA 6?!", "You can't ...", "Stop saying ...", "Imagine ...", "Nobody noticed ...".
3. **Story:** 4-5 lines at about 3 words/s: hook, what happened, the twist, payoff, a question for comments ("Would you ...?"). End on the payoff with no outro, so it loops.
4. **Facts:** every claim must be visible in the footage (list them in `facts`). No speculation, no made-up numbers, no non-GTA-6 footage. This is our edge over channels using modded GTA 5.
5. **Picture:** real Twitch footage only. Creator stays visible in a smaller top band (`facecam_h` about 480-540) so the game fills most of the screen. Punch in with per-segment `"zoom"` and `"y"` so the key thing (creature, text, number) is big on a phone.
6. **Voice:** vidIQ Liam (TX3LPaxmHKxFdv7VOQHJ, `scriptLines`), line timings set the cuts; game audio 15%; word-by-word captions (whisper on the MP3 + `write_ass`).
7. **Titles:** a broad GTA 6 question, not the streamer's name: "There's A Bigfoot Hiding In GTA 6?!". Creator credit in the description and caption.
8. **YouTube pace:** 3-4 Shorts a day, spread 16:00-23:00 UTC (US afternoon/evening). Best first. Instagram stays every 30 min, TikTok every 90 min.
9. **Template:** clips/story-skunk-ape.json.

### Owner rules, 21 Nov (evening): override anything above that conflicts

1. **Preview first.** Every new clip is sent to the owner in chat to watch before any draft is made. Nothing is drafted or posted without a preview and an explicit yes.
2. **Hashtags: at least 10 on every post, every platform** (Instagram caption, TikTok caption, YouTube Shorts description). Always: #GTA6 #GTAVI #GTA6Clips #ViceCity #GrandTheftAuto #GTA6Gameplay #Gaming #GamingClips #RockstarGames #Leonida, then 2-4 topic tags (#GTA6Funny, #GTA6Secrets, #GTA6Tips, #GTA6Physics...), plus #Shorts on YouTube. Creator hashtag only on reaction clips.
3. **Narrated stories and fact videos: clean picture, voice only.**
   - Streamer audio at 0 (game/stream audio fully muted; voiceover only, optional quiet music).
   - No facecam, no avatar, no streamer overlays: `layout: "full"` 9:16 crop of the gameplay, `x`/`zoom`/`y` per segment to keep the action centred and corner overlays out.
   - The narration never names the streamer or the stream, and there is no credit line anywhere (owner's call, 21 Nov): not on screen, not in the caption or description.
4. **Reactions** (streamer moments) keep the stack layout with the creator visible and their voice, 12-35 s (12 s minimum since 25 Nov).

### Owner rules, 25 Nov: content rules relaxed ("we are established")

These override the older safety lists (21 Nov SAFETY line, launch-week spoiler rule, 20 s reaction minimum).

**Now allowed**
- **Night and dark footage**, as long as the action is easy to read on a phone screen (check a frame at phone size; brighten with `eq` if needed).
- **Edgy and crude humour**: mild innuendo, crude jokes, swimsuit/revealing outfits in game. Still no nudity, nothing sexually explicit, and keep it out of the hook and cover frame.
- **In-game drug and alcohol references** (NPC lines, streamer jokes). These clips go to YouTube and Instagram only: `"platforms": {"tiktok": false}` (TikTok regulated-goods rule still stands).
- **Short reactions from 12 s** (quick punchline clips). Upper limit stays 35 s.
- **Story and mission moments** that streamers react to. The hook and cover must not give away the twist; add "SPOILER" (or "⚠️ spoilers") at the start of every caption/description; no ending or final-mission content.

**Still banned (platform strikes)**: real or in-game nudity / explicit sexual content, slurs, real-world harm or animal harm, gore close-ups, self-harm jokes, off-game content, unverified claims, static menus, repeats.

**Unchanged**: swears stay muted; preview first; 10+ hashtags; narrated/fact video rules (voice only, no facecam, never name the streamer, no credit line).

### Owner rule, 25 Nov: YouTube Shorts 3 hours apart
YouTube Shorts go out at least 3 h apart on a 13:50 / 16:50 / 19:50 / 22:50 UTC grid (max 4 a day). Long-form keeps its own slot. Instagram (hourly) and TikTok (90 min) unchanged. Owner is verifying the channel to raise YouTube's daily upload limit.
