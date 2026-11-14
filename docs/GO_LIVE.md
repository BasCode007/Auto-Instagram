# Go-live checklist

The whole path, in order. Budget about an hour; step 2 is most of it.

## 1. Accounts and keys

- [ ] **Instagram** — account set to **Creator** or **Business** (Settings →
      Account type and tools).
- [ ] **Instagram token** — the one hard step. `SETUP.md` Part A.
- [ ] **Script writer** — an OpenAI API key (or any OpenAI-compatible API).
- [ ] **ElevenLabs** — API key and a voice ID.
- [ ] **Pexels** — free API key.
- [ ] **Cloudinary** — free account; an **unsigned** upload preset.
- [ ] **Telegram bot** — `/newbot` with @BotFather; your chat ID. This is how
      you hear about failures, so do it even for autopilot.

## 2. Start it

```bash
cp .env.example .env      # paste the values in
docker compose up -d --build
```

Nothing to configure in the n8n UI: the workflows import and activate
themselves.

### Optional: AI signature shots

On the machine with the NVIDIA GPU: `bash comfyui/smoke_test.sh` once, then
`docker compose --profile gpu up -d` and set `COMFYUI_URL=http://comfyui:8188`
in `.env`. Each reel then opens with up to two generated shots.

## 3. Check it

```bash
docker compose exec renderer bash /app/scripts/verify_setup.sh
```

Every line should be green. It calls each service with your real keys and
confirms the token can publish.

## 4. First post

Open <http://localhost:5678>, create the owner login when asked, open
**Auto-Instagram — create and publish** and click **Execute workflow**.

- `AUTO_PUBLISH=true` — it posts, then messages you the link.
- `AUTO_PUBLISH=false` — it messages you the video with Approve / Skip links.
  Those links need a public URL: `SETUP.md` Part C.

## 5. Leave it running

It posts at 07:30 and 18:30 (your `GENERIC_TIMEZONE`). To change that, edit the
cron line in `n8n/build_workflow.py`, run it, and re-import with
`FORCE_REIMPORT=1 docker compose up -d`.

Keep the machine on. A small always-on box or a ~$6/month VPS is enough.

## When something breaks

| Symptom | Cause |
|---|---|
| Telegram: "FAILED at Render video" | A key or quota problem — run the verifier. |
| Telegram: "Instagram did not accept the video" | Usually the video URL was not public. The verifier tests this. |
| Posts stop after ~2 months | Token expired. Generate a new one (Part A) and restart. |
| Approve link does nothing | `WEBHOOK_URL` is not reachable from your phone (Part C). |
