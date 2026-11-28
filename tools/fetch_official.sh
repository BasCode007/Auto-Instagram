#!/usr/bin/env bash
# Download the official GTA 6 trailers from Rockstar's media page into media/raw/.
# Usage: bash tools/fetch_official.sh [Launch_Trailer Trailer_1 Trailer_2 Pre-Load_Now]
set -euo pipefail
cd "$(dirname "$0")/.."
BASE=https://media-rockstargames-com.akamaized.net/VI/downloads/videos
names=("$@")
[ ${#names[@]} -eq 0 ] && names=(Launch_Trailer Trailer_1 Trailer_2 Pre-Load_Now)
mkdir -p media/raw
for n in "${names[@]}"; do
  f="GTAVI_${n}"
  echo "-> $f.mp4"
  curl -fL --retry 4 -C - -o "media/raw/$f.mp4" "$BASE/$f/$f.mp4"
done
