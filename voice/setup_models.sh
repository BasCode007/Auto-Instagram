#!/usr/bin/env bash
# One-time model install for the VoiceStudio container (headless). Installs the
# OmniVoice TTS model and a fast Whisper for word timings, then waits for both.
# Usage: VOICE_BASE_URL=http://localhost:3900 VOICE_API_KEY=... bash voice/setup_models.sh
set -euo pipefail
B="${VOICE_BASE_URL:-http://localhost:3900}"; K="${VOICE_API_KEY:-}"
H=(-H "Content-Type: application/json"); [ -n "$K" ] && H+=(-H "Authorization: Bearer $K")
TTS="${VOICE_TTS_REPO:-k2-fsa/OmniVoice}"
ASR="${VOICE_ASR_REPO:-deepdml/faster-whisper-large-v3-turbo-ct2}"
for i in $(seq 1 60); do curl -fsS "$B/health" >/dev/null 2>&1 && break; sleep 5; done
curl -fsS "$B/health" >/dev/null || { echo "VoiceStudio not reachable at $B" >&2; exit 1; }
installed() { curl -fsS "${H[@]}" "$B/models" | python3 -c '
import json,sys; want=sys.argv[1]; d=json.load(sys.stdin); items=d if isinstance(d,list) else d.get("models") or d.get("items") or []
print("yes" if any(m.get("repo_id")==want and m.get("installed") for m in items) else "no")' "$1"; }
for repo in "$TTS" "$ASR"; do
  if [ "$(installed "$repo")" = "yes" ]; then echo "already installed: $repo"; continue; fi
  echo "installing $repo"
  curl -sS "${H[@]}" -X POST "$B/models/install" -d "{\"repo_id\":\"$repo\"}" -o /tmp/install.out -w " http %{http_code}\n" || true
  head -c 300 /tmp/install.out; echo
done
for i in $(seq 1 360); do   # up to 30 min of downloading
  s="$(curl -fsS "${H[@]}" "$B/models/install/status" 2>/dev/null || echo '{}')"
  busy="$(printf '%s' "$s" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d.get("jobs") or d.get("active") or []))' 2>/dev/null || echo 0)"
  [ "$busy" = "0" ] && [ "$(installed "$TTS")" = "yes" ] && [ "$(installed "$ASR")" = "yes" ] && { echo "models ready"; exit 0; }
  [ $((i % 6)) -eq 0 ] && echo "  downloading... ($s)" | head -c 300 && echo
  sleep 5
done
echo "timed out waiting for models; check $B in a browser" >&2; exit 1
