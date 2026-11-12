#!/usr/bin/env bash
#
# verify_setup.sh — preflight check for the Auto-Instagram pipeline.
#
# Checks the render tools, the required settings, and then calls every
# external service with your real credentials: the script-writing model,
# ElevenLabs (including that your voice id exists), Pexels, a real test upload
# to your video host, the Instagram API (token, publish permission, quota,
# expiry) and Telegram. Read-only apart from one tiny test clip upload.
#
# Run it in the renderer container, which has the tools and your .env:
#   docker compose exec renderer bash /app/scripts/verify_setup.sh
#
# Exit code is 0 only when nothing failed.
#
# Flags:
#   --skip-network   only check tools and settings (offline)
#   --help           show usage

set -uo pipefail   # deliberately not -e: every check should run

SKIP_NETWORK=0
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"

for arg in "$@"; do
  case "$arg" in
    --skip-network) SKIP_NETWORK=1 ;;
    -h|--help) awk 'NR==1 {next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg (try --help)" >&2; exit 2 ;;
  esac
done

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_OK=$'\033[32m'; C_BAD=$'\033[31m'; C_WARN=$'\033[33m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else C_OK=""; C_BAD=""; C_WARN=""; C_DIM=""; C_OFF=""; fi
PASS=0; FAIL=0; WARN=0
ok()   { PASS=$((PASS+1)); printf '  %s✓%s %s\n' "$C_OK" "$C_OFF" "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  %s✗%s %s\n' "$C_BAD" "$C_OFF" "$1"; [ $# -gt 1 ] && printf '      %s%s%s\n' "$C_DIM" "$2" "$C_OFF"; return 0; }
warn() { WARN=$((WARN+1)); printf '  %s!%s %s\n' "$C_WARN" "$C_OFF" "$1"; [ $# -gt 1 ] && printf '      %s%s%s\n' "$C_DIM" "$2" "$C_OFF"; return 0; }
section() { printf '\n%s\n' "$1"; }
snip() {  # short human hint from an API error body; never more than 160 chars
  local raw="${1:-}" msg=""
  msg="$(printf '%s' "$raw" | jq -r '.error.message? // .error.description? // .detail.message? // .description? // .message? // empty' 2>/dev/null | head -n1)"
  [ -z "$msg" ] && msg="$(printf '%s' "$raw" | tr -d '\n')"
  printf '%s' "$msg" | cut -c1-160
}
http_get() { curl -sS --max-time 25 -w '\n%{http_code}' "$@" 2>/dev/null; }
body_of()   { printf '%s' "$1" | sed '$d'; }
status_of() { printf '%s' "$1" | tail -n1; }

# AUTO_IG_SKIP_DOTENV=1 ignores .env (used by the tests).
if [ "${AUTO_IG_SKIP_DOTENV:-0}" != "1" ] && [ -f "$REPO_ROOT/.env" ] && [ -z "${IG_ACCESS_TOKEN:-}" ]; then
  set -a; . "$REPO_ROOT/.env"; set +a   # shellcheck disable=SC1091
  echo "${C_DIM}(loaded $REPO_ROOT/.env)${C_OFF}"
fi

echo "Auto-Instagram preflight"
echo "========================"

section "Render tools"
for bin in bash curl jq ffmpeg ffprobe python3; do
  if command -v "$bin" >/dev/null 2>&1; then ok "$bin"; else bad "$bin missing" "run this inside the renderer container"; fi
done
if command -v convert >/dev/null 2>&1; then ok "ImageMagick (convert)"; else bad "ImageMagick missing" "needed for quote cards"; fi
# (captured first: with pipefail, `ffmpeg | grep -q` fails when grep exits early)
ff_filters="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
if printf '%s' "$ff_filters" | grep -q ' subtitles '; then ok "ffmpeg has libass (burned-in captions)"
else bad "ffmpeg lacks the subtitles filter" "captions cannot be burned in"; fi
if [ -f /usr/share/fonts/opentype/inter/Inter-Bold.otf ]; then ok "Inter font"
else warn "Inter font not found" "falls back to DejaVu Sans; install fonts-inter for the intended look"; fi

FAIL_BEFORE_ENV="$FAIL"
section "Settings"
UPLOADER="${UPLOADER:-cloudinary}"
AUTO_PUBLISH="$(printf '%s' "${AUTO_PUBLISH:-false}" | tr '[:upper:]' '[:lower:]')"
LLM_KEY="${LLM_API_KEY:-${OPENAI_API_KEY:-}}"
require() { local name="$1" hint="${2:-}"; if [ -z "${!1:-}" ]; then bad "$name is not set" "$hint"; return 1; fi; ok "$name is set"; }

require IG_ACCESS_TOKEN     "docs/SETUP.md Part A"
if [ -n "$LLM_KEY" ]; then ok "LLM_API_KEY is set"; else bad "LLM_API_KEY is not set" "key for the script-writing model"; fi
require ELEVENLABS_API_KEY  "elevenlabs.io -> profile -> API key"
require ELEVENLABS_VOICE_ID "elevenlabs.io -> Voices -> copy the voice ID"
require PEXELS_API_KEY      "pexels.com/api"
case "$UPLOADER" in
  cloudinary) require CLOUDINARY_CLOUD_NAME "Cloudinary dashboard"; require CLOUDINARY_UPLOAD_PRESET "must be an UNSIGNED preset" ;;
  copy)       require PUBLIC_DIR "directory you serve over https"; require PUBLIC_BASE_URL "public https base URL for PUBLIC_DIR" ;;
  *) bad "UPLOADER='$UPLOADER' is not recognised" "use 'cloudinary' or 'copy'" ;;
