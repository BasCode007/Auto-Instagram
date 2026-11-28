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
  # one standalone 10-minute file per ffmpeg run: the segment muxer stops splitting
  # when Twitch ad breaks reset timestamps, and a killed run never finalises its file
  n=0
  while :; do
    f=$(printf "%s/rec_%s_%03d.mp4" "$out" "$stamp" "$n")
    ffmpeg -v error -nostdin -i "$m3u8" -t 600 -c copy -map 0:v:0 -map 0:a:0 -movflags +faststart "$f.part.mp4" || break
    mv "$f.part.mp4" "$f"
    n=$((n + 1))
  done
  echo "$(date -u +%T) recorder stopped (stream ended or URL expired), restarting"
  sleep 5
done
