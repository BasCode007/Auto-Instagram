#!/usr/bin/env python3
"""Publish a finished clip to Instagram as a Reel (Instagram Graph API).

Uploads the local MP4 with the resumable upload flow (no public URL needed),
waits for Instagram to process it, publishes it, and appends a row to
log.md and scoreboard.csv.

Requirements
  * Instagram Professional account (Creator or Business) linked to a
    Facebook Page, and an access token with instagram_content_publish.
  * Environment: IG_USER_ID, IG_ACCESS_TOKEN (put them in .env; never commit).

Safety
  Without --confirm this only prints what it would post. Posting is an
  outward-facing action: get approval on the exact caption and clip first.

Usage
  python3 tools/post_instagram.py clips/001-out-now.json             # dry run
  python3 tools/post_instagram.py clips/001-out-now.json --confirm   # posts
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "v21.0"
GRAPH = f"https://graph.facebook.com/{API}"
RUPLOAD = f"https://rupload.facebook.com/ig-api-upload/{API}"


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def call(method: str, url: str, params: dict | None = None,
         data: bytes | None = None, headers: dict | None = None) -> dict:
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"Instagram API error {e.code}: {e.read().decode()}")


def publish(video: Path, caption: str, cover_offset_ms: int, share_to_feed: bool) -> str:
    uid, token = os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"]
    # 1. create a resumable REELS container
    c = call("POST", f"{GRAPH}/{uid}/media", {
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": str(share_to_feed).lower(), "thumb_offset": cover_offset_ms,
        "access_token": token})
    cid = c["id"]
    # 2. upload the bytes
    size = video.stat().st_size
    call("POST", f"{RUPLOAD}/{cid}", data=video.read_bytes(), headers={
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)})
    # 3. wait for processing
    for _ in range(60):
        s = call("GET", f"{GRAPH}/{cid}", {"fields": "status_code,status",
                                            "access_token": token})
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            sys.exit(f"Processing failed: {s}")
        time.sleep(5)
    else:
        sys.exit("Timed out waiting for Instagram to process the video.")
    # 4. publish
    p = call("POST", f"{GRAPH}/{uid}/media_publish",
             {"creation_id": cid, "access_token": token})
    m = call("GET", f"{GRAPH}/{p['id']}", {"fields": "permalink", "access_token": token})
    return m.get("permalink", p["id"])


def record(spec: dict, link: str, length: float) -> None:
    now = dt.datetime.now()
    caption = spec["captions"]["instagram"].splitlines()[0]
    with (ROOT / "log.md").open("a") as f:
        f.write(f"| {now:%Y-%m-%d} | {now:%H:%M} | Instagram | {spec['id']} | "
                f"{caption} | {spec.get('credit', '')} | {link} |\n")
    with (ROOT / "scoreboard.csv").open("a", newline="") as f:
        csv.writer(f).writerow([f"ig-{spec['id']}", f"{now:%Y-%m-%d}", f"{now:%H:%M}",
                                "instagram", spec.get("pillar", ""), "reel",
                                spec["hook"].replace("*", ""), f"{length:.1f}",
                                spec.get("credit", "")] + [""] * 9 + [""])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--confirm", action="store_true", help="actually post")
    ap.add_argument("--no-feed", action="store_true", help="Reels tab only")
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text())
    video = ROOT / "media" / "edits" / f"{spec['id']}.mp4"
    if not video.exists():
        sys.exit(f"Render it first: python3 tools/make_clip.py {a.spec}")
    caption = spec["captions"]["instagram"]
    length = sum(s["end"] - s["start"] for s in spec["segments"])
    cover_ms = int(spec.get("cover_at", 1.0) * 1000)
    print(f"Clip:    {video} ({length:.1f}s)\nCover:   {cover_ms} ms\n"
          f"Caption:\n{caption}\n")
    if not a.confirm:
        print("Dry run. Re-run with --confirm to post.")
        return
    load_env()
    for k in ("IG_USER_ID", "IG_ACCESS_TOKEN"):
        if not os.environ.get(k):
            sys.exit(f"Missing {k} (set it in .env).")
    link = publish(video, caption, cover_ms, not a.no_feed)
    record(spec, link, length)
    print(f"Posted: {link}")


if __name__ == "__main__":
    main()
