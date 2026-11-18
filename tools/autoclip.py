#!/usr/bin/env python3
"""Long video / live stream -> short-form clips.

  scan   Pull the AUDIO of a VOD, live broadcast or long video (small, fast),
         transcribe it, and score every moment by reaction energy (loudness
         spikes), excited speech and laughter. Writes a ranked shortlist to
         media/raw/<source>/candidates.md, skipping anything already clipped.

  cut    Download only the chosen section at full quality (1080p60), check
         the no-repeat registry, transcribe it accurately for word-by-word
         captions, write clips/<id>.json and render the vertical clip.

Examples
  # score the last 40 minutes of a live Twitch broadcast
  python3 tools/autoclip.py scan https://www.twitch.tv/videos/2932194507 --last 40 \\
      --creator lacy

  # cut a moment (source seconds), streamer layout with facecam on top
  python3 tools/autoclip.py cut twitch-2932194507 --start 7212 --end 7241 \\
      --hook "LACY FOUND *THE MAP SIZE*" --facecam 0,0,0.258,0.256

Sources: anything yt-dlp supports. Twitch VODs (including the VOD of a
broadcast that's still live), Kick, YouTube (YouTube blocks downloads from
cloud servers; run this on your own computer for YouTube, or drop the file in
media/raw/<id>/ and use `scan --file`).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_clip  # noqa: E402
import registry  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "media" / "raw"
CLIPS = ROOT / "clips"
SR = 16000

HYPE = ["oh my god", "no way", "what the", "holy", "bro", "dude", "yo ", "insane",
        "crazy", "look at", "wait", "are you kidding", "let's go", "lets go",
        "oh no", "run", "why", "this game", "unreal", "beautiful", "huge", "massive",
        "chat", "help", "stop", "what is that", "is that", "rockstar", "gta"]
LAUGH = ["haha", "hahaha", "lmao", "lol", "laugh"]
# Moments with sexual content/nudity are never clipped (playbook: skip nudity).
NSFW = ["dick", "cock", "jerk", "naked", "nude", "tits", "titties", "yiddies", "boob",
        "penis", "strip club", "stripper", " sex", "porn", "nipple", "vibrator",
        "topless", "horny", "onlyfans"]
NSFW_RADIUS = 60.0   # nudity scenes run longer than the word that flags them


# --------------------------------------------------------------------------
def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("timeout", 1800)
    return subprocess.run(cmd, check=True, **kw)


def ytdlp_info(url: str) -> dict:
    out = subprocess.run(["yt-dlp", "--js-runtimes", "node", "-J", "--no-warnings", url],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"yt-dlp couldn't read {url}:\n{out.stderr.strip()[-600:]}")
    return json.loads(out.stdout)


def source_id_for(info: dict) -> str:
    plat = (info.get("extractor_key") or "src").lower().replace("vod", "")
    vid = re.sub(r"[^A-Za-z0-9_-]", "", str(info.get("id", "x"))).lstrip("v")
    return f"{plat}-{vid}"


def src_dir(source_id: str) -> Path:
    return RAW / source_id


def load_source(source_id: str) -> dict:
    p = src_dir(source_id) / "source.json"
    if not p.exists():
        sys.exit(f"Unknown source {source_id}; run scan first.")
    return json.loads(p.read_text())


def decode(path: Path, start: float = 0, dur: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    pcm = sh(cmd, capture_output=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def hls_range(url: str, fmt_sel: str, start: float, end: float, out: Path) -> float:
    """Download only the HLS segments covering [start, end] of a VOD.

    Works on broadcasts that are still live (ffmpeg's own HLS reader can hang
    on those). Returns the offset of `start` inside the written file, so cuts
    stay frame-accurate without re-encoding.
    """
    import concurrent.futures as cf
    import urllib.request
    m3u8 = subprocess.run(["yt-dlp", "--js-runtimes", "node", "--no-warnings", "-g",
                           "-f", fmt_sel, url], capture_output=True, text=True,
                          timeout=120).stdout.split()
    if not m3u8:
        raise RuntimeError(f"no stream URL for format {fmt_sel}")
    text = urllib.request.urlopen(m3u8[0], timeout=30).read().decode()
    if "#EXTINF" not in text:
        raise RuntimeError("not a media playlist")
    base = m3u8[0].rsplit("/", 1)[0] + "/"
    init, segs, t, dur = None, [], 0.0, None
    for ln in text.splitlines():
        if ln.startswith("#EXT-X-MAP:"):
            init = re.search(r'URI="([^"]+)"', ln).group(1)
        elif ln.startswith("#EXTINF:"):
            dur = float(ln[8:].split(",")[0])
        elif ln and not ln.startswith("#") and dur is not None:
            segs.append((t, t + dur, ln))
            t, dur = t + dur, None
    sel = [x for x in segs if x[1] > start and x[0] < end]
    if not sel:
        raise RuntimeError(f"range {start}-{end} not in playlist (length {t:.0f}s)")

    def get(uri: str) -> bytes:
        full = uri if uri.startswith("http") else base + uri
        for attempt in range(4):
            try:
                return urllib.request.urlopen(full, timeout=60).read()
            except Exception:
                if attempt == 3:
                    raise
        return b""
    with cf.ThreadPoolExecutor(8) as ex:
        blobs = list(ex.map(get, [x[2] for x in sel]))
    raw = out.with_suffix(".raw" + out.suffix)
    with raw.open("wb") as f:
        if init:
            f.write(get(init))
        for b in blobs:
            f.write(b)
    # remux (no re-encode) so every tool reads it as a normal file
    sh(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c", "copy", str(out)])
    raw.unlink(missing_ok=True)
    return start - sel[0][0]


def fetch_range(url: str, fmts: list[str], start: float, end: float, out: Path) -> float:
    """HLS segment fetch first (Twitch/Kick), yt-dlp section download as fallback."""
    for f in fmts:
        try:
            return hls_range(url, f, start, end, out)
        except Exception as e:  # noqa: BLE001
            last = e
    print(f"  segment fetch failed ({last}); falling back to yt-dlp")
    sh(["yt-dlp", "--js-runtimes", "node", "--no-warnings", "-q", "-f",
        "/".join(fmts) + "/best", "--download-sections", f"*{start}-{end}",
        "--force-keyframes-at-cuts", "-o", str(out), url], timeout=900)
    return 0.0


_models: dict = {}


def transcribe(audio: np.ndarray, model: str) -> list[tuple[str, float, float]]:
    from faster_whisper import WhisperModel
    if model not in _models:
        _models[model] = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = _models[model].transcribe(audio, word_timestamps=True, vad_filter=True,
                                        language="en", beam_size=1 if "tiny" in model
                                        or "base" in model else 5)
    return [(w.word.strip(), float(w.start), float(w.end)) for s in segs for w in s.words]


# --------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------
def energy_curve(audio: np.ndarray, hop: float = 0.5) -> np.ndarray:
    n = int(SR * hop)
    frames = audio[: len(audio) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-6)
    # spike = how far above the local (60 s) median the loudness is
    k = int(60 / hop)
    pad = np.pad(db, (k // 2, k // 2), mode="edge")
    med = np.array([np.median(pad[i:i + k]) for i in range(len(db))])
    return np.clip(db - med, 0, None)


def score_windows(words, spikes, t0: float, length: float, hop: float = 0.5,
                  step: float = 2.0, skip: list[tuple[float, float]] = ()):
    dur = len(spikes) * hop
    out = []
    t = 0.0
    lower = [(w.lower(), s) for w, s, _ in words]
    # whole neighbourhoods around sexual-content words are off limits
    flagged = [s for w, s in lower if any(k.strip() in w for k in NSFW)]
    skip = list(skip) + [(f - NSFW_RADIUS, f + NSFW_RADIUS) for f in flagged]
    while t + length <= dur:
        a, b = t + t0, t + t0 + length
        if any(a < e and b > s for s, e in skip):
            t += step
            continue
        sp = spikes[int(t / hop): int((t + length) / hop)]
        energy = float(np.sort(sp)[-6:].sum())            # strongest moments
        ws = [w for w, s in lower if a <= s < b]
        text = " ".join(ws)
        hype = sum(text.count(k) for k in HYPE)
        laugh = sum(text.count(k) for k in LAUGH)
        excl = text.count("!") + text.count("?")
        speech = min(len(ws) / (length * 2.2), 1.0)       # ~2.2 words/s = talky
        score = energy * 1.0 + hype * 2.5 + laugh * 3 + excl * 0.8 + speech * 6
        if any(k in f" {text}" for k in NSFW):
            t += step
            continue
        out.append((score, a, b))
        t += step
    out.sort(reverse=True)
    picked = []
    for sc, a, b in out:
        if all(b <= pa or a >= pb for _, pa, pb in picked):
            picked.append((sc, a, b))
    return picked


def snap(words, a: float, b: float, lead: float = 0.6, tail: float = 0.8):
    """Move edges to word boundaries so clips don't start/end mid-word."""
    starts = [s for _, s, _ in words if a - 3 <= s <= a + 3]
    ends = [e for _, _, e in words if b - 3 <= e <= b + 3]
    if starts:
        a = min(starts, key=lambda s: abs(s - a)) - lead
    if ends:
        b = min(ends, key=lambda e: abs(e - b)) + tail
    return max(0.0, a), b


