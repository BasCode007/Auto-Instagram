#!/usr/bin/env bash
#
# render_narrated_reel.sh — render a faceless narrated vertical Reel and print
# JSON: {"video_url":"https://...","duration":<seconds>}
#
# Pipeline: voiceover (ElevenLabs, with word timings) -> portrait b-roll
# (Pexels) cut every few seconds -> burned-in captions + opening hook ->
# optional music bed -> public URL.
#
# Requires: curl, jq, ffmpeg (with libass), ffprobe, python3.
#
# Inputs (env):
#   SCRIPT_TEXT        (required) the voiceover text
#   BROLL_KEYWORDS     comma-separated stock search terms (required unless BROLL_DIR)
#   ON_SCREEN_HOOK     optional short text shown for the first 3s
#   MUSIC              optional path to a background music file
#   ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID   required unless VOICE_FILE is set
#   ELEVENLABS_MODEL   default eleven_multilingual_v2
#   PEXELS_API_KEY     required unless BROLL_DIR is set
#   VOICE_FILE         use this audio instead of calling ElevenLabs
#   BROLL_DIR          use the *.mp4 in this dir instead of calling Pexels
#   CAPTION_FONT       font family for captions (default Inter, else DejaVu Sans)
#   ELEVENLABS_BASE_URL / PEXELS_BASE_URL      override API hosts (tests)
#   OUT_DIR            working/output dir (default: mktemp)
set -euo pipefail

for bin in curl jq ffmpeg ffprobe python3; do
  command -v "$bin" >/dev/null || { echo "need $bin" >&2; exit 1; }
done
: "${SCRIPT_TEXT:?set SCRIPT_TEXT}"

here="$(cd "$(dirname "$0")" && pwd)"
ELEVENLABS_MODEL="${ELEVENLABS_MODEL:-eleven_multilingual_v2}"
EL_BASE="${ELEVENLABS_BASE_URL:-https://api.elevenlabs.io}"
PX_BASE="${PEXELS_BASE_URL:-https://api.pexels.com}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
mkdir -p "$OUT_DIR"
# libass needs to be pointed at the font directory explicitly to find Inter.
FONTS_DIR=""
if [ -z "${CAPTION_FONT:-}" ]; then
  if [ -d /usr/share/fonts/opentype/inter ]; then
    CAPTION_FONT="Inter"; FONTS_DIR="/usr/share/fonts/opentype/inter"
  else
    CAPTION_FONT="DejaVu Sans"
  fi
fi
sub_filter="subtitles=captions.ass${FONTS_DIR:+:fontsdir=${FONTS_DIR}}"

voice="$OUT_DIR/voice.mp3"
out="$OUT_DIR/reel.mp4"
printf '%s' "$SCRIPT_TEXT" > "$OUT_DIR/script.txt"

# 1) Voiceover ---------------------------------------------------------------
align_args=()
if [ -n "${VOICE_FILE:-}" ]; then
  cp -f "$VOICE_FILE" "$voice"
else
  : "${ELEVENLABS_API_KEY:?set ELEVENLABS_API_KEY}"
  : "${ELEVENLABS_VOICE_ID:?set ELEVENLABS_VOICE_ID}"
  jq -n --arg t "$SCRIPT_TEXT" --arg m "$ELEVENLABS_MODEL" \
    '{text:$t, model_id:$m, voice_settings:{stability:0.5, similarity_boost:0.75}}' > "$OUT_DIR/tts_req.json"
  # with-timestamps returns the audio plus per-character timings for captions
  curl -sS -f --retry 2 --max-time 120 -X POST \
    "${EL_BASE}/v1/text-to-speech/${ELEVENLABS_VOICE_ID}/with-timestamps?output_format=mp3_44100_128" \
    -H "xi-api-key: ${ELEVENLABS_API_KEY}" -H "Content-Type: application/json" \
    --data @"$OUT_DIR/tts_req.json" -o "$OUT_DIR/tts.json"
  jq -r '.audio_base64' "$OUT_DIR/tts.json" | base64 -d > "$voice"
  [ -s "$voice" ] || { echo "ElevenLabs returned no audio: $(head -c 200 "$OUT_DIR/tts.json")" >&2; exit 1; }
  align_args=(--alignment "$OUT_DIR/tts.json")
fi

dur="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$voice")"
total="$(awk -v d="$dur" 'BEGIN{printf "%.2f", d + 0.6}')"     # short tail after the last word
total_ceil="$(awk -v d="$total" 'BEGIN{printf "%d", (d == int(d)) ? d : int(d) + 1}')"

