#!/usr/bin/env python3
"""Find who is live on GTA 6 right now and how we can clip them.

Reads the Twitch "Grand Theft Auto VI" directory (sorted by viewers) with a
headless browser, then for each English-titled stream checks whether its
current broadcast VOD is public (scan it with `autoclip.py scan --new`) or
subscriber-only (record it live with `tools/record_live.sh`). Results are
merged into streamers.json, which also stores each streamer's facecam box
once it has been measured.

Usage
  python3 tools/discover_streams.py            # print + update streamers.json
  python3 tools/discover_streams.py --top 15
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "streamers.json"
DIRECTORY = "https://www.twitch.tv/directory/category/grand-theft-auto-vi?sort=VIEWER_COUNT"

JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36' });
  await p.goto(process.argv[2], { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(8000);
  const rows = await p.evaluate(() => [...document.querySelectorAll('a[data-a-target="preview-card-channel-link"]')]
     .map(a => ({ url: a.href, text: a.innerText.replace(/\n+/g, ' / ') })));
  console.log(JSON.stringify(rows));
  await b.close();
})();
"""


def live_channels() -> list[dict]:
    js = ROOT / ".discover.js"
    js.write_text(JS)
    try:
        npm_root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
        env = dict(subprocess.os.environ, NODE_PATH=npm_root)
        out = subprocess.run(["node", str(js), DIRECTORY], capture_output=True, text=True,
                             timeout=120, env=env)
        rows = json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else []
    finally:
        js.unlink(missing_ok=True)
    chans = []
    for r in rows:
        m = re.match(r"https://www\.twitch\.tv/([^/?#]+)", r["url"])
        if m:
            chans.append({"channel": m.group(1).lower(), "title": r["text"].split(" / ")[0]})
    return chans


def looks_english(title: str) -> bool:
    if re.search(r"[Ѐ-ӿ؀-ۿ぀-ヿ一-鿿]", title):
        return False
    non_en = ["jogando", "directo", "stunden", "neuseeland", "aus ", "ao vivo", "en vivo",
              "drops aktiv", "verlosung", "codigo", "giornata", "maratona", "interdit",
              "tage", "spielt", "geiler", "dia ", "le jeu", "heures", "jeu ", "spiel", "deutsch",
              "español", "francais", "français", "partida", "juego", "jugando", "neuer", "mit "]
    t = title.lower()
    return not any(w in t for w in non_en)


def vod_access(channel: str) -> tuple[str, str | None]:
    """('public', vod_id) | ('sub-only', vod_id) | ('none', None)"""
    out = subprocess.run(["yt-dlp", "--flat-playlist", "--playlist-end", "1", "--print", "%(id)s",
                          f"https://www.twitch.tv/{channel}/videos?filter=archives&sort=time"],
                         capture_output=True, text=True, timeout=90)
    vid = out.stdout.strip().splitlines()[0] if out.stdout.strip() else None
    if not vid:
        return "none", None
    vid = vid.lstrip("v")
    chk = subprocess.run(["yt-dlp", "--no-warnings", "-F", f"https://www.twitch.tv/videos/{vid}"],
                         capture_output=True, text=True, timeout=90)
    if "subscriber-only" in chk.stderr or "logged into an account" in chk.stderr:
        return "sub-only", vid
    return ("public", vid) if chk.returncode == 0 else ("none", vid)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--all-languages", action="store_true")
    a = ap.parse_args()
    db = json.loads(DB.read_text()) if DB.exists() else {}
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    for e in db.values():
        e["live"] = False
    for c in live_channels()[: a.top * 2]:
        if not a.all_languages and not looks_english(c["title"]):
            continue
        e = db.setdefault(c["channel"], {"facecam": None, "priority": "normal"})
        access, vid = vod_access(c["channel"])
        e.update({"live": True, "title": c["title"], "vod_access": access, "vod_id": vid,
                  "seen": now})
        if sum(1 for x in db.values() if x.get("live")) >= a.top:
            break
    DB.write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n")
    print(f"{'channel':<18} {'access':<9} {'vod':<12} facecam  title")
    for ch, e in sorted(db.items(), key=lambda kv: not kv[1].get("live")):
        if e.get("live"):
            fc = "set" if e.get("facecam") else "MEASURE"
            print(f"{ch:<18} {e['vod_access']:<9} {str(e['vod_id']):<12} {fc:<8} {e['title'][:60]}")


if __name__ == "__main__":
    main()