esac
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then ok "Telegram alerts configured"
elif [ "$AUTO_PUBLISH" = "true" ]; then warn "Telegram not configured" "autopilot will run, but failures will be silent — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
else bad "Telegram not configured" "review mode sends each post to Telegram for approval"; fi
case "${N8N_ENCRYPTION_KEY:-}" in
  ""|change-me*) warn "N8N_ENCRYPTION_KEY unset or still the placeholder" "set it once: openssl rand -hex 24" ;;
  *) ok "N8N_ENCRYPTION_KEY is set" ;;
esac
if [ "$AUTO_PUBLISH" = "true" ]; then
  ok "mode: autopilot (no approval step, no public URL needed)"
else
  case "${WEBHOOK_URL:-}" in
    ""|*localhost*|*127.0.0.1*) warn "mode: review, but WEBHOOK_URL is local" "Approve/Skip links will not open from your phone — run the Cloudflare Tunnel, or set AUTO_PUBLISH=true" ;;
    *) ok "mode: review, approval links via $WEBHOOK_URL" ;;
  esac
fi

if [ "$((FAIL - FAIL_BEFORE_ENV))" -gt 0 ]; then
  section "Summary"
  printf '  %s%d passed, %d failed, %d warnings%s\n' "$C_BAD" "$PASS" "$FAIL" "$WARN" "$C_OFF"
  echo "  Set the missing values above, then re-run — the service checks"
  echo "  can't run without credentials."
  exit 1
fi
if [ "$SKIP_NETWORK" = "1" ]; then
  section "Summary"; printf '  %d passed, %d failed, %d warnings (network checks skipped)\n' "$PASS" "$FAIL" "$WARN"; exit 0
fi

section "Script-writing model"
LLM_BASE="${LLM_BASE_URL:-https://api.openai.com/v1}"; LLM_MODEL="${LLM_MODEL:-gpt-4o-mini}"
resp="$(http_get -H "Authorization: Bearer $LLM_KEY" "$LLM_BASE/models")"
case "$(status_of "$resp")" in
  200) ok "API key accepted"
       if printf '%s' "$(body_of "$resp")" | jq -e --arg m "$LLM_MODEL" '.data[]? | select(.id == $m)' >/dev/null 2>&1; then ok "model $LLM_MODEL is available"
       else warn "model $LLM_MODEL not in this account's model list" "set LLM_MODEL to one that is"; fi ;;
  401) bad "API key rejected (401)" "check LLM_API_KEY" ;;
  *)   bad "unexpected status $(status_of "$resp")" "$(snip "$(body_of "$resp")")" ;;
