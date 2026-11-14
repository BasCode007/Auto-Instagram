# Setup detail

`GO_LIVE.md` is the checklist; this is the reference behind it.

## Part A — Instagram token

You need a token that lets an app publish to **your own** account. An app in
Development mode can do this for accounts with a role on it — no App Review.

**Recommended: Instagram Login** (no Facebook Page needed)

1. Make the Instagram account **Creator** or **Business**.
2. <https://developers.facebook.com> → *My Apps* → *Create app* → choose the
   Instagram use case ("Manage messaging & content on Instagram").
3. In the app: *Instagram* → *API setup with Instagram login*.
4. Under *Generate access tokens*, add your Instagram account, log in and
   approve. Accept the tester invite if asked (Instagram → Settings → Apps and
   websites → Tester invites).
5. Copy the token into `.env` as `IG_ACCESS_TOKEN`. Leave
   `IG_GRAPH_HOST=graph.instagram.com` and `IG_USER_ID=me`.

It needs the `instagram_business_basic` and `instagram_business_content_publish`
permissions. The token lasts **60 days**. Refresh it before then:

```bash
curl "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=$IG_ACCESS_TOKEN"
```

**Alternative: Facebook Login** — use this if you want a token that never
expires. Link the Instagram account to a Facebook Page, create a System User in
Meta Business Settings with `instagram_basic`, `instagram_content_publish` and
`pages_read_engagement`, and generate its token. Set
`IG_GRAPH_HOST=graph.facebook.com`; the verifier prints the `IG_USER_ID` to use.

Meta's dashboard wording changes often. If a label above has moved, the goal is
unchanged: a token for your account with the content-publish permission.

## Part B — The other keys

| Setting | Where |
|---|---|
| `LLM_API_KEY` | platform.openai.com → API keys. Any OpenAI-compatible API works via `LLM_BASE_URL` / `LLM_MODEL`. |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | elevenlabs.io → profile → API key; Voices → copy a voice ID. Use a paid tier for commercial rights. |
| `PEXELS_API_KEY` | pexels.com/api |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_UPLOAD_PRESET` | Cloudinary → Settings → Upload → add an **unsigned** preset. |
| `TELEGRAM_BOT_TOKEN` | @BotFather → `/newbot` |
| `TELEGRAM_CHAT_ID` | message your bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `message.chat.id` |

## Part C — Review mode needs a public URL

Only when `AUTO_PUBLISH=false`. The Approve / Skip links in Telegram open n8n,
so n8n must be reachable from your phone. Autopilot needs none of this.

1. Cloudflare → Zero Trust → Networks → Tunnels → create a tunnel; copy the
   connector token into `CLOUDFLARE_TUNNEL_TOKEN`.
2. Add a public hostname with service URL **`http://n8n:5678`** — the compose
   service name, not `localhost`.
3. Set `WEBHOOK_URL=https://that-hostname` and run
   `docker compose --profile tunnel up -d`.
4. That hostname exposes the n8n editor. Put Cloudflare Access in front of it,
   limited to your email. If you want approval links to open without a login,
   add a second, narrower Access application for the path `/webhook-waiting`
   with a Bypass policy. Never bypass `/` or `/rest`.

For a one-off test without a domain: `docker compose --profile quicktunnel up -d`
and take the URL from `docker compose logs cloudflared-quick`.

An unanswered approval is treated as Skip after 12 hours.

## Part D — Music

Put royalty-free tracks you are licensed to use in `assets/music/`. One is
picked at random per video. Without any, videos are voice-only or silent.

## Part E — Changing what it posts

- The look and pacing: `CUT` (seconds per shot) and `MUSIC_LEVEL` in `.env`;
  caption size, colour and position at the top of `scripts/make_captions.py`.
- AI shots: `COMFYUI_URL`, `COMFY_SHOTS`, `COMFY_SECONDS` (see `comfyui/README.md`).

- Voice, pillars, rules: `config/niche.md`.
- Prompts, schedule, rotation: `n8n/build_workflow.py`, then
  `python3 n8n/build_workflow.py` and `FORCE_REIMPORT=1 docker compose up -d`.
  Re-importing clears the "already posted" memory.

## Running one post by hand, without n8n

```bash
docker compose exec renderer bash -c 'QUOTE="Calm is a strategy." PILLAR=wealth_mindset bash /app/scripts/render_quote_card.sh'
# -> {"video_url": "...", "duration": 7}
IG_ACCESS_TOKEN=... bash scripts/publish_reel.sh "<video_url>" caption.txt
```
