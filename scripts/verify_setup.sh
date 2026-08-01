#!/usr/bin/env bash
#
# verify_setup.sh — preflight check for the Auto-Instagram pipeline.
#
# Verifies, in order:
#   1. required binaries (ffmpeg, ImageMagick, curl, jq, fonts)
#   2. required environment variables
#   3. that every external service actually answers with your credentials:
#      OpenAI, ElevenLabs (including that the voice id exists), Pexels,
#      Cloudinary (a real 1-second test upload through upload_public.sh),
#      the Instagram Graph API (token validity, publish permission, quota),
#      and optionally Telegram.
#
# Run it inside the n8n container, which is where the workflow runs:
#   docker compose exec n8n bash /repo/scripts/verify_setup.sh
#
# Exit code is 0 only when nothing FAILed, so it is safe to gate on.
#
# Flags:
#   --skip-network   only check binaries and env vars (offline)
#   --help           show usage
#
# Nothing here writes to your account: the Instagram checks are read-only and
# the Cloudinary check uploads a 64x64 black test clip, never a real post.

set -uo pipefail   # deliberately not -e: we want every check to run

GRAPH_VERSION="${GRAPH_VERSION:-v21.0}"
SKIP_NETWORK=0
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"

for arg in "$@"; do
  case "$arg" in
    --skip-network) SKIP_NETWORK=1 ;;
    -h|--help)
      # Print the header comment block (everything after the shebang up to the
      # first line of real code), so help can never drift out of sync.
      awk 'NR==1 {next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "$0"
      exit 0
      ;;
    *) echo "unknown flag: $arg (try --help)" >&2; exit 2 ;;
  esac
done

# ---- output helpers --------------------------------------------------------
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_OK=$'\033[32m'; C_BAD=$'\033[31m'; C_WARN=$'\033[33m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
  C_OK=""; C_BAD=""; C_WARN=""; C_DIM=""; C_OFF=""
fi