esac

section "ElevenLabs"
EL_BASE="${ELEVENLABS_BASE_URL:-https://api.elevenlabs.io}"
resp="$(http_get -H "xi-api-key: $ELEVENLABS_API_KEY" "$EL_BASE/v1/voices")"
if [ "$(status_of "$resp")" = "200" ]; then
  ok "API key accepted"
  vname="$(printf '%s' "$(body_of "$resp")" | jq -r --arg v "$ELEVENLABS_VOICE_ID" '.voices[]? | select(.voice_id == $v) | .name' 2>/dev/null | head -n1)"
  if [ -n "$vname" ]; then ok "voice id resolves ($vname)"; else bad "ELEVENLABS_VOICE_ID not found on this account" "copy the ID from elevenlabs.io -> Voices"; fi
else bad "voices lookup failed ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"; fi
resp="$(http_get -H "xi-api-key: $ELEVENLABS_API_KEY" "$EL_BASE/v1/user/subscription")"
if [ "$(status_of "$resp")" = "200" ]; then
  used="$(printf '%s' "$(body_of "$resp")" | jq -r '.character_count // 0')"; lim="$(printf '%s' "$(body_of "$resp")" | jq -r '.character_limit // 0')"
  left=$(( lim - used ))
  # one narrated Reel is roughly 700 characters
  if [ "$left" -lt 1500 ]; then bad "voice quota nearly exhausted ($left characters left)" "narrated Reels will fail until it resets or you upgrade"
  elif [ "$left" -lt 8000 ]; then warn "voice quota low: $left characters left (~$(( left / 700 )) Reels)"
  else ok "voice quota: $left characters left (~$(( left / 700 )) Reels)"; fi
fi

section "Pexels"
resp="$(http_get -H "Authorization: $PEXELS_API_KEY" "${PEXELS_BASE_URL:-https://api.pexels.com}/videos/search?query=city&orientation=portrait&per_page=1")"
if [ "$(status_of "$resp")" = "200" ]; then ok "API key accepted"; else bad "search failed ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"; fi

section "Video hosting ($UPLOADER)"
tmpdir="$(mktemp -d)"
if ffmpeg -y -loglevel error -f lavfi -i color=c=black:s=64x64:d=1 -c:v libx264 -pix_fmt yuv420p "$tmpdir/preflight.mp4" 2>/dev/null; then
  if url="$(bash "$HERE/upload_public.sh" "$tmpdir/preflight.mp4" 2>"$tmpdir/err")"; then
    ok "test upload succeeded"
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 -L "$url" 2>/dev/null)"
    if [ "$code" = "200" ]; then ok "uploaded file is publicly fetchable"
    else bad "uploaded file not publicly reachable (HTTP $code)" "Instagram downloads the video from this URL: $url"; fi
  else
    bad "test upload failed" "$(snip "$(cat "$tmpdir/err" 2>/dev/null)")"
    [ "$UPLOADER" = "cloudinary" ] && warn "most common cause" "the Cloudinary upload preset must be UNSIGNED"
  fi
else warn "could not create a test clip" "skipping upload check"; fi
rm -rf "$tmpdir"