def fmt(t: float) -> str:
    h, r = divmod(int(t), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}"


def cmd_scan(a) -> None:
    if a.file:
        f = Path(a.file).resolve()
        info = {"id": f.stem, "extractor_key": "file", "title": f.stem,
                "uploader": a.creator or "", "webpage_url": str(f),
                "duration": float(subprocess.check_output(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(f)]).decode())}
    else:
        info = ytdlp_info(a.url)
    sid = source_id_for(info)
    d = src_dir(sid)
    d.mkdir(parents=True, exist_ok=True)
    dur = float(info.get("duration") or 0)
    start = a.start if a.start is not None else max(0.0, dur - a.last * 60) if a.last else 0.0
    end = a.end if a.end is not None else dur
    prev = json.loads((d / "source.json").read_text()) if (d / "source.json").exists() else {}
    if a.new and prev.get("scanned_to"):
        start = max(0.0, prev["scanned_to"] - 20)       # small overlap
    if end - start < 60:
        sys.exit(f"[{sid}] nothing new to scan yet ({end - start:.0f}s since last scan)")
    meta = {"source_id": sid, "url": info.get("webpage_url") or a.url,
            "title": info.get("title"), "channel": info.get("uploader") or info.get("channel"),
            "creator": a.creator or info.get("uploader_id") or info.get("uploader"),
            "platform": info.get("extractor_key"), "duration_at_scan": dur,
            "file": a.file, "scanned_to": max(end, prev.get("scanned_to", 0))}
    (d / "source.json").write_text(json.dumps(meta, indent=2))
    print(f"[{sid}] {meta['title']}\n  scanning {fmt(start)} - {fmt(end)}")

    audio_path = d / f"audio_{int(start)}_{int(end)}.mp4"
    if a.file:
        audio_path = Path(a.file)
        audio = decode(audio_path, start, end - start)
    else:
        off = fetch_range(meta["url"], ["Audio_Only", "160p", "160p30", "worstaudio", "worst"],
                          start, end, audio_path)
        audio = decode(audio_path, off, end - start)
    spikes = energy_curve(audio)
    print(f"  transcribing {len(audio) / SR / 60:.1f} min with {a.model} ...")
    words = [(w, s + start, e + start) for w, s, e in transcribe(audio, a.model)]
    tpath = d / "transcript_scan.json"
    old = json.loads(tpath.read_text()) if tpath.exists() else []
    old = [w for w in old if not (start <= w[1] < end)]
    tpath.write_text(json.dumps(sorted(old + words, key=lambda w: w[1])))

    used = registry.used_ranges(sid)
    rows = []
    for kind, length in (("reel", a.reel_len), ("short", a.short_len)):
        for sc, s0, e0 in score_windows(words, spikes, start, length, skip=used)[: a.top]:
            s1, e1 = snap(words, s0, e0)
            text = " ".join(w for w, ws, _ in words if s1 <= ws < e1)
            rows.append({"kind": kind, "score": round(sc, 1), "start": round(s1, 2),
                         "end": round(e1, 2), "text": text})
    (d / "candidates.json").write_text(json.dumps(rows, indent=2))
    (d / f"candidates_{int(start)}_{int(end)}.json").write_text(json.dumps(rows, indent=2))
    link = meta["url"]
    md = [f"# Candidates: {meta['title']}", f"Source: {link}  ·  creator: {meta['creator']}",
          f"Scanned {fmt(start)}-{fmt(end)}. Already-used ranges are excluded.", ""]
    for i, r in enumerate(rows, 1):
        ts = f"{link}?t={int(r['start']) // 3600}h{int(r['start']) % 3600 // 60}m{int(r['start']) % 60}s" \
            if "twitch" in link else link
        md += [f"## {i}. {r['kind']} · score {r['score']} · {fmt(r['start'])}-{fmt(r['end'])} "
               f"({r['end'] - r['start']:.0f}s)", f"[open at timestamp]({ts})", "",
               f"> {r['text'][:700]}", "",
               f"`python3 tools/autoclip.py cut {sid} --start {r['start']} --end {r['end']} "
               f"--hook \"...\"`", ""]
    (d / "candidates.md").write_text("\n".join(md))
    print(f"  {len(rows)} candidates -> {d / 'candidates.md'}")
    if a.thumbs:
        thumbs(sid, meta, rows)


