#!/usr/bin/env bash
#
# publish_reel.sh — publish one Reel through the Instagram Graph API and print
# JSON: {"media_id":"...","permalink":"https://www.instagram.com/reel/..."}
#
# Usage: publish_reel.sh <public-video-url> <caption-file>
#
# The same three calls the n8n workflow makes, usable on their own:
# create container -> poll until processed -> publish. Polling is bounded and
# a failed or expired container is an error, never an endless wait.
#
# Env:
#   IG_ACCESS_TOKEN  token with content-publish permission. May be omitted when
#                    an outbound proxy injects the Authorization header.
#   IG_GRAPH_HOST    graph.instagram.com (Instagram Login, default) or
#                    graph.facebook.com (Facebook Login)
#   IG_USER_ID       Instagram account id (default: me)
#   GRAPH_VERSION    default v27.0
#   COVER_OFFSET_MS  frame used as the grid cover (default 1500)
#   POLL_SECONDS / POLL_ATTEMPTS   default 20s x 20
set -euo pipefail

video_url="${1:?usage: publish_reel.sh <video-url> <caption-file>}"
caption_file="${2:?usage: publish_reel.sh <video-url> <caption-file>}"
[ -f "$caption_file" ] || { echo "no such caption file: $caption_file" >&2; exit 1; }

HOST="${IG_GRAPH_HOST:-graph.instagram.com}"
VER="${GRAPH_VERSION:-v27.0}"
IG="${IG_USER_ID:-me}"
BASE="${IG_GRAPH_BASE_URL:-https://${HOST}}/${VER}"
auth=(); [ -n "${IG_ACCESS_TOKEN:-}" ] && auth=(-H "Authorization: Bearer ${IG_ACCESS_TOKEN}")

call() { # call METHOD URL [curl args...] -> body on stdout, fails with the API message
  local method="$1" url="$2"; shift 2
  local resp code
  resp="$(curl -sS --max-time 60 -X "$method" -w '\n%{http_code}' "${auth[@]}" "$url" "$@")"
  code="$(printf '%s' "$resp" | tail -n1)"; resp="$(printf '%s' "$resp" | sed '$d')"
  if [ "$code" != "200" ]; then
    echo "Graph API ${method} ${url%%\?*} -> HTTP ${code}: $(printf '%s' "$resp" | jq -r '.error.message // .' 2>/dev/null | head -c 300)" >&2
    return 1
  fi
  printf '%s' "$resp"
}

container="$(call POST "${BASE}/${IG}/media" \
  --data-urlencode "media_type=REELS" \
  --data-urlencode "video_url=${video_url}" \
  --data-urlencode "caption@${caption_file}" \
  --data-urlencode "thumb_offset=${COVER_OFFSET_MS:-1500}" \
  --data-urlencode "share_to_feed=true" | jq -r '.id')"
[ -n "$container" ] && [ "$container" != "null" ] || { echo "no container id returned" >&2; exit 1; }

status=""
for _ in $(seq 1 "${POLL_ATTEMPTS:-20}"); do
  status="$(call GET "${BASE}/${container}?fields=status_code,status" | jq -r '.status_code')"
  case "$status" in
    FINISHED) break ;;
    ERROR|EXPIRED) echo "container ${container} ended as ${status}; Instagram rejected the video" >&2; exit 1 ;;
  esac
  sleep "${POLL_SECONDS:-20}"
done
[ "$status" = "FINISHED" ] || { echo "container ${container} still ${status:-unknown} after polling; giving up" >&2; exit 1; }

media_id="$(call POST "${BASE}/${IG}/media_publish" --data-urlencode "creation_id=${container}" | jq -r '.id')"
permalink="$(call GET "${BASE}/${media_id}?fields=permalink" | jq -r '.permalink // ""' || true)"
printf '{"media_id":"%s","permalink":"%s"}\n' "$media_id" "$permalink"
