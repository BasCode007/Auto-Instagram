# Auto-Instagram

Writes, voices, renders and publishes short vertical videos for a finance /
wealth / success account — on a schedule, through the official Instagram API.

```bash
cp .env.example .env          # paste in your keys
docker compose up -d --build  # that is the whole install
docker compose exec renderer bash /app/scripts/verify_setup.sh
```

The workflows import and activate themselves and everything is configured from
`.env`. With `AUTO_PUBLISH=true` it runs unattended and needs no public URL;
with `false`, each post is sent to Telegram for Approve / Skip first.

- **[docs/GO_LIVE.md](docs/GO_LIVE.md)** — the checklist.
- **[docs/SETUP.md](docs/SETUP.md)** — where each key comes from.
- **[docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)** — how it works.
- **[docs/AUDIT.md](docs/AUDIT.md)** — what broke when it was first run, and the fixes.

## Layout

```
docker-compose.yml   n8n + renderer (+ optional Cloudflare Tunnel)
n8n/                 build_workflow.py -> the two workflow JSON files; init.sh
renderer/            HTTP wrapper around the render scripts
scripts/             render_*.sh, make_captions.py, upload_public.sh,
                     publish_reel.sh, verify_setup.sh
config/              niche.md (voice + rules), hashtags.json
auto_instagram/      caption rules as a tested Python library
assets/music/        optional licensed background tracks
tests/               unit tests; tests/e2e runs real n8n against mock APIs
```

## Tests

```bash
python -m unittest discover -s tests   # library + verifier
bash tests/e2e/run.sh                  # real n8n + real renderer, mock APIs
```

Content is education and motivation, **not financial advice**; see
[config/niche.md](config/niche.md).
