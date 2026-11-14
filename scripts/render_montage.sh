#!/usr/bin/env bash
#
# render_montage.sh — render a narrated montage Reel at the standard in
# docs/STANDARD.md and print JSON: {"video_url":"https://...","duration":<s>}
#
#   voice (ElevenLabs with word timings, or VOICE_FILE [+ WORDS_JSON])
#   -> a new shot every CUT seconds: AI hero shots from ComfyUI when
#      COMFYUI_URL is set, then portrait stock (Pexels HD renditions or BROLL_DIR)
#   -> cinematic grade, slow push-in, grain, vignette
#   -> big centred word-revealed captions -> music at about -12 dB -> public URL
#
# Inputs (env):
#   SCRIPT_TEXT          (required) the voiceover text
#   BROLL_KEYWORDS       comma-separated stock search terms (unless BROLL_DIR)
#   HERO_PROMPTS         '||'-separated text-to-video prompts for ComfyUI (optional)
#   COMFYUI_URL          e.g. http://comfyui:8188 (optional; skipped when unset/unreachable)
#   COMFY_SHOTS          max AI shots per reel (default 2)   COMFY_SECONDS (default 5)
#   CUT                  seconds per shot (default 1.3)
#   MUSIC                background track path (optional)   MUSIC_LEVEL (default 0.25)
#   ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID   unless VOICE_FILE
#   VOICE_FILE           pre-made voice audio;  WORDS_JSON optional word timings for it
#   PEXELS_API_KEY       unless BROLL_DIR;      BROLL_DIR local *.mp4 instead of Pexels
#   CAPTION_FONT         default Inter (installed in the renderer image)
#   OUT_DIR              working dir (default mktemp)
set -euo pipefail
for bin in curl jq ffmpeg ffprobe python3; do command -v "$bin" >/dev/null || { echo "need $bin" >&2; exit 1; }; done
: "${SCRIPT_TEXT:?set SCRIPT_TEXT}"

here="$(cd "$(dirname "$0")" && pwd)"
CUT="${CUT:-1.3}"; MUSIC_LEVEL="${MUSIC_LEVEL:-0.25}"
COMFY_SHOTS="${COMFY_SHOTS:-2}"; COMFY_SECONDS="${COMFY_SECONDS:-5}"
EL_BASE="${ELEVENLABS_BASE_URL:-https://api.elevenlabs.io}"; PX_BASE="${PEXELS_BASE_URL:-https://api.pexels.com}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"; mkdir -p "$OUT_DIR"
FONTS_DIR=""
if [ -z "${CAPTION_FONT:-}" ]; then
  if [ -d /usr/share/fonts/opentype/inter ]; then CAPTION_FONT="Inter"; FONTS_DIR="/usr/share/fonts/opentype/inter"; else CAPTION_FONT="DejaVu Sans"; fi
fi
sub_filter="subtitles=captions.ass${FONTS_DIR:+:fontsdir=${FONTS_DIR}}"
voice="$OUT_DIR/voice.mp3"; printf '%s' "$SCRIPT_TEXT" > "$OUT_DIR/script.txt"

# 1) Voice -------------------------------------------------------------------
cap_args=()
if [ -n "${VOICE_FILE:-}" ]; then
  cp -f "$VOICE_FILE" "$voice"
  [ -n "${WORDS_JSON:-}" ] && [ -f "$WORDS_JSON" ] && cap_args=(--words-json "$WORDS_JSON")
