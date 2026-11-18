#!/usr/bin/env bash
# Record a public Twitch/Kick live stream into 10-minute MP4 chunks
# (media/raw/live-<name>/rec_<UTC time>_NNN.mp4) so finished chunks can be
# scanned and clipped while the stream keeps recording.
# Usage: bash tools/record_live.sh <channel-url> <name> [format]
set -u
url="$1"; name="$2"; fmt="${3:-1080p60/1080p/720p60/best}"
out="$(dirname "$0")/../media/raw/live-$name"
mkdir -p "$out"
while true; do
  m3u8=$(yt-dlp --no-warnings -g -f "$fmt" "$url" 2>/dev/null | head -1)
  if [ -z "$m3u8" ]; then echo "$(date -u +%T) offline or unavailable, retrying in 60s"; sleep 60; continue; fi
  stamp=$(date -u +%Y%m%dT%H%M%S)
  echo "$(date -u +%T) recording -> $out/rec_${stamp}_NNN.mp4"
  ffmpeg -v error -nostdin -i "$m3u8" -c copy -map 0:v:0 -map 0:a:0 -f segment -segment_time 600 \
    -reset_timestamps 1 -segment_format mp4 "$out/rec_${stamp}_%03d.mp4"
  echo "$(date -u +%T) recorder stopped (stream ended or URL expired), restarting"
  sleep 5
done