def thumbs(sid: str, meta: dict, rows: list[dict]) -> None:
    """Low-res frame strips for each candidate so a human can eyeball them."""
    d = src_dir(sid) / "thumbs"
    d.mkdir(exist_ok=True)
    for i, r in enumerate(rows, 1):
        low = d / f"c{i}.mp4"
        if not meta.get("file"):
            ss = fetch_range(meta["url"], ["360p", "360p30", "480p", "worst"],
                             r["start"], r["end"], low)
            srcf = low
        else:
            srcf, ss = Path(meta["file"]), r["start"]
        n = 8
        step = (r["end"] - r["start"]) / n
        sh(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", str(r["end"] - r["start"]),
            "-i", str(srcf), "-vf", f"fps=1/{step:.2f},scale=320:-2,tile={n}x1",
            "-frames:v", "1", str(d / f"c{i}.jpg")])
        low.unlink(missing_ok=True)
    print(f"  thumbnails -> {d}")


# --------------------------------------------------------------------------
# cut
# --------------------------------------------------------------------------
KEEP_CAPS = {"GTA", "NPC", "NPCS", "PS5", "FPS", "AI", "USA", "UK", "NZ", "OG", "VI"}


def sentence_case(text: str) -> str:
    """'GTA 6 HAS COLLECTIBLE CARDS' -> 'GTA 6 has collectible cards'."""
    out = []
    for i, w in enumerate(text.split()):
        core = re.sub(r"[^A-Za-z0-9]", "", w).upper()
        if core in KEEP_CAPS or core.startswith("GTA"):
            out.append(w)
        else:
            out.append(w.capitalize() if i == 0 else w.lower())
    res = " ".join(out)
    for name in PROPER:
        res = re.sub(rf"\b{re.escape(name)}\b", name, res, flags=re.I)
    return res


