# Posting: Instagram Reels + YouTube Shorts (+ TikTok)

## Recommended setup: vidIQ (already connected to Claude)

vidIQ can post to Instagram, YouTube, TikTok, X and Facebook from one draft, and schedule each destination
for its own time. Posting to Instagram, YouTube and TikTok costs no vidIQ credits.

### One-time connection (you do this; it never posts anything)

1. **Instagram**
   - Make sure the new GTA 6 account is a **Professional account (Creator or Business)**. In the app: Settings → Account type and tools.
   - On instagram.com, **log out of every other account** and log in as the new GTA 6 account.
     vidIQ currently has a *different* account linked ("money_motivation_central"). Don't approve the connection while logged in as that one.
   - Open the Instagram authorization link Claude gives you, approve, and tell Claude it's done.
2. **YouTube**
   - Open the YouTube link Claude gives you, pick the **new GTA 6 channel** (not a personal one), and tick every permission box.
3. **TikTok (optional)**: ask Claude for the TikTok connection card the same way.

### How each clip goes out

1. Claude renders the clip (1080x1920, H.264/AAC, 60 fps for streams) and checks it with `tools/phone_preview.py`.
2. Claude uploads the MP4 to vidIQ (`vidiq_video_upload` with the local file) and creates **one draft** for every destination:
   - Instagram Reel: the INSTAGRAM caption from `<clip>_captions.txt`
   - YouTube Short: the title (the hook in sentence case, under 100 characters), with the YOUTUBE_SHORTS text as the description and the privacy setting **you** choose
   - TikTok (optional): privacy, comments and music confirmation are **your** choices
3. You see the draft and reply "yes, post it". Only then does Claude publish it, either now or at the planned time (Sydney time).
4. Claude logs it in `log.md` and `scoreboard.csv`.

### Nothing posts without your OK

Each post needs your approval of the exact clip, caption and account. To speed things up, you can approve a batch at once ("post 1–5 at these times").

## Posting times (Sydney, AEDT, UTC+11)

Launch week: as many strong clips as possible, spaced 1 to 2 hours apart per account.
After that, the defaults are 11:00 and 18:00 Sydney time, adjusted once scoreboard.csv shows what works.
Don't post more than one clip within the same 60 minutes on one account, or the clips compete with each other.

## Fallback: direct API

`tools/post_instagram.py` publishes a Reel through the Instagram Graph API with a long-lived token (`IG_USER_ID`, `IG_ACCESS_TOKEN` in `.env`).
YouTube direct upload needs a Google Cloud OAuth client with the `youtube.upload` scope.
Both work, but vidIQ is simpler and already connected.

## Getting YouTube sources (long YouTube videos and streams)

YouTube blocks downloads from Claude's cloud server. Options, best first:

1. **Connect your computer** (Claude desktop app → Settings → Claude Code → Remote Control). Claude then runs
   `tools/autoclip.py` on your machine, using your home internet connection, for any YouTube video or stream.
2. **Import a specific finished video through vidIQ** (`vidiq_video_upload` with the YouTube link). It works for normal uploads. Multi-hour streams may be too large.
3. Run `tools/autoclip.py` yourself (setup steps are in the README).

Never paste passwords, cookies or tokens into the chat.