PASS=0; FAIL=0; WARN=0
ok()   { PASS=$((PASS+1)); printf '  %s✓%s %s\n' "$C_OK" "$C_OFF" "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  %s✗%s %s\n' "$C_BAD" "$C_OFF" "$1"
         [ $# -gt 1 ] && printf '      %s%s%s\n' "$C_DIM" "$2" "$C_OFF"; return 0; }
warn() { WARN=$((WARN+1)); printf '  %s!%s %s\n' "$C_WARN" "$C_OFF" "$1"
         [ $# -gt 1 ] && printf '      %s%s%s\n' "$C_DIM" "$2" "$C_OFF"; return 0; }
section() { printf '\n%s\n' "$1"; }

# Turn an API error body into a short human hint. Prefers the provider's own
# message field (Graph, ElevenLabs, Telegram all differ) and falls back to a
# truncated raw body. Never prints more than 160 chars, so tokens echoed back
# by a provider can't sprawl across the terminal.
snip() {
  local raw="${1:-}" msg=""
  msg="$(printf '%s' "$raw" | jq -r '
      .error.message? // .error.description? // .detail.message?
      // .description? // .message? // empty' 2>/dev/null | head -n1)"
  [ -z "$msg" ] && msg="$(printf '%s' "$raw" | tr -d '\n')"
  printf '%s' "$msg" | cut -c1-160
}

# GET returning "<body>\n<http_status>"; body may be empty.
http_get() {
  curl -sS --max-time 25 -w '\n%{http_code}' "$@" 2>/dev/null
}
body_of()   { printf '%s' "$1" | sed '$d'; }
status_of() { printf '%s' "$1" | tail -n1; }

# ---- load .env if present and vars aren't already exported ------------------
# Set AUTO_IG_SKIP_DOTENV=1 to ignore .env entirely (used by the test suite so
# results don't depend on whether the developer has a populated .env locally).
if [ "${AUTO_IG_SKIP_DOTENV:-0}" != "1" ] \
   && [ -f "$REPO_ROOT/.env" ] && [ -z "${IG_ACCESS_TOKEN:-}" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$REPO_ROOT/.env"
  set +a
  echo "${C_DIM}(loaded $REPO_ROOT/.env)${C_OFF}"
fi

echo "Auto-Instagram preflight"
echo "========================"

# ---- 1. binaries -----------------------------------------------------------
section "Binaries"
for bin in bash curl jq ffmpeg ffprobe; do
  if command -v "$bin" >/dev/null 2>&1; then ok "$bin"
  else bad "$bin missing" "rebuild the container: docker compose up -d --build"; fi
done

if command -v convert >/dev/null 2>&1; then
  ok "ImageMagick (convert)"
elif command -v magick >/dev/null 2>&1; then
  warn "ImageMagick has 'magick' but not 'convert'" \
       "quote cards call convert; alias it: ln -s \$(command -v magick) /usr/local/bin/convert"
else
  bad "ImageMagick missing" "needed by render_quote_card.sh"
fi

FONT_FOUND=""
if command -v fc-match >/dev/null 2>&1; then
  FONT_FOUND="$(fc-match -f '%{file}' 'DejaVu Sans:bold' 2>/dev/null)"
fi
[ -z "$FONT_FOUND" ] && [ -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf ] \
  && FONT_FOUND=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
if [ -n "$FONT_FOUND" ]; then ok "bold font ($FONT_FOUND)"
else bad "no bold TTF found" "install ttf-dejavu, or set FONT=/path/to/font.ttf"; fi

# ---- 2. environment --------------------------------------------------------
# Missing binaries and bad credentials are independent problems, so a missing
# ffmpeg still counts as a failure but does not stop us validating your keys.
FAIL_BEFORE_ENV="$FAIL"

section "Environment"
UPLOADER="${UPLOADER:-cloudinary}"

require() { # require VAR "hint"
  local name="$1" hint="${2:-}" val="${!1:-}"
  if [ -z "$val" ]; then bad "$name is not set" "$hint"; return 1; fi
  ok "$name is set"
}

require OPENAI_API_KEY        "platform.openai.com -> API keys"
require ELEVENLABS_API_KEY    "elevenlabs.io -> profile -> API key"
require ELEVENLABS_VOICE_ID   "elevenlabs.io -> Voices -> copy the voice ID"
require PEXELS_API_KEY        "pexels.com/api"
require IG_ACCESS_TOKEN       "docs/SETUP.md Part A"
require TELEGRAM_CHAT_ID      "docs/SETUP.md Part C"

case "$UPLOADER" in
  cloudinary)
    require CLOUDINARY_CLOUD_NAME    "Cloudinary dashboard"
    require CLOUDINARY_UPLOAD_PRESET "must be an UNSIGNED preset"
    ;;
  copy)
    require PUBLIC_DIR      "directory you serve over https"
    require PUBLIC_BASE_URL "public https base URL for PUBLIC_DIR"
    ;;
  *) bad "UPLOADER='$UPLOADER' is not recognised" "use 'cloudinary' or 'copy'" ;;
esac

if [ -z "${IG_USER_ID:-}" ]; then
  warn "IG_USER_ID not set" "not fatal — this script will try to discover it below"
else
  ok "IG_USER_ID is set"
fi

case "${N8N_ENCRYPTION_KEY:-}" in
  ""|change-me*) warn "N8N_ENCRYPTION_KEY unset or still the placeholder" \
                      "set it once (openssl rand -hex 24) BEFORE saving n8n credentials" ;;
  *) ok "N8N_ENCRYPTION_KEY is set" ;;
esac

case "${WEBHOOK_URL:-}" in
  ""|*localhost*|*127.0.0.1*)
    warn "WEBHOOK_URL is unset or localhost" \
         "Telegram approve/skip buttons cannot call back — use a tunnel or public domain" ;;
  *) ok "WEBHOOK_URL is public ($WEBHOOK_URL)" ;;
esac

if [ "$((FAIL - FAIL_BEFORE_ENV))" -gt 0 ]; then
  section "Summary"
  printf '  %s%d passed, %d failed, %d warnings%s\n' "$C_BAD" "$PASS" "$FAIL" "$WARN" "$C_OFF"
  echo "  Set the missing variables above, then re-run — the service checks"
  echo "  can't run without credentials."
  exit 1
fi

if [ "$SKIP_NETWORK" = "1" ]; then
  section "Summary"
  printf '  %d passed, %d failed, %d warnings (network checks skipped)\n' "$PASS" "$FAIL" "$WARN"
  exit 0
fi

# ---- 3. live service checks ------------------------------------------------
section "OpenAI"
resp="$(http_get -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models)"
case "$(status_of "$resp")" in
  200) ok "API key accepted" ;;
  401) bad "API key rejected (401)" "check OPENAI_API_KEY" ;;
  429) warn "rate limited (429)" "key looks valid but is throttled or out of quota" ;;
  *)   bad "unexpected status $(status_of "$resp")" "$(snip "$(body_of "$resp")")" ;;
