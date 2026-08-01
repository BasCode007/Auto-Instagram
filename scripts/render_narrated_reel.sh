#!/usr/bin/env bash
#
# render_narrated_reel.sh — render a faceless narrated vertical Reel and print
# JSON: {"video_url":"https://...","duration":<seconds>}
#
# Pipeline: ElevenLabs voiceover -> Pexels b-roll -> ffmpeg compose (b-roll +
# voiceover + optional music + optional on-screen hook) -> public URL.
#
# Requires: curl, jq, ffmpeg, ffprobe, and whatever upload_public.sh needs.
#
# Inputs (env):
#   SCRIPT_TEXT        (required) the voiceover text
#   BROLL_KEYWORDS     (required) comma-separated stock search terms
#   ON_SCREEN_HOOK     optional short text shown for the first 3.5s
#   HANDLE             optional handle (currently informational)
#   MUSIC              optional path to a background music file
#   ELEVENLABS_API_KEY (required)   ELEVENLABS_VOICE_ID (required)
#   ELEVENLABS_MODEL   default eleven_multilingual_v2
#   PEXELS_API_KEY     (required)
#   FONT               path to a .ttf (default: auto-detected bold sans)
#   OUT_DIR            working/output dir (default: mktemp)
set -euo pipefail

for bin in curl jq ffmpeg ffprobe; do
  command -v "$bin" >/dev/null || { echo "need $bin" >&2; exit 1; }
done
: "${SCRIPT_TEXT:?set SCRIPT_TEXT}"
: "${BROLL_KEYWORDS:?set BROLL_KEYWORDS}"
: "${ELEVENLABS_API_KEY:?set ELEVENLABS_API_KEY}"
: "${ELEVENLABS_VOICE_ID:?set ELEVENLABS_VOICE_ID}"
: "${PEXELS_API_KEY:?set PEXELS_API_KEY}"

ELEVENLABS_MODEL="${ELEVENLABS_MODEL:-eleven_multilingual_v2}"
FONT="${FONT:-$(fc-match -f '%{file}' 'DejaVu Sans:bold' 2>/dev/null || true)}"
FONT="${FONT:-/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
mkdir -p "$OUT_DIR"

voice="$OUT_DIR/voice.mp3"
out="$OUT_DIR/reel.mp4"

# 1) Voiceover via ElevenLabs -----------------------------------------------
jq -n --arg t "$SCRIPT_TEXT" --arg m "$ELEVENLABS_MODEL" \
  '{text:$t, model_id:$m, voice_settings:{stability:0.5, similarity_boost:0.75}}' \
  > "$OUT_DIR/tts.json"
curl -sS -f -X POST \
  "https://api.elevenlabs.io/v1/text-to-speech/${ELEVENLABS_VOICE_ID}" \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: audio/mpeg" \
  --data @"$OUT_DIR/tts.json" -o "$voice"

dur="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$voice")"
dur_ceil=$(( $(printf '%.0f' "$dur") + 1 ))

# 2a) Download up to 3 portrait b-roll clips from Pexels ---------------------
IFS=',' read -ra kws <<< "$BROLL_KEYWORDS"
raw_clips=()
idx=0
for kw in "${kws[@]}"; do
  kw="$(printf '%s' "$kw" | sed 's/^ *//; s/ *$//')"
  [ -n "$kw" ] || continue
  [ "$idx" -ge 3 ] && break
  resp="$(curl -sS -f -G "https://api.pexels.com/videos/search" \
    -H "Authorization: ${PEXELS_API_KEY}" \
    --data-urlencode "query=${kw}" \
    --data-urlencode "orientation=portrait" \
    --data-urlencode "per_page=3")" || continue
  link="$(printf '%s' "$resp" | jq -r \
    'first(.videos[].video_files[] | select(.height > .width and .width >= 720) | .link)
     // first(.videos[].video_files[] | select(.height > .width) | .link) // empty')"
  [ -n "$link" ] || continue
  raw="$OUT_DIR/broll_${idx}.mp4"
  curl -sS -fL "$link" -o "$raw" || continue
  raw_clips+=("$raw")
  idx=$(( idx + 1 ))
done

[ "${#raw_clips[@]}" -gt 0 ] || { echo "no usable b-roll found for: $BROLL_KEYWORDS" >&2; exit 1; }

# 2b) Normalise each clip to an equal slot that together covers the voiceover.
#     Sized to the clips we actually got, so partial Pexels failures still fill.
nclips="${#raw_clips[@]}"
seg=$(( dur_ceil / nclips + 1 ))
[ "$seg" -ge 2 ] || seg=2
norm_clips=()
i=0
for raw in "${raw_clips[@]}"; do
  norm="$OUT_DIR/norm_${i}.mp4"
  ffmpeg -y -loglevel error -stream_loop -1 -i "$raw" -t "$seg" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,format=yuv420p" \
    -an -c:v libx264 -profile:v high -pix_fmt yuv420p "$norm"
  norm_clips+=("$norm")
  i=$(( i + 1 ))
done

# 3) Concatenate b-roll and trim to the voiceover length ---------------------
: > "$OUT_DIR/list.txt"
for c in "${norm_clips[@]}"; do printf "file '%s'\n" "$c" >> "$OUT_DIR/list.txt"; done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT_DIR/list.txt" -c copy "$OUT_DIR/visuals_full.mp4"
ffmpeg -y -loglevel error -i "$OUT_DIR/visuals_full.mp4" -t "$dur_ceil" -c copy "$OUT_DIR/visuals.mp4"

# 4) Compose: visuals + voiceover (+ music) (+ on-screen hook) ---------------
if [ -n "${ON_SCREEN_HOOK:-}" ]; then
  printf '%s' "$ON_SCREEN_HOOK" > "$OUT_DIR/hook.txt"
  vfilter="[0:v]drawtext=fontfile=${FONT}:textfile=${OUT_DIR}/hook.txt:fontcolor=white:fontsize=64:line_spacing=10:box=1:boxcolor=black@0.45:boxborderw=24:x=(w-text_w)/2:y=200:enable='lt(t,3.5)'[v]"
else
  vfilter="[0:v]copy[v]"
fi

if [ -n "${MUSIC:-}" ] && [ -f "${MUSIC:-}" ]; then
  ffmpeg -y -loglevel error -i "$OUT_DIR/visuals.mp4" -i "$voice" -i "$MUSIC" \
    -filter_complex "${vfilter};[2:a]volume=0.15[mus];[1:a]volume=1.0[vo];[vo][mus]amix=inputs=2:duration=first:dropout_transition=0[a]" \
    -map "[v]" -map "[a]" -t "$dur_ceil" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 128k -movflags +faststart "$out"
else
  ffmpeg -y -loglevel error -i "$OUT_DIR/visuals.mp4" -i "$voice" \
    -filter_complex "$vfilter" \
    -map "[v]" -map 1:a -t "$dur_ceil" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 128k -movflags +faststart "$out"
fi

# 5) Publish -----------------------------------------------------------------
here="$(cd "$(dirname "$0")" && pwd)"
url="$("$here/upload_public.sh" "$out")"
printf '{"video_url":"%s","duration":%s}\n' "$url" "$dur_ceil"