else
  : "${ELEVENLABS_API_KEY:?set ELEVENLABS_API_KEY}"; : "${ELEVENLABS_VOICE_ID:?set ELEVENLABS_VOICE_ID}"
  jq -n --arg t "$SCRIPT_TEXT" --arg m "${ELEVENLABS_MODEL:-eleven_multilingual_v2}" \
    '{text:$t, model_id:$m, voice_settings:{stability:0.55, similarity_boost:0.75, style:0.2}}' > "$OUT_DIR/tts_req.json"
  curl -sS -f --retry 2 --max-time 120 -X POST \
    "${EL_BASE}/v1/text-to-speech/${ELEVENLABS_VOICE_ID}/with-timestamps?output_format=mp3_44100_128" \
    -H "xi-api-key: ${ELEVENLABS_API_KEY}" -H "Content-Type: application/json" \
    --data @"$OUT_DIR/tts_req.json" -o "$OUT_DIR/tts.json"
  jq -r '.audio_base64' "$OUT_DIR/tts.json" | base64 -d > "$voice"
  [ -s "$voice" ] || { echo "ElevenLabs returned no audio: $(head -c 200 "$OUT_DIR/tts.json")" >&2; exit 1; }
  cap_args=(--alignment "$OUT_DIR/tts.json")
fi
dur="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$voice")"
total="$(awk -v d="$dur" 'BEGIN{printf "%.2f", d + 0.5}')"
nseg="$(awk -v t="$total" -v c="$CUT" 'BEGIN{n=int(t/c); if (n*c < t) n++; print n}')"

# 2) Shots: AI hero clips first, then stock --------------------------------------
clips=()
if [ -n "${COMFYUI_URL:-}" ] && [ -n "${HERO_PROMPTS:-}" ] && curl -sS -m 5 "${COMFYUI_URL%/}/system_stats" >/dev/null 2>&1; then
  i=0
  while IFS= read -r -d '' p || [ -n "$p" ]; do
    [ "$i" -ge "$COMFY_SHOTS" ] && break
    p="$(printf '%s' "$p" | sed 's/^ *//; s/ *$//')"; [ -n "$p" ] || continue
    if python3 "$here/../pipeline_v2/comfy_client.py" "$p" "$OUT_DIR/hero_${i}.mp4" --seconds "$COMFY_SECONDS" \
         --url "$COMFYUI_URL" --timeout "${COMFY_TIMEOUT:-900}" >/dev/null 2>"$OUT_DIR/comfy_${i}.err"; then
      clips+=("$OUT_DIR/hero_${i}.mp4"); i=$(( i + 1 ))
    else
      echo "comfyui shot failed: $(tail -c 300 "$OUT_DIR/comfy_${i}.err")" >&2
    fi
  done < <(printf '%s' "$HERO_PROMPTS" | sed 's/||/\x0/g')
fi
if [ -n "${BROLL_DIR:-}" ]; then
  while IFS= read -r f; do clips+=("$f"); done < <(find "$BROLL_DIR" -maxdepth 1 -name '*.mp4' | sort)