section "Instagram API"
HOST="${IG_GRAPH_HOST:-graph.instagram.com}"; VER="${GRAPH_VERSION:-v27.0}"
G="${IG_GRAPH_BASE_URL:-https://$HOST}/$VER"; AUTH=(-H "Authorization: Bearer $IG_ACCESS_TOKEN")
ig_id="${IG_USER_ID:-me}"
if [ "$HOST" = "graph.facebook.com" ] && [ "$ig_id" = "me" ]; then
  # Facebook Login: the Instagram account hangs off a Page, so find it.
  resp="$(http_get "${AUTH[@]}" "$G/me/accounts?fields=instagram_business_account{id,username}")"
  ig_id="$(printf '%s' "$(body_of "$resp")" | jq -r 'first(.data[]?.instagram_business_account.id // empty) // empty' 2>/dev/null)"
  if [ -n "$ig_id" ]; then warn "found Instagram account id $ig_id" "set IG_USER_ID=$ig_id in .env"
  else bad "no Instagram business account linked to this token's Pages" "$(snip "$(body_of "$resp")")"; fi
fi
if [ -n "$ig_id" ]; then
  resp="$(http_get "${AUTH[@]}" "$G/$ig_id?fields=username")"
  if [ "$(status_of "$resp")" = "200" ]; then ok "token valid, account: @$(printf '%s' "$(body_of "$resp")" | jq -r '.username // "?"')"
  else bad "cannot read the account ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"; fi
  # Needs the content-publish permission, so success here proves publishing will work.
  resp="$(http_get "${AUTH[@]}" "$G/$ig_id/content_publishing_limit?fields=quota_usage,config")"
  if [ "$(status_of "$resp")" = "200" ]; then
    used="$(printf '%s' "$(body_of "$resp")" | jq -r '.data[0].quota_usage // 0')"; tot="$(printf '%s' "$(body_of "$resp")" | jq -r '.data[0].config.quota_total // 100')"
    ok "publishing permission confirmed (used $used of $tot posts in the last 24h)"
  else bad "publish permission check failed ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"; fi
fi
if [ "$HOST" = "graph.facebook.com" ]; then
  resp="$(http_get "$G/debug_token?input_token=${IG_ACCESS_TOKEN}&access_token=${IG_ACCESS_TOKEN}")"
  exp="$(printf '%s' "$(body_of "$resp")" | jq -r '.data.expires_at // empty' 2>/dev/null)"
  if [ -n "$exp" ] && [ "$exp" != "0" ]; then
    days=$(( (exp - $(date +%s)) / 86400 ))
    if [ "$days" -lt 7 ]; then warn "token expires in $days day(s)" "refresh it or switch to a System User token"; else ok "token valid for ~$days more days"; fi
  elif [ "$exp" = "0" ]; then ok "token does not expire"; fi
else
  warn "Instagram Login tokens last 60 days" "refresh before then: GET $HOST/refresh_access_token?grant_type=ig_refresh_token"
fi

section "Telegram"
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  T="${TELEGRAM_BASE_URL:-https://api.telegram.org}/bot${TELEGRAM_BOT_TOKEN}"
  resp="$(http_get "$T/getMe")"
  if [ "$(status_of "$resp")" = "200" ]; then
    ok "bot token valid (@$(printf '%s' "$(body_of "$resp")" | jq -r '.result.username // "?"'))"
    resp="$(http_get "$T/getChat?chat_id=${TELEGRAM_CHAT_ID:-}")"
    if [ "$(status_of "$resp")" = "200" ]; then ok "chat reachable"; else bad "chat id not reachable" "send your bot a message first, then re-run"; fi
  else bad "bot token rejected" "$(snip "$(body_of "$resp")")"; fi
else warn "skipped (no TELEGRAM_BOT_TOKEN)"; fi

section "Summary"
if [ "$FAIL" -eq 0 ]; then
  printf '  %s%d passed, 0 failed, %d warnings%s\n' "$C_OK" "$PASS" "$WARN" "$C_OFF"; echo "  Ready."; exit 0
else
  printf '  %s%d passed, %d failed, %d warnings%s\n' "$C_BAD" "$PASS" "$FAIL" "$WARN" "$C_OFF"; echo "  Fix the ✗ items above, then re-run."; exit 1
fi