# names that keep their capitals in sentence-case captions (longest first)
PROPER = sorted([
    "Jason", "Lucia", "Dolores", "Brian", "Cal", "Boobie", "Dre'Quan", "Raul", "Lori",
    "Leonida", "Vice City", "Vice-Dale County", "Mariana County", "Kelly County",
    "Leonard County", "Leonida Keys", "Grassrivers", "Port Gellhorn", "Ambrosia",
    "Mount Kalaga", "Ammu-Nation", "Hamlet Pawn", "Ratface", "Rockstar", "Los Santos",
    "Weazel News", "xQc", "Lacy", "TheBurntPeanut", "Twitch", "YouTube", "TikTok",
], key=len, reverse=True)


def platform_captions(hook: str, creator: str, platform: str, line: str,
                      source_url: str = "") -> dict:
    h = hook.replace("*", "").strip()
    h_sent = sentence_case(h)
    tag = re.sub(r"[^A-Za-z0-9]", "", creator or "")
    where = f" on {platform}" if platform else ""
    credit = f"🎥 @{creator}{where}" if creator else ""
    body = f"\n\n{line}" if line else ""
    return {
        "instagram": f"{h_sent}{body}\n\n{credit}\n\n#GTA6 #GTAVI #GrandTheftAuto #ViceCity #{tag}",
        "tiktok": f"{h_sent} {credit} #GTA6 #GTAVI #gta6clips #{tag}",
        "youtube_shorts": f"{h_sent} #GTA6 #Shorts\n\n{credit}"
                          + (f"\nFull stream: {source_url}" if source_url else ""),
    }


