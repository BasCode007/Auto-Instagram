#!/usr/bin/env bash
#
# render_quote_card.sh — render a vertical (1080x1920) motion quote card and
# print JSON: {"video_url":"https://...","duration":<seconds>}
#
# Requires: ImageMagick (convert), ffmpeg, and whatever upload_public.sh needs.
#
# Inputs (env):
#   QUOTE          (required) the quote text
#   HANDLE         account handle shown at the bottom, e.g. "@yourhandle"
#   DURATION       seconds (default 7)
#   BG_TOP/BG_BOTTOM  gradient colours (default deep navy)
#   TEXT_COLOR     quote colour (default white)
#   ACCENT         handle colour (default gold)
#   FONT           path to a .ttf (default: auto-detected bold sans)
#   MUSIC          optional path to a background music file
#   OUT_DIR        working/output dir (default: mktemp)
set -euo pipefail

command -v convert >/dev/null || { echo "need ImageMagick (convert)" >&2; exit 1; }
command -v ffmpeg  >/dev/null || { echo "need ffmpeg" >&2; exit 1; }
: "${QUOTE:?set QUOTE}"

HANDLE="${HANDLE:-}"
DURATION="${DURATION:-7}"
BG_TOP="${BG_TOP:-#0d1b2a}"
BG_BOTTOM="${BG_BOTTOM:-#16324f}"
TEXT_COLOR="${TEXT_COLOR:-white}"
ACCENT="${ACCENT:-#e0b100}"
FONT="${FONT:-$(fc-match -f '%{file}' 'DejaVu Sans:bold' 2>/dev/null || true)}"
FONT="${FONT:-/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
mkdir -p "$OUT_DIR"

bg="$OUT_DIR/bg.png"
text="$OUT_DIR/text.png"
card="$OUT_DIR/card.png"
out="$OUT_DIR/quote_card.mp4"

# 1) gradient background
convert -size 1080x1920 "gradient:${BG_TOP}-${BG_BOTTOM}" "$bg"

# 2) quote text, auto-wrapped and auto-sized to fit a 900x1400 box
convert -background none -fill "$TEXT_COLOR" -gravity center \
  -font "$FONT" -size 900x1400 "caption:${QUOTE}" "$text"

# 3) compose text over background, nudged up a little
convert "$bg" "$text" -gravity center -geometry +0-40 -composite "$card"

# 4) handle at the bottom
if [ -n "$HANDLE" ]; then
  convert "$card" -gravity south -fill "$ACCENT" -font "$FONT" \
    -pointsize 40 -annotate +0+90 "$HANDLE" "$card"
fi

# 5) still -> video with a slow ken-burns zoom
frames=$(( DURATION * 30 ))
vf="scale=1080:1920,zoompan=z='min(zoom+0.0006,1.10)':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p"

if [ -n "${MUSIC:-}" ] && [ -f "${MUSIC:-}" ]; then
  ffmpeg -y -loglevel error -loop 1 -i "$card" -i "$MUSIC" \
    -t "$DURATION" -vf "$vf" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 128k -shortest -movflags +faststart "$out"
else
  ffmpeg -y -loglevel error -loop 1 -i "$card" \
    -t "$DURATION" -vf "$vf" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 \
    -an -movflags +faststart "$out"
fi

# 6) publish to a public URL
here="$(cd "$(dirname "$0")" && pwd)"
url="$("$here/upload_public.sh" "$out")"
printf '{"video_url":"%s","duration":%s}\n' "$url" "$DURATION"
