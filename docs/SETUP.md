# Setup guide

End-to-end setup for the finance/wealth auto-poster. Budget path: **self-hosted
n8n** with local rendering. Plan ~1–2 hours the first time.

You will collect a set of secrets and put them in n8n's **environment** (not in
the workflow). The workflow references them as `{{ $env.NAME }}`, and the render
scripts read them directly.

Secrets checklist:

| Env var | From |
| --- | --- |
| `OPENAI_API_KEY` | platform.openai.com |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | elevenlabs.io |
| `PEXELS_API_KEY` | pexels.com/api |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_UPLOAD_PRESET` | cloudinary.com |
| `IG_ACCESS_TOKEN` | Meta app (Part A) |
| `TELEGRAM_CHAT_ID` | Telegram (Part D) |
| `SCRIPTS_DIR` | path to this repo's `scripts/` on the n8n host |

Non-secret values (`igUserId`, `graphVersion`, `handle`) go in the **Set config**
node inside the workflow.

---

## Part A — Instagram + Meta (official Graph API)

1. **Convert the account** to **Business** or **Creator** (Instagram app →
   Settings → Account type). Business accounts must be **linked to a Facebook
   Page** (create a throwaway Page if you don't have one).
2. Go to **developers.facebook.com** → *My Apps* → *Create App* → type
   **Business**. Add the **Instagram Graph API** product.
3. **Keep the app in _Development_ mode** and add yourself as an app admin. In
   development mode you can publish to accounts that have a role on the app —
   i.e. your own — **without going through App Review**. (You only need Review +
   Business Verification if you later publish for other people.)
4. In **Graph API Explorer**, select your app and generate a **User token** with
   scopes: `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement`, `business_management`.
5. Find your **Instagram Business Account ID**:
   ```bash
   # 1) find your page id
   curl -s "https://graph.facebook.com/v21.0/me/accounts?access_token=SHORT_TOKEN"
   # 2) get the linked IG account id from that page
   curl -s "https://graph.facebook.com/v21.0/PAGE_ID?fields=instagram_business_account&access_token=SHORT_TOKEN"
   ```
   The `instagram_business_account.id` is your **`igUserId`** (put it in *Set config*).
6. **Get a long-lived token** (~60 days):
   ```bash
   curl -s "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"
   ```
   Use that value as **`IG_ACCESS_TOKEN`**. For a token that doesn't expire,
   create a **System User** in *Business Settings → Users → System Users*, assign
   your Page and the two `instagram_*` permissions, and generate its token
   instead. Set a calendar reminder to refresh if you use the 60-day token.

## Part B — Content API keys

- **OpenAI** — create a key → `OPENAI_API_KEY`. (Swap the model/URL in the
  *Generate script* node if you prefer another provider.)
- **ElevenLabs** — subscribe to **Starter** (~USD 5/mo, includes a commercial
  licence). Copy your API key → `ELEVENLABS_API_KEY`. Pick a voice in *Voices*
  and copy its **Voice ID** → `ELEVENLABS_VOICE_ID`.
- **Pexels** — request a free API key at pexels.com/api → `PEXELS_API_KEY`.
- **Cloudinary** — free account. In *Settings → Upload*, add an **unsigned**
  upload preset. Note your **cloud name** and the **preset name** →
  `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_UPLOAD_PRESET`.

## Part C — Telegram approval bot

1. In Telegram, message **@BotFather** → `/newbot` → copy the **bot token**.
2. Send your new bot any message, then read your chat id:
   ```bash
   curl -s "https://api.telegram.org/botBOT_TOKEN/getUpdates"
   ```
   Use `result[0].message.chat.id` → `TELEGRAM_CHAT_ID`.
3. In n8n you'll create a **Telegram credential** with the bot token (the two
   Telegram nodes reference it).

## Part D — Host the renderer + n8n

The render scripts need `ffmpeg`, `imagemagick`, `bash`, `curl`, `jq` and fonts
on the same machine as n8n. The stock n8n image doesn't include them, so extend
it:

```dockerfile
# Dockerfile
FROM n8nio/n8n:latest
USER root
RUN apk add --no-cache ffmpeg imagemagick ttf-dejavu fontconfig bash curl jq
USER node
```

```yaml
# docker-compose.yml
services:
  n8n:
    build: .
    ports: ["5678:5678"]
    environment:
      - GENERIC_TIMEZONE=Australia/Sydney
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - ELEVENLABS_VOICE_ID=${ELEVENLABS_VOICE_ID}
      - PEXELS_API_KEY=${PEXELS_API_KEY}
      - CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME}
      - CLOUDINARY_UPLOAD_PRESET=${CLOUDINARY_UPLOAD_PRESET}
      - IG_ACCESS_TOKEN=${IG_ACCESS_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - SCRIPTS_DIR=/repo/scripts
    volumes:
      - n8n_data:/home/node/.n8n
      - ./Auto-Instagram:/repo        # this repo, so /repo/scripts exists
volumes:
  n8n_data:
```

Put the secrets in a `.env` next to the compose file, clone this repo into
`./Auto-Instagram`, then `docker compose up -d --build`. Open
`http://localhost:5678`.

> Quick render self-test (inside the container):
> ```bash
> QUOTE="Wealth is built in the boring middle." HANDLE="@yourhandle" \
>   UPLOADER=copy PUBLIC_DIR=/tmp/pub PUBLIC_BASE_URL=http://localhost \
>   bash /repo/scripts/render_quote_card.sh
> ```
> It should print a JSON line ending in `.mp4`.

## Part E — Import and wire the workflow

1. In n8n: *Workflows → Import from File* → `n8n/auto-instagram-workflow.json`.
2. Open **Set config** and fill `igUserId`, `graphVersion` (keep `v21.0`),
   `handle`.
3. Open the two **Telegram** nodes and select your Telegram credential. If the
   **Approve post?** node shows a parameter warning after import, re-select
   operation **"Send and Wait for Response"** (the human-in-the-loop op).
4. Confirm the env vars from the checklist are set (Part D).
5. Click **Execute Workflow** once to test. You should get a Telegram message
   with the caption and a video link; tap **Approve** and watch it publish.

## Part F — Go live

- The **Schedule** node runs every 12h (edit to your posting cadence).
- Content type alternates by time of day and the pillar rotates daily — tune the
  logic in **Pick content type & pillar**.
- Activate the workflow with the toggle. Keep an eye on the first week of
  Telegram approvals to calibrate tone before trusting it.

## Optional — cloud rendering (e.g. on n8n Cloud)

If you can't self-host ffmpeg (n8n Cloud has no Execute Command), replace the two
render nodes with an **HTTP Request** node that calls a render API
(**Creatomate** or **JSON2Video**) using the same fields (`script_b64` etc.,
base64-decoded on their side or sent as plain text), returning a public MP4 URL.
Feed that URL into **Parse render output** as `video_url`. Budget note: these
services start around AUD 30+/mo, above the AUD 20–30 target.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `need ffmpeg` / `need ImageMagick` | Rebuild the image with the `apk add` line above. |
| ImageMagick has only `magick`, not `convert` | Alias it: `ln -s $(command -v magick) /usr/local/bin/convert`. |
| Graph API "media not ready" | The workflow already polls; increase the **Wait** if your videos are long. |
| Graph API permission error | Token missing `instagram_content_publish`, or the account isn't Business/Creator + Page-linked. |
| Cloudinary upload fails | The preset must be **unsigned**; check `CLOUDINARY_CLOUD_NAME`/preset. |
| Token stopped working after ~60 days | Refresh the long-lived token, or switch to a System User token. |
