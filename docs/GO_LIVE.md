# Go-live checklist

The ordered path from an empty account to a live, self-running poster. Tick
straight down. `SETUP.md` has the detail for each step; this page is the
sequence and the checkpoints.

Everything here is **owner action** — it needs your accounts and credentials.
The code side is finished and on the branch. Budget ~1–2 hours end to end;
step 2 is the long pole.

---

## Stage 1 — Accounts (~1 hour)

- [ ] **1. Instagram account** — switch to **Business** or **Creator** and link
      a Facebook Page. *Nothing downstream works until this is true.*
- [ ] **2. Meta app + token** — create the app, add the Instagram Graph API
      product, **leave it in Development mode** (publishing to your own account
      needs no App Review), and generate a token with `instagram_basic`,
      `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`,
      `business_management`. Then exchange it for a **long-lived** token.
      → `SETUP.md` Part A
- [ ] **3. Content keys** — OpenAI, ElevenLabs (**Starter** tier, for the
      commercial licence), Pexels, Cloudinary (the upload preset must be
      **unsigned**). → `SETUP.md` Part B
- [ ] **4. Telegram bot** — `/newbot` with @BotFather, message the bot once,
      then read your chat id from `getUpdates`. → `SETUP.md` Part C

## Stage 2 — Host (~10 min)

- [ ] **5. Configure** — `cp .env.example .env` and fill it in.
- [ ] **6. Start** — `docker compose up -d --build`, then open
      <http://localhost:5678>.

## ✅ Checkpoint A — verify credentials

```bash
docker compose exec n8n bash /repo/scripts/verify_setup.sh
```

Every line must be green before you go further. The verifier proves your keys
work, confirms the Graph token really carries `instagram_content_publish`,
does a real test upload to check the video URL is publicly fetchable, and
**prints your Instagram Business Account ID** if you haven't set one.

- [ ] **7. Verifier passes** (warnings are acceptable; `✗` failures are not).

## Stage 3 — Wire the workflow (~10 min)

- [ ] **8. Import** `n8n/auto-instagram-workflow.json`.
- [ ] **9. Set config node** — paste your `igUserId` (from the verifier) and
      your `handle`; leave `graphVersion` at `v21.0`.
- [ ] **10. Telegram credential** — create it with your bot token and select it
      on both Telegram nodes. If the *Approve post?* node warns after import,
      re-select operation **"Send and Wait for Response"**.

## ✅ Checkpoint B — one real post

- [ ] **11. Execute Workflow** once, by hand. Expect: a Telegram message with
      the caption and a video link → tap **Approve** → the Reel appears on the
      account within a minute or two.

If the video renders and the Telegram message arrives but tapping Approve does
nothing, your `WEBHOOK_URL` isn't publicly reachable — see Gotchas.

## Stage 4 — Live

- [ ] **12. Cadence** — edit the Schedule node (ships at every 12h).
- [ ] **13. Activate** the workflow with the toggle.
- [ ] **14. Watch the first week** of approvals and tune
      `config/niche.md` + `prompts/` until the voice sounds like you.

---

## Gotchas that actually bite

| Symptom | Cause | Fix |
| --- | --- | --- |
| Telegram message arrives, Approve does nothing | `WEBHOOK_URL` is `localhost`, so Telegram can't call back | Put n8n behind a public domain or a tunnel (Cloudflare Tunnel / ngrok) and set `WEBHOOK_URL` to it |
| Publishing breaks ~60 days in | Long-lived tokens expire | Switch to a **System User** token (Business Settings → Users → System Users) — it doesn't expire |
| `Invalid OAuth access token` | Token wrong, expired, or missing scopes | Re-run the verifier; it names the missing scope |
| Upload works, Instagram won't fetch it | Video URL isn't public | Verifier's "publicly fetchable" check catches this |
| Credentials vanish after restart | `N8N_ENCRYPTION_KEY` unset or changed | Set it **once** before saving credentials, never change it |
| Quote cards fail on ImageMagick | image is v7 (`magick`, no `convert`) | `ln -s $(command -v magick) /usr/local/bin/convert` |

## When you're ready to drop the approval step

The pipeline ships with review-before-posting on purpose — keep it while you
calibrate. To go fully hands-off later, connect **Parse render output** straight
to **Create media container**, bypassing *Approve post?* and *Approved?*. Keep
the "Notify posted" node so you still get a receipt for every post.
