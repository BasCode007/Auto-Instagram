#!/usr/bin/env bash
#
# render_quote_card.sh — render a vertical (1080x1920) motion quote card and
# print JSON: {"video_url":"https://...","duration":<seconds>}
#
# Layout respects the Instagram Reels UI safe zone: nothing important in the
# top ~250px, the bottom ~450px (username/caption overlay) or the right ~170px
# (like/comment/share column). The file always carries an AAC audio track.
#
# Requires: ImageMagick (convert), ffmpeg, and whatever upload_public.sh needs.
#
# Inputs (env):
#   QUOTE          (required) the quote text
#   PILLAR         optional label shown above the quote, e.g. "money_habits"
#   HANDLE         account handle shown under the quote, e.g. "@yourhandle"
#   DURATION       seconds (default 7)
#   BG_TOP/BG_BOTTOM  gradient colours (default deep navy)
#   TEXT_COLOR     quote colour (default white)
#   ACCENT         label/rule/handle colour (default gold)
#   FONT           path to a font file (default: Inter Bold, else DejaVu Bold)
#   MUSIC          optional path to a background music file (else silent track)
#   OUT_DIR        working/output dir (default: mktemp)
set -euo pipefail

command -v convert >/dev/null || { echo "need ImageMagick (convert)" >&2; exit 1; }
command -v ffmpeg  >/dev/null || { echo "need ffmpeg" >&2; exit 1; }
: "${QUOTE:?set QUOTE}"

here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/_lib.sh
. "$here/_lib.sh"

HANDLE="${HANDLE:-}"
PILLAR="${PILLAR:-}"
DURATION="${DURATION:-7}"
BG_TOP="${BG_TOP:-#0b1626}"
BG_BOTTOM="${BG_BOTTOM:-#17324d}"
TEXT_COLOR="${TEXT_COLOR:-white}"
ACCENT="${ACCENT:-#e0b100}"
FONT="${FONT:-$(pick_font)}"
OUT_DIR="${OUT_DIR:-$(mktemp -d)}"
mkdir -p "$OUT_DIR"

card="$OUT_DIR/card.png"
out="$OUT_DIR/quote_card.mp4"

# Type size steps down as the quote gets longer, so short quotes don't shout
# and long ones still fit the safe zone.
len=${#QUOTE}
if   [ "$len" -le 60 ];  then pt=92
elif [ "$len" -le 100 ]; then pt=78
elif [ "$len" -le 150 ]; then pt=66
else                          pt=56
fi

TEXT_W=780   # centred -> x 150..930, clear of the right-hand button column

# quote block: fixed width, wrapped, height grows with the text
convert -background none -fill "$TEXT_COLOR" -font "$FONT" -pointsize "$pt" \
  -interline-spacing 10 -gravity center -size "${TEXT_W}x" "caption:${QUOTE}" "$OUT_DIR/quote.png"

parts=()
if [ -n "$PILLAR" ]; then
  label="$(printf '%s' "$PILLAR" | tr '_' ' ' | tr '[:lower:]' '[:upper:]')"
  convert -background none -fill "$ACCENT" -font "$FONT" -pointsize 34 -kerning 8 \
    "label:${label}" "$OUT_DIR/label.png"
  parts+=("$OUT_DIR/label.png")
  convert -size 120x56 xc:none -fill "$ACCENT" -draw "rectangle 0,26 120,30" "$OUT_DIR/rule.png"
  parts+=("$OUT_DIR/rule.png")
fi
parts+=("$OUT_DIR/quote.png")
if [ -n "$HANDLE" ]; then
  convert -size 10x70 xc:none "$OUT_DIR/gap.png"
  convert -background none -fill "$ACCENT" -font "$FONT" -pointsize 38 "label:${HANDLE}" "$OUT_DIR/handle.png"
  parts+=("$OUT_DIR/gap.png" "$OUT_DIR/handle.png")
fi
convert -background none -gravity center "${parts[@]}" -append "$OUT_DIR/block.png"

# The block must fit the vertical safe zone (y 260..1460 = 1200px).
bh="$(convert "$OUT_DIR/block.png" -format '%h' info:)"
if [ "$bh" -gt 1200 ]; then
  convert "$OUT_DIR/block.png" -resize x1200 "$OUT_DIR/block.png"
fi

# gradient + soft vignette, block centred on the safe zone (100px above centre)
convert -size 1080x1920 "gradient:${BG_TOP}-${BG_BOTTOM}" \
  \( -size 1080x1920 radial-gradient:none-'rgba(0,0,0,0.45)' \) -compose over -composite \
  "$OUT_DIR/block.png" -gravity center -geometry +0-100 -compose over -composite "$card"

# still -> video with a slow zoom; always attach an audio track
frames=$(( DURATION * 30 ))
vf="scale=2160:3840,zoompan=z='min(zoom+0.0005,1.06)':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p"
if [ -n "${MUSIC:-}" ] && [ -f "${MUSIC:-}" ]; then
  audio_in=(-stream_loop -1 -i "$MUSIC"); afilt="volume=0.6,afade=t=out:st=$((DURATION-1)):d=1"
else
  audio_in=(-f lavfi -i "anullsrc=r=44100:cl=stereo"); afilt="anull"
fi
ffmpeg -y -loglevel error -loop 1 -i "$card" "${audio_in[@]}" \
  -t "$DURATION" -vf "$vf" -af "$afilt" \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 -g 60 \
  -c:a aac -b:a 128k -ar 44100 -movflags +faststart "$out"

url="$("$here/upload_public.sh" "$out")"
printf '{"video_url":"%s","duration":%s}\n' "$url" "$DURATION"