else
  : "${BROLL_KEYWORDS:?set BROLL_KEYWORDS}"; : "${PEXELS_API_KEY:?set PEXELS_API_KEY}"
  IFS=',' read -ra kws <<< "$BROLL_KEYWORDS"; links=()
  for kw in "${kws[@]}"; do
    kw="$(printf '%s' "$kw" | sed 's/^ *//; s/ *$//')"; [ -n "$kw" ] || continue
    resp="$(curl -sS -f --retry 2 --max-time 30 -G "${PX_BASE}/videos/search" -H "Authorization: ${PEXELS_API_KEY}" \
      --data-urlencode "query=${kw}" --data-urlencode "orientation=portrait" --data-urlencode "per_page=15")" || continue
    while IFS= read -r l; do [ -n "$l" ] && links+=("$l"); done < <(printf '%s' "$resp" | jq -r '
      .videos[]? | select((.duration // 99) >= 4) | [.video_files[]? | select(.height > .width and .width >= 1000)]
      | sort_by((.width - 1080) | fabs) | .[0].link // empty' | shuf | head -n 3)
  done
  want=$(( nseg / 2 + 2 )); [ "$want" -gt 12 ] && want=12; idx=0
  for l in $(printf '%s\n' "${links[@]}" | shuf); do
    [ "$idx" -ge "$want" ] && break
    raw="$OUT_DIR/broll_${idx}.mp4"; curl -sS -fL --retry 2 --max-time 120 "$l" -o "$raw" || continue
    clips+=("$raw"); idx=$(( idx + 1 ))
  done
fi
[ "${#clips[@]}" -gt 0 ] || { echo "no usable footage" >&2; exit 1; }

# 3) Cut a shot every CUT seconds, cycling clips and advancing into each one --------
declare -A off; : > "$OUT_DIR/list.txt"
grade="eq=contrast=1.10:brightness=-0.03:saturation=0.90,colorbalance=rs=-0.04:bs=0.05:rh=0.06:bh=-0.06,vignette=PI/4.5,noise=alls=5:allf=t"
for i in $(seq 0 $(( nseg - 1 ))); do
  src="${clips[$(( i % ${#clips[@]} ))]}"
  len="$(awk -v t="$total" -v c="$CUT" -v i="$i" 'BEGIN{l=t-i*c; if (l>c) l=c; printf "%.2f", l}')"
  sdur="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$src")"
  start="${off[$src]:-0.3}"
  if awk -v s="$start" -v l="$len" -v d="$sdur" 'BEGIN{exit !(s + l > d - 0.1)}'; then start=0.3; fi
  off[$src]="$(awk -v s="$start" -v c="$CUT" 'BEGIN{printf "%.2f", s + c + 0.7}')"
  ffmpeg -y -loglevel error -ss "$start" -t "$len" -i "$src" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,scale=eval=frame:w='trunc(1080*(1+0.08*t/${CUT})/2)*2':h=-2,crop=1080:1920,${grade},format=yuv420p" \
    -an -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$OUT_DIR/seg_${i}.mp4"
  printf "file 'seg_%s.mp4'\n" "$i" >> "$OUT_DIR/list.txt"
done
( cd "$OUT_DIR" && ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -c copy visuals.mp4 )

# 4) Captions ----------------------------------------------------------------
python3 "$here/make_captions.py" --out "$OUT_DIR/captions.ass" --duration "$total" --text "$OUT_DIR/script.txt" --font "$CAPTION_FONT" "${cap_args[@]}"

# 5) Mix ---------------------------------------------------------------------
cd "$OUT_DIR"
fade_at="$(awk -v t="$total" 'BEGIN{printf "%.2f", (t > 2.5) ? t - 2.5 : 0}')"
if [ -n "${MUSIC:-}" ] && [ -f "${MUSIC:-}" ]; then
  ffmpeg -y -loglevel error -i visuals.mp4 -i voice.mp3 -stream_loop -1 -i "$MUSIC" \
    -filter_complex "[0:v]${sub_filter}[v];[2:a]volume=${MUSIC_LEVEL},afade=t=in:d=1,afade=t=out:st=${fade_at}:d=2.5[mus];[1:a]apad[vo];[vo][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]" \
    -map "[v]" -map "[a]" -t "$total" -c:v libx264 -profile:v high -crf 21 -maxrate 10M -bufsize 20M -pix_fmt yuv420p -r 30 -g 60 -c:a aac -b:a 160k -ar 44100 -movflags +faststart reel.mp4
else
  ffmpeg -y -loglevel error -i visuals.mp4 -i voice.mp3 -filter_complex "[0:v]${sub_filter}[v];[1:a]apad[a]" \
    -map "[v]" -map "[a]" -t "$total" -c:v libx264 -profile:v high -crf 21 -maxrate 10M -bufsize 20M -pix_fmt yuv420p -r 30 -g 60 -c:a aac -b:a 160k -ar 44100 -movflags +faststart reel.mp4
fi
cd - >/dev/null
url="$("$here/upload_public.sh" "$OUT_DIR/reel.mp4")"
printf '{"video_url":"%s","duration":%s,"shots":%s,"ai_shots":%s}\n' "$url" "$total" "$nseg" "$(ls "$OUT_DIR"/hero_*.mp4 2>/dev/null | wc -l)"
