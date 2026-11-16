# Shared helpers for the render scripts. Sourced, not executed.

# Print the path of the best available bold font: Inter first (installed in the
# renderer image), then DejaVu, which nearly every Linux has.
pick_font() {
  local f
  for f in \
    /usr/share/fonts/opentype/inter/Inter-Bold.otf \
    /usr/share/fonts/truetype/inter/Inter-Bold.ttf \
    /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf; do
    [ -f "$f" ] && { printf '%s' "$f"; return 0; }
  done
  fc-match -f '%{file}' 'sans:bold' 2>/dev/null
}