esac

section "ElevenLabs"
resp="$(http_get -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/voices)"
if [ "$(status_of "$resp")" = "200" ]; then
  ok "API key accepted"
  if printf '%s' "$(body_of "$resp")" | jq -e --arg v "$ELEVENLABS_VOICE_ID" \
       '.voices[]? | select(.voice_id == $v)' >/dev/null 2>&1; then
    vname="$(printf '%s' "$(body_of "$resp")" | jq -r --arg v "$ELEVENLABS_VOICE_ID" \
             '.voices[] | select(.voice_id == $v) | .name' 2>/dev/null)"
    ok "voice id resolves ($vname)"
  else
    bad "ELEVENLABS_VOICE_ID not found on this account" \
        "copy the ID from elevenlabs.io -> Voices"
  fi
else
  bad "voices lookup failed ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"
fi

section "Pexels"
resp="$(http_get -H "Authorization: $PEXELS_API_KEY" \
        "https://api.pexels.com/videos/search?query=city&orientation=portrait&per_page=1")"
if [ "$(status_of "$resp")" = "200" ]; then
  n="$(printf '%s' "$(body_of "$resp")" | jq -r '.videos | length' 2>/dev/null)"
  if [ "${n:-0}" -gt 0 ]; then ok "API key accepted, portrait b-roll available"
  else warn "API key works but search returned no portrait clips" "unusual; retry later"; fi
else
  bad "search failed ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"
fi

section "Public hosting ($UPLOADER)"
if command -v ffmpeg >/dev/null 2>&1; then
  tmpdir="$(mktemp -d)"
  if ffmpeg -y -loglevel error -f lavfi -i color=c=black:s=64x64:d=1 \
       -c:v libx264 -pix_fmt yuv420p "$tmpdir/preflight.mp4" 2>/dev/null; then
    if url="$(bash "$HERE/upload_public.sh" "$tmpdir/preflight.mp4" 2>"$tmpdir/err")"; then
      ok "test upload succeeded"
      code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 -L "$url" 2>/dev/null)"
      if [ "$code" = "200" ]; then
        ok "uploaded file is publicly fetchable"
      else
        bad "uploaded file not publicly reachable (HTTP $code)" \
            "Instagram fetches the video from this URL, so it must be public: $url"
      fi
    else
      bad "test upload failed" "$(snip "$(cat "$tmpdir/err" 2>/dev/null)")"
      [ "$UPLOADER" = "cloudinary" ] && \
        warn "most common cause" "the Cloudinary upload preset must be UNSIGNED"
    fi
  else
    warn "could not synthesise a test clip" "skipping upload check"
  fi
  rm -rf "$tmpdir"
else
  warn "ffmpeg missing" "skipping upload check"
fi

section "Instagram Graph API"
# Token validity + granted scopes (best effort: some token types can't self-debug).
resp="$(http_get "https://graph.facebook.com/${GRAPH_VERSION}/me/permissions?access_token=${IG_ACCESS_TOKEN}")"
if [ "$(status_of "$resp")" = "200" ]; then
  ok "access token is valid"
  granted="$(printf '%s' "$(body_of "$resp")" \
    | jq -r '[.data[]? | select(.status=="granted") | .permission] | join(",")' 2>/dev/null)"
  for scope in instagram_basic instagram_content_publish; do
    case ",$granted," in
      *",$scope,"*) ok "scope $scope granted" ;;
      *) bad "scope $scope NOT granted" "regenerate the token with this permission" ;;
    esac
  done
else
  warn "could not read /me/permissions ($(status_of "$resp"))" \
       "normal for System User tokens; the publish check below is authoritative"
fi

