#!/usr/bin/env bash
#
# End-to-end test: real n8n + the real renderer, with every external API mocked.
# Runs the whole workflow (script -> render -> container -> poll -> publish) and
# asserts on what was actually sent. Needs docker, ffmpeg (with flite) and jq.
#
#   bash tests/e2e/run.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
W="$(mktemp -d)"; M=http://127.0.0.1:9911; N8N_IMAGE="${N8N_IMAGE:-n8nio/n8n:2.47.3}"
cleanup() { docker rm -f autoig-e2e-n8n >/dev/null 2>&1 || true; for p in "${MOCK:-}" "${REND:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done; true; }
trap cleanup EXIT
mkdir -p "$W/fx" "$W/pub" "$W/data"; chmod 777 "$W/data" "$W/pub"

echo "== fixtures"
ffmpeg -y -loglevel error -f lavfi -i "flite=text='Wealth is a system you repeat. Start small this week and let time do the work.':voice=slt" -c:a libmp3lame "$W/fx/voice.mp3"
VS="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/fx/voice.mp3")"
for i in 1 2 3; do ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=720x1280:r=25:d=4" -c:v libx264 -pix_fmt yuv420p "$W/fx/clip$i.mp4"; done

start_mock() { [ -n "${MOCK:-}" ] && kill "$MOCK" 2>/dev/null; python3 tests/e2e/mock_apis.py --port 9911 --fixtures "$W/fx" --public "$W/pub" --graph-mode "$1" --voice-seconds "$VS" & MOCK=$!; sleep 1; }
start_mock ok
PORT=8080 UPLOADER=copy PUBLIC_DIR="$W/pub" PUBLIC_BASE_URL="$M/pub" ELEVENLABS_BASE_URL="$M" PEXELS_BASE_URL="$M" \
  ELEVENLABS_API_KEY=k ELEVENLABS_VOICE_ID=v PEXELS_API_KEY=k python3 renderer/server.py >"$W/renderer.log" 2>&1 & REND=$!

cat > "$W/env" <<ENV
N8N_LISTEN_ADDRESS=0.0.0.0
N8N_DIAGNOSTICS_ENABLED=false
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
LLM_BASE_URL=$M/v1
LLM_API_KEY=k
IG_GRAPH_BASE_URL=$M
IG_ACCESS_TOKEN=t
RENDERER_URL=http://127.0.0.1:8080
TELEGRAM_BASE_URL=$M
TELEGRAM_BOT_TOKEN=1:b
TELEGRAM_CHAT_ID=1
AUTO_PUBLISH=true
NO_PROXY=127.0.0.1,localhost
ENV
echo "== n8n: unattended import + publish, then start"
docker run --rm --network host --env-file "$W/env" -v "$W/data":/home/node/.n8n -v "$ROOT/n8n":/workflows:ro --entrypoint /bin/sh "$N8N_IMAGE" /workflows/init.sh >/dev/null 2>&1
docker run -d --name autoig-e2e-n8n --network host --env-file "$W/env" -v "$W/data":/home/node/.n8n "$N8N_IMAGE" >/dev/null
for _ in $(seq 1 90); do [ "$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' http://127.0.0.1:5678/healthz || true)" = "200" ] && break; sleep 2; done; sleep 6
exec_wf() { docker exec -e N8N_RUNNERS_BROKER_PORT=5690 autoig-e2e-n8n n8n execute --id=AutoIgMain000001 2>&1 || true; }
fail() { echo "FAIL: $1"; exit 1; }

echo "== happy path"
out="$(exec_wf)"; echo "$out" | grep -q "Execution was successful" || { echo "$out" | tail -20; fail "workflow did not succeed"; }
log="$(curl -s --noproxy '*' $M/_log)"
[ "$(echo "$log" | jq '[.[]|select(.path|test("media_publish"))]|length')" = "1" ] || fail "expected exactly one publish"
cap="$(echo "$log" | jq -r '[.[]|select(.body.caption?)][0].body.caption')"
[ "$(printf '%s' "$cap" | grep -o '#[A-Za-z0-9_]*' | wc -l)" -le 5 ] || fail "more than 5 hashtags"
[ "$(echo "$log" | jq '[.[]|select(.auth=="" and (.path|test("^/bot")|not))]|length')" = "0" ] || fail "an API call went out without auth"
echo "   ok: published once, <=5 hashtags, auth on every call"

echo "== Instagram rejects the video"
start_mock error
out="$(exec_wf)"; echo "$out" | grep -q "Instagram did not accept the video" || fail "rejection was not reported"
[ "$(curl -s --noproxy '*' $M/_log | jq '[.[]|select(.path|test("media_publish"))]|length')" = "0" ] || fail "published a rejected video"
echo "   ok: stopped cleanly, nothing published"
echo "ALL E2E CHECKS PASSED"
