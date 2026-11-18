# Ready to upload

## Launch-night stream clips (post these first, they're the freshest)

Facecam on top, gameplay below, word-by-word captions, 1080x1920 at 60 fps. Credit is on screen and in every caption.
Post to **Instagram Reels + YouTube Shorts**; TikTok too.

| Clip | Hook | Length | Source |
|---|---|---|---|
| `lacy-map-first-look.mp4` | FIRST LOOK AT THE FULL GTA 6 MAP | 38s | Lacy, Twitch |
| `lacy-snake-dolores.mp4` | JASON HAS A PET SNAKE NAMED DOLORES | 25s | Lacy, Twitch |
| `lacy-fridge.mp4` | JASON'S FRIDGE IS TOO REAL | 22s | Lacy, Twitch |
| `lacy-shoe-store.mp4` | GTA 6 HAS REAL SHOE STORES | 28s | Lacy, Twitch |
| `peanut-ammu-nation.mp4` | AMMU-NATION IS BACK IN GTA 6 | 29s | TheBurntPeanut, Twitch |
| `xqc-mirror-shave.mp4` | YOU CAN SHAVE JASON IN GTA 6 | 27s | xQc, Twitch |
| `xqc-collectible-card.mp4` | GTA 6 HAS COLLECTIBLE CARDS | 33s | xQc, Twitch |
| `lacy-cops-know-outfit.mp4` | GTA 6 COPS REMEMBER YOUR OUTFIT | 20s | Lacy, Twitch (tip) |
| `lacy-real-hotel.mp4` | HE'S BEEN TO THIS HOTEL IN REAL LIFE | 21s | Lacy, Twitch |

Lacy's stream title includes `!CLIPPING`; he invites clippers. Keep the credit on every post.

## Trailer clips (batch 1)

Batch 1: six vertical clips, all from official Rockstar trailers (rockstargames.com/VI/media).
Each clip has a `_cover.jpg` (Reel/TikTok cover) and a `_captions.txt` (Instagram, TikTok, Shorts and X captions).
**Nothing has been posted.** Each one needs your OK first (playbook.md, approval rules).

| Order | Clip | Length | Pillar | When to post |
|---|---|---|---|---|
| 1 | `001-out-now.mp4`: GTA 6 IS OUT NOW | 22s | official news | The moment it's visibly live in the first region (NZ unlocks 11:00 UTC Nov 18). Confirm with real player posts first. |
| 2 | `002-5-things-to-know.mp4`: 5 THINGS TO KNOW BEFORE YOU PLAY | 16s | tips | Launch day, late morning |
| 3 | `005-13-years-los-santos.mp4`: 13 YEARS OF LOS SANTOS | 11s | nostalgia | Launch day, evening |
| 4 | `003-ps5-pro-extra.mp4`: PS5 PRO GETS SOMETHING EXTRA | 13s | spotlight | Day 2 |
| 5 | `004-meet-brian-heder.mp4`: JASON'S LANDLORD IS A DRUG RUNNER | 17s | spotlight | Day 2 or 3 |
| 6 | `006-only-in-leonida.mp4`: LEONIDA SOCIAL MEDIA IS UNHINGED | 10s | gameplay clip | Day 3 |

## Manual upload (until a scheduler or API is connected)

**Instagram (Reel):** + → Reel → pick the MP4 → Next → paste the INSTAGRAM caption from `_captions.txt` →
Edit cover → "Add from camera roll" → `_cover.jpg` → keep "Also share to feed" on → Share.

**TikTok:** + → Upload → pick the MP4 → Next → paste the TIKTOK caption → Select cover → Post.

**If a platform mutes the audio** (trailer songs are licensed): mute the original sound in the app and add a trending sound from the app's library.

After posting, add a row to log.md and scoreboard.csv (post_id, date, time, platform, pillar, hook, length, credit). Fill views at 12h, 24h and 72h.

## Automated Instagram posting

`python3 tools/post_instagram.py clips/<id>.json` shows exactly what would be posted.
Add `--confirm` to publish. It needs `IG_USER_ID` and `IG_ACCESS_TOKEN` in `.env`. The Instagram connection in the build session didn't authenticate, so this hasn't been run live yet.