# Resolve the IG business account id (discover it if the owner hasn't set it).
ig_id="${IG_USER_ID:-}"
if [ -z "$ig_id" ]; then
  resp="$(http_get "https://graph.facebook.com/${GRAPH_VERSION}/me/accounts?fields=instagram_business_account{id,username}&access_token=${IG_ACCESS_TOKEN}")"
  if [ "$(status_of "$resp")" = "200" ]; then
    ig_id="$(printf '%s' "$(body_of "$resp")" \
      | jq -r 'first(.data[]?.instagram_business_account.id // empty) // empty' 2>/dev/null)"
    if [ -n "$ig_id" ]; then
      ig_name="$(printf '%s' "$(body_of "$resp")" \
        | jq -r 'first(.data[]?.instagram_business_account.username // empty) // empty' 2>/dev/null)"
      ok "discovered IG business account: $ig_id (@${ig_name:-unknown})"
      warn "put this id in the workflow's 'Set config' node as igUserId" \
           "and optionally set IG_USER_ID=$ig_id in .env so this check is exact"
    else
      bad "no Instagram business account linked to this token's Pages" \
          "the IG account must be Business/Creator AND linked to a Facebook Page"
    fi
  else
    bad "could not list Pages ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"
  fi
fi

if [ -n "$ig_id" ]; then
  resp="$(http_get "https://graph.facebook.com/${GRAPH_VERSION}/${ig_id}?fields=username,followers_count&access_token=${IG_ACCESS_TOKEN}")"
  if [ "$(status_of "$resp")" = "200" ]; then
    uname="$(printf '%s' "$(body_of "$resp")" | jq -r '.username // "?"' 2>/dev/null)"
    ok "account readable: @$uname"
  else
    bad "cannot read account $ig_id ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"
  fi

  # This endpoint requires instagram_content_publish, so it is the definitive
  # proof that publishing will work — and it reports remaining daily quota.
  resp="$(http_get "https://graph.facebook.com/${GRAPH_VERSION}/${ig_id}/content_publishing_limit?fields=quota_usage&access_token=${IG_ACCESS_TOKEN}")"
  if [ "$(status_of "$resp")" = "200" ]; then
    used="$(printf '%s' "$(body_of "$resp")" | jq -r '.data[0].quota_usage // 0' 2>/dev/null)"
    ok "publishing permission confirmed (used ${used}/50 posts in the last 24h)"
  else
    bad "publish permission check failed ($(status_of "$resp"))" "$(snip "$(body_of "$resp")")"
  fi
fi

# Token lifetime, if the token can describe itself.
resp="$(http_get "https://graph.facebook.com/${GRAPH_VERSION}/debug_token?input_token=${IG_ACCESS_TOKEN}&access_token=${IG_ACCESS_TOKEN}")"
if [ "$(status_of "$resp")" = "200" ]; then
  exp="$(printf '%s' "$(body_of "$resp")" | jq -r '.data.expires_at // empty' 2>/dev/null)"
  if [ -z "$exp" ] || [ "$exp" = "0" ]; then
    ok "token does not expire (System User or permanent token)"
  else
    now="$(date +%s)"; days=$(( (exp - now) / 86400 ))
    if   [ "$days" -lt 0 ]; then bad "token EXPIRED" "generate a new long-lived token"
    elif [ "$days" -lt 7 ]; then warn "token expires in $days day(s)" "refresh it, or switch to a System User token"
    else ok "token valid for ~$days more days"; fi
  fi
fi

section "Telegram"
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  resp="$(http_get "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe")"
  if [ "$(status_of "$resp")" = "200" ]; then
    bot="$(printf '%s' "$(body_of "$resp")" | jq -r '.result.username // "?"' 2>/dev/null)"
    ok "bot token valid (@$bot)"
    resp="$(http_get "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getChat?chat_id=${TELEGRAM_CHAT_ID}")"
    if [ "$(status_of "$resp")" = "200" ]; then ok "chat id $TELEGRAM_CHAT_ID reachable"
    else bad "chat id $TELEGRAM_CHAT_ID not reachable" "send your bot a message first, then re-run"; fi
  else
    bad "bot token rejected" "$(snip "$(body_of "$resp")")"
  fi
else
  warn "TELEGRAM_BOT_TOKEN not set — skipping" \
       "the workflow keeps it in an n8n credential; set it here too to verify approvals"
fi

# ---- summary ---------------------------------------------------------------
section "Summary"
if [ "$FAIL" -eq 0 ]; then
  printf '  %s%d passed, 0 failed, %d warnings%s\n' "$C_OK" "$PASS" "$WARN" "$C_OFF"
  echo "  Ready. Import n8n/auto-instagram-workflow.json and run it once manually."
  exit 0
else
  printf '  %s%d passed, %d failed, %d warnings%s\n' "$C_BAD" "$PASS" "$FAIL" "$WARN" "$C_OFF"
  echo "  Fix the ✗ items above, then re-run this script."
  exit 1
fi