# 2) B-roll: one clip per ~4.5s so the picture keeps moving ------------------
want=$(( (total_ceil + 4) / 5 )); [ "$want" -lt 3 ] && want=3; [ "$want" -gt 8 ] && want=8
raw_clips=()
if [ -n "${BROLL_DIR:-}" ]; then
  while IFS= read -r f; do raw_clips+=("$f"); done < <(find "$BROLL_DIR" -maxdepth 1 -name '*.mp4' | sort)
else
  : "${BROLL_KEYWORDS:?set BROLL_KEYWORDS}"
  : "${PEXELS_API_KEY:?set PEXELS_API_KEY}"
  IFS=',' read -ra kws <<< "$BROLL_KEYWORDS"
  links=()
  for kw in "${kws[@]}"; do
    kw="$(printf '%s' "$kw" | sed 's/^ *//; s/ *$//')"; [ -n "$kw" ] || continue
    resp="$(curl -sS -f --retry 2 --max-time 30 -G "${PX_BASE}/videos/search" \
      -H "Authorization: ${PEXELS_API_KEY}" --data-urlencode "query=${kw}" \
      --data-urlencode "orientation=portrait" --data-urlencode "per_page=15")" || continue
    # per video: the portrait rendition closest to 1080 wide (not the 4K one);
    # shuffled so the same keyword doesn't yield the same clip every post
    while IFS= read -r l; do [ -n "$l" ] && links+=("$l"); done < <(printf '%s' "$resp" | jq -r '
      .videos[]? | [.video_files[]? | select(.height > .width and .width >= 720)]
      | sort_by((.width - 1080) | fabs) | .[0].link // empty' | shuf | head -n 4)
  done
  idx=0
  for l in $(printf '%s\n' "${links[@]}" | shuf); do
    [ "$idx" -ge "$want" ] && break
    raw="$OUT_DIR/broll_${idx}.mp4"
    curl -sS -fL --retry 2 --max-time 120 "$l" -o "$raw" || continue
    raw_clips+=("$raw"); idx=$(( idx + 1 ))
  done
fi
[ "${#raw_clips[@]}" -gt 0 ] || { echo "no usable b-roll found" >&2; exit 1; }

# Cycle through what we got until the voiceover is covered.
nseg="$want"; [ "${#raw_clips[@]}" -gt "$nseg" ] && nseg="${#raw_clips[@]}"
seg="$(awk -v t="$total" -v n="$nseg" 'BEGIN{printf "%.2f", t / n + 0.05}')"
: > "$OUT_DIR/list.txt"
for i in $(seq 0 $(( nseg - 1 ))); do
  src="${raw_clips[$(( i % ${#raw_clips[@]} ))]}"
  norm="$OUT_DIR/norm_${i}.mp4"
  ffmpeg -y -loglevel error -stream_loop -1 -i "$src" -t "$seg" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,eq=brightness=-0.06:saturation=1.05,format=yuv420p" \
    -an -c:v libx264 -preset veryfast -profile:v high -pix_fmt yuv420p "$norm"
  printf "file '%s'\n" "$norm" >> "$OUT_DIR/list.txt"
done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT_DIR/list.txt" -c copy "$OUT_DIR/visuals.mp4"

# 3) Captions + hook ---------------------------------------------------------
python3 "$here/make_captions.py" --out "$OUT_DIR/captions.ass" --duration "$total" \
  --text "$OUT_DIR/script.txt" --hook "${ON_SCREEN_HOOK:-}" --font "$CAPTION_FONT" "${align_args[@]}"

# 4) Compose -----------------------------------------------------------------
# (cd into OUT_DIR so the subtitles filter gets a path with nothing to escape)
cd "$OUT_DIR"
if [ -n "${MUSIC:-}" ] && [ -f "${MUSIC:-}" ]; then
  ffmpeg -y -loglevel error -i visuals.mp4 -i voice.mp3 -stream_loop -1 -i "$MUSIC" \
    -filter_complex "[0:v]${sub_filter}[v];[2:a]volume=0.12[mus];[1:a]apad[vo];[vo][mus]amix=inputs=2:duration=first:dropout_transition=0[a]" \
    -map "[v]" -map "[a]" -t "$total" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 -g 60 \
    -c:a aac -b:a 128k -ar 44100 -movflags +faststart reel.mp4
else
  ffmpeg -y -loglevel error -i visuals.mp4 -i voice.mp3 \
    -filter_complex "[0:v]${sub_filter}[v];[1:a]apad[a]" \
    -map "[v]" -map "[a]" -t "$total" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 -g 60 \
    -c:a aac -b:a 128k -ar 44100 -movflags +faststart reel.mp4
fi
cd - >/dev/null

# 5) Publish -----------------------------------------------------------------
url="$("$here/upload_public.sh" "$out")"
printf '{"video_url":"%s","duration":%s}\n' "$url" "$total"