def platform_name(extractor: str) -> str:
    e = extractor.lower()
    for key, name in (("twitch", "Twitch"), ("youtube", "YouTube"), ("kick", "Kick"),
                      ("tiktok", "TikTok"), ("instagram", "Instagram"), ("twitter", "X")):
        if key in e:
            return name
    return ""


def cmd_cut(a) -> None:
    meta = load_source(a.source_id)
    sid = a.source_id
    start, end = float(a.start), float(a.end)
    if end - start > 180:
        sys.exit("Shorts/Reels max out at 3 minutes; pick a shorter range.")
    d = src_dir(sid)
    sec = d / f"sec_{int(start * 10)}_{int(end * 10)}.mp4"
    off_file = sec.with_suffix(".offset")
    if not sec.exists():
        if meta.get("file"):
            sh(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(end - start),
                "-i", meta["file"], "-c", "copy", str(sec)])
            off = 0.0
        else:
            print(f"downloading {fmt(start)}-{fmt(end)} at full quality ...")
            off = fetch_range(meta["url"], ["1080p60", "1080p", "1440p60", "720p60",
                                            "bv*[height<=1080]+ba", "best"], start, end, sec)
        off_file.write_text(str(off))
    off = float(off_file.read_text()) if off_file.exists() else 0.0
    length = end - start

    # no-repeat check: same source + overlapping time, or same scene anywhere
    sw, shh = make_clip.probe_size(sec)
    game_crop = None
    if a.facecam:
        game_crop = f"crop={int(sw * 0.5)}:{int(shh * 0.6)}:{int(sw * 0.25)}:{int(shh * 0.3)}"
    hashes = registry.frame_hashes(sec, off, off + length, crop=game_crop)
    problems = registry.check(sid, start, end, hashes)
    if problems and not a.force:
        sys.exit("REPEAT, not cutting:\n  " + "\n  ".join(problems) +
                 "\n(--force only if you're sure it's different)")

    print("transcribing for captions ...")
    words = [[w, round(s + off, 2), round(e + off, 2)] for w, s, e in
             transcribe(decode(sec, off, length), a.model)] if not a.no_captions else []

    creator = (a.creator or meta.get("creator") or "").lstrip("@")
    clip_id = a.id or f"{sid.split('-')[0][:2]}-{creator or 'clip'}-{int(start)}".lower()
    clip_id = re.sub(r"[^a-z0-9_-]", "", clip_id.lower())
    plat = platform_name(meta.get("platform") or "")
    spec = {
        "id": clip_id, "pillar": a.pillar, "kind": a.kind,
        "source": str(sec.relative_to(RAW)), "source_url": meta["url"],
        "source_range": [start, end], "creator": creator,
        "hook": a.hook, "credit": f"@{creator}" + (f" on {plat}" if plat else "") if creator else "",
        "layout": "stack" if a.facecam else a.layout, "fps": a.fps,
        "no_letterbox": True, "preset": "medium",
        "segments": [{"start": round(off, 3), "end": round(off + length, 3)}],
        "words": words,
        "captions": platform_captions(a.hook, creator, plat, a.line or "", meta["url"]),
        "notes": f"Cut from {meta['url']} at {fmt(start)}-{fmt(end)}. "
                 "Credit is not permission: ask the creator if reachable; "
                 "take down same day on request.",
    }
    if a.facecam:
        spec["facecam"] = [float(v) for v in a.facecam.split(",")]
        spec["facecam_h"] = a.facecam_h
        spec["gzoom"] = a.gzoom
    if a.gx is not None:
        spec["gx"] = a.gx
    if a.labels:
        spec["labels"] = json.loads(a.labels)
    CLIPS.mkdir(exist_ok=True)
    spath = CLIPS / f"{clip_id}.json"
    spath.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    out = make_clip.build(spath, RAW, ROOT / "media" / "edits", a.preview)
    if not a.preview:
        registry.add(clip_id, sid, meta["url"], start, end, hashes, creator)
    print(f"rendered {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="score a long video/stream for clip moments")
    s.add_argument("url", nargs="?")
    s.add_argument("--file", help="local video instead of a URL")
    s.add_argument("--creator", help="handle to credit, without @")
    s.add_argument("--start", type=float)
    s.add_argument("--end", type=float)
    s.add_argument("--last", type=float, help="only the last N minutes (live streams)")
    s.add_argument("--new", action="store_true",
                   help="only what was streamed since the previous scan of this source")
    s.add_argument("--model", default="base.en", help="whisper model for scanning")
    s.add_argument("--reel-len", type=float, default=28)
    s.add_argument("--short-len", type=float, default=60)
    s.add_argument("--top", type=int, default=6)
    s.add_argument("--thumbs", action="store_true", help="frame strips per candidate")
    s.set_defaults(func=cmd_scan)

    c = sub.add_parser("cut", help="cut + render one clip")
    c.add_argument("source_id")
    c.add_argument("--start", required=True)
    c.add_argument("--end", required=True)
    c.add_argument("--hook", required=True, help="on-screen hook; *word* = accent colour")
    c.add_argument("--line", help="one sentence of value for the IG caption")
    c.add_argument("--id")
    c.add_argument("--creator")
    c.add_argument("--kind", default="reel", choices=["reel", "short"])
    c.add_argument("--pillar", default="gameplay clips")
    c.add_argument("--layout", default="fit", choices=["fit", "full", "stack"])
    c.add_argument("--facecam", help="x,y,w,h of the facecam as fractions of the frame")
    c.add_argument("--facecam-h", type=int, default=700)
    c.add_argument("--gx", type=float, help="gameplay horizontal focus 0..1")
    c.add_argument("--gzoom", type=float, default=1.08,
                   help="zoom gameplay slightly so overlays at the edges drop out")
    c.add_argument("--labels", help="JSON list of extra labels")
    c.add_argument("--fps", type=int, default=60)
    c.add_argument("--model", default="small.en", help="whisper model for captions")
    c.add_argument("--no-captions", action="store_true")
    c.add_argument("--preview", action="store_true")
    c.add_argument("--force", action="store_true", help="ignore the repeat check")
    c.set_defaults(func=cmd_cut)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
