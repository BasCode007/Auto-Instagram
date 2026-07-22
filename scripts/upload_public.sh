#!/usr/bin/env bash
#
# upload_public.sh — put a rendered file somewhere with a PUBLIC https URL and
# print that URL to stdout. The Instagram Graph API fetches the video from a
# public URL, so every rendered Reel has to land somewhere reachable.
#
# Backends (set UPLOADER):
#   cloudinary  (default) — free tier, unsigned upload preset.
#                 Needs: CLOUDINARY_CLOUD_NAME, CLOUDINARY_UPLOAD_PRESET
#   copy        — copy into a directory you already serve over https.
#                 Needs: PUBLIC_DIR, PUBLIC_BASE_URL
#
# Usage: upload_public.sh /path/to/file.mp4
set -euo pipefail

file="${1:?usage: upload_public.sh <file>}"
[ -f "$file" ] || { echo "upload_public.sh: no such file: $file" >&2; exit 1; }

uploader="${UPLOADER:-cloudinary}"

case "$uploader" in
  cloudinary)
    : "${CLOUDINARY_CLOUD_NAME:?set CLOUDINARY_CLOUD_NAME}"
    : "${CLOUDINARY_UPLOAD_PRESET:?set CLOUDINARY_UPLOAD_PRESET}"
    resp="$(curl -sS -f \
      -F "file=@${file}" \
      -F "upload_preset=${CLOUDINARY_UPLOAD_PRESET}" \
      "https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/video/upload")"
    url="$(printf '%s' "$resp" | jq -r '.secure_url')"
    [ -n "$url" ] && [ "$url" != "null" ] || {
      echo "upload_public.sh: cloudinary upload failed: $resp" >&2; exit 1; }
    printf '%s\n' "$url"
    ;;
  copy)
    : "${PUBLIC_DIR:?set PUBLIC_DIR}"
    : "${PUBLIC_BASE_URL:?set PUBLIC_BASE_URL}"
    mkdir -p "$PUBLIC_DIR"
    base="$(basename "$file")"
    cp -f "$file" "${PUBLIC_DIR%/}/${base}"
    printf '%s/%s\n' "${PUBLIC_BASE_URL%/}" "$base"
    ;;
  *)
    echo "upload_public.sh: unknown UPLOADER '$uploader'" >&2
    exit 1
    ;;
esac
