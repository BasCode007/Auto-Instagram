#!/usr/bin/env bash
# Scan each finished chunk from tools/record_live.sh as soon as the next one starts.
# Usage: bash tools/watch_chunks.sh <name> <creator> <platform> <channel-url>
set -u
name="$1"; creator="$2"; platform="$3"; chan="$4"
dir="$(dirname "$0")/../media/raw/live-$name"
done_list="$dir/.scanned"; touch "$done_list"
while true; do
  files=$(ls "$dir"/rec_*.mp4 2>/dev/null | sort)
  newest=$(echo "$files" | tail -1)
  for f in $files; do
    [ "$f" = "$newest" ] && continue                 # still being written
    grep -qxF "$f" "$done_list" && continue
    echo "$(date -u +%T) scanning $(basename "$f")"
    python3 "$(dirname "$0")/autoclip.py" scan --file "$f" --creator "$creator" \
      --platform "$platform" --source-url "$chan" --top 5 --thumbs 2>&1 | grep -v -i warning
    echo "$f" >> "$done_list"
  done
  sleep 30
done
