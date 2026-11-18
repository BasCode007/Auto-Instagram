#!/usr/bin/env python3
"""Render a vertical (1080x1920) short-form clip from a JSON spec.

Each spec in clips/*.json describes one post: which source video, which
segments to cut, the on-screen hook, timed labels (our commentary/captions),
the credit line, and the per-platform captions. This script turns that into
an upload-ready MP4 (H.264 + AAC, 30 fps, +faststart), a cover image, and a
captions text file in media/edits/.

Layouts
  fit  : blurred, darkened background + the shot cropped to 4:3 in the middle.
         Leaves clean space above and below for the hook and labels.
  full : full-bleed 9:16 crop. Set "x" per segment (0 = left edge,
         0.5 = centre, 1 = right edge) to keep the subject in frame.
  stack: streamer layout. Facecam on top ("facecam": [x, y, w, h] as
         fractions of the frame), gameplay below ("gx" = horizontal focus).

Captions: give "words": [[word, start, end], ...] in source seconds and the
clip gets big word-by-word captions with the spoken word highlighted
(profanity masked). tools/autoclip.py fills this in from Whisper.

Text is drawn with Pillow into transparent PNGs and overlaid by ffmpeg, so
there is no drawtext escaping to worry about. Wrap a word in *asterisks* in
the hook to colour it with the accent colour.

Usage
  python3 tools/make_clip.py clips/001-out-now.json
  python3 tools/make_clip.py clips/*.json --raw-dir /path/to/raw --preview
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
W, H = 1080, 1920
FPS = 30

# Phone safe area (1080x1920 canvas, checked against Instagram Reels, YouTube
# Shorts and TikTok on an iPhone): the app header covers the top ~14%, the
# caption/username block the bottom ~22%, the like/comment/share column the
# right ~130px, and tall iPhones can zoom-crop ~9% off each side. All text
# stays inside x 100..940, y 270..1480.
SAFE_LEFT, SAFE_RIGHT = 100, W - 140
HOOK_TOP = 270
SAFE_BOTTOM = 1480
FG_TOP = 500            # top of the 4:3 foreground in "fit" layout
FG_H = 810              # 1080 wide * 3/4
LABEL_TOP = FG_TOP + FG_H + 28
STACK_FACE_H = 700      # facecam band height in "stack" layout

ACCENT = (255, 79, 163)       # neon pink
ACCENT_2 = (255, 170, 60)     # sunset orange
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


# --------------------------------------------------------------------------
# Text rendering
# --------------------------------------------------------------------------
NBSP = " "


def _tokens(text: str):
    """Split 'GTA 6 IS *OUT NOW*.' into [(word, accent?)].

    Asterisks toggle the accent colour and may sit next to punctuation
    ('*Leonida*.'). 'GTA 6' is kept on one line.
    """
    text = re.sub(r"\bGTA 6\b", f"GTA{NBSP}6", text, flags=re.I)
    out, accent = [], False
    for raw in text.split(" "):
        if not raw:
            continue
        # a word can contain several runs: '*Gaming*,' -> [('Gaming',T),(',',F)]
        runs, buf = [], ""
        for ch in raw:
            if ch == "*":
                if buf:
                    runs.append((buf, accent))
                buf, accent = "", not accent
            else:
                buf += ch
        if buf:
            runs.append((buf, accent))
        out.append(runs)
    return out


def _plain(tok) -> str:
    return "".join(t for t, _ in tok)


def _draw_tokens(d, x, y, line, fnt, base, acc_col, **kw):
    for i, tok in enumerate(line):
        for j, (txt, acc) in enumerate(tok):
            piece = txt + (" " if (i < len(line) - 1 and j == len(tok) - 1) else "")
            d.text((x, y), piece, font=fnt, fill=acc_col if acc else base, **kw)
            x += d.textlength(piece, font=fnt)


def _wrap(tokens, fnt, max_w, draw):
    lines, cur = [], []
    for tok in tokens:
        trial = cur + [tok]
        width = draw.textlength(" ".join(_plain(t) for t in trial), font=fnt)
        if cur and width > max_w:
            lines.append(cur)
            cur = [tok]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def render_hook(text: str, path: Path, size: int = 84) -> int:
    """Big bold hook at the top. Returns the bottom y of the text block."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    max_w = SAFE_RIGHT - SAFE_LEFT
    fnt = font("InterDisplay-Black.otf", size)
    lines = _wrap(_tokens(text.upper()), fnt, max_w, d)
    while len(lines) > 3 and size > 56:          # shrink long hooks
        size -= 6
        fnt = font("InterDisplay-Black.otf", size)
        lines = _wrap(_tokens(text.upper()), fnt, max_w, d)
    line_h = int(size * 1.12)
    y = HOOK_TOP
    stroke = max(6, size // 11)
    for line in lines:
        full = " ".join(_plain(t) for t in line)
        x = SAFE_LEFT + (max_w - d.textlength(full, font=fnt)) / 2
        _draw_tokens(d, x, y, line, fnt, WHITE, ACCENT,
                     stroke_width=stroke, stroke_fill=BLACK)
        y += line_h
    # soft drop shadow for legibility on bright frames
    shadow = img.split()[3].filter(ImageFilter.GaussianBlur(10))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.putalpha(shadow.point(lambda a: int(a * 0.55)))
    base.alpha_composite(img)
    base.save(path)
    return y


def render_label(text: str, path: Path, top: int, size: int = 50,
                 color=WHITE) -> None:
    """Caption/label in a rounded dark pill, centred under the footage."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fnt = font("Inter-Bold.otf", size)
    max_w = SAFE_RIGHT - SAFE_LEFT - 60
    lines = _wrap(_tokens(text), fnt, max_w, d)
    line_h = int(size * 1.25)
    block_w = max(d.textlength(" ".join(_plain(t) for t in ln), font=fnt) for ln in lines)
    pad_x, pad_y = 30, 18
    box_w, box_h = block_w + pad_x * 2, line_h * len(lines) + pad_y * 2 - (line_h - size)
    bx = SAFE_LEFT + (SAFE_RIGHT - SAFE_LEFT - box_w) / 2
    d.rounded_rectangle([bx, top, bx + box_w, top + box_h], radius=22,
                        fill=(10, 8, 20, 205))
    y = top + pad_y - 4
    for ln in lines:
        full = " ".join(_plain(t) for t in ln)
        x = SAFE_LEFT + (SAFE_RIGHT - SAFE_LEFT - d.textlength(full, font=fnt)) / 2
        _draw_tokens(d, x, y, ln, fnt, color, ACCENT_2)
        y += line_h
    img.save(path)


def render_credit(text: str, path: Path, y: int) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fnt = font("Inter-SemiBold.otf", 30)
    x = SAFE_LEFT + 6
    d.text((x, y), text, font=fnt, fill=(255, 255, 255, 235),
           stroke_width=3, stroke_fill=(0, 0, 0, 200))
    img.save(path)


# --------------------------------------------------------------------------
# Video
# --------------------------------------------------------------------------
def probe_size(src: Path) -> tuple[int, int]:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(src)])
    w, h = out.decode().strip().split(",")[:2]
    return int(w), int(h)


def detect_letterbox(src: Path, sw: int, sh: int) -> int:
    """Height of the picture inside any black letterbox bars (even number).

    Samples a few points in the source with cropdetect and keeps the tallest
    result, so a dark shot can't trick it into over-cropping.
    """
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(src)]).decode().strip())
    best = 0
    for frac in (0.3, 0.45, 0.6):
        r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{dur * frac:.2f}", "-i",
                            str(src), "-t", "2", "-vf", "cropdetect=24:2:0",
                            "-an", "-f", "null", "-"], capture_output=True, text=True)
        found = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr)
        if found:
            best = max(best, int(found[-1][1]))
    if best < sh * 0.6:      # nothing sensible found: assume full frame
        return sh
    return best // 2 * 2


def auto_x(src: Path, start: float, end: float, sw: int, sh: int, y_off: int,
           cw: int) -> float:
    """Horizontal crop position that keeps the subject in a 9:16 crop.

    Trailer and cinematic shots use shallow focus, so the sharpest region
    (highest edge energy) is the subject. Sample a few frames, build a column
    profile of edge energy with a mild centre prior, and centre the crop on
    it. Returns 0..1 like a manual "x"."""
    small_w = 320
    small_h = int(sh * small_w / sw) // 2 * 2
    n = 5
    dur = max(0.2, end - start)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start + dur * 0.1:.3f}", "-t", f"{dur * 0.8:.3f}",
         "-i", str(src), "-vf",
         f"crop={sw}:{sh}:0:{y_off},fps={n / (dur * 0.8):.4f},scale={small_w}:{small_h},format=gray",
         "-frames:v", str(n), "-f", "rawvideo", "-"], capture_output=True).stdout
    px = np.frombuffer(raw, np.uint8)
    k = len(px) // (small_w * small_h)
    if k == 0:
        return 0.5
    f = px[: k * small_w * small_h].reshape(k, small_h, small_w).astype(np.float32)
    gx = np.abs(np.diff(f, axis=2))[:, :, :-1]
    gy = np.abs(np.diff(f, axis=1))[:, :-1, :]
    col = (gx[:, : gy.shape[1], : gy.shape[2]] + gy[:, :, : gx.shape[2]]).sum(axis=(0, 1))
    xs = np.linspace(-1, 1, col.size)
    col = col * (1.0 - 0.35 * xs ** 2)               # gentle centre prior
    win = max(1, int(col.size * cw / sw))
    run = np.convolve(col, np.ones(win), mode="valid")
    best = int(run.argmax())
    room = col.size - win
    return float(best / room) if room > 0 else 0.5


def segment_filter(i: int, seg: dict, layout: str, sw: int, sh: int,
                   y_off: int = 0, fps: int = FPS, spec: dict | None = None) -> str:
    """Filter chain for input i -> [v{i}] (1080x1920) and [a{i}].

    sh is the picture height inside the letterbox, y_off its top edge.
    """
    spec = spec or {}
    dur = seg["end"] - seg["start"]
    x = seg.get("x", spec.get("gx", 0.5))
    x = 0.5 if x == "auto" else float(x)
    zoom = float(seg.get("zoom", 1.0))
    if layout == "full":
        ch = int(sh / zoom) // 2 * 2
        cw = int(ch * 9 / 16) // 2 * 2
        cx = int((sw - cw) * x)
        cy = (sh - ch) // 2 + y_off
        v = (f"[{i}:v]crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:flags=lanczos,"
             f"setsar=1,fps={fps},format=yuv420p[v{i}]")
    elif layout == "stack":
        # facecam band on top, gameplay below (streamer clips)
        fh_band = int(spec.get("facecam_h", STACK_FACE_H))
        gh_band = H - fh_band
        fx, fy, fw, fhh = (float(v) for v in spec["facecam"])   # fractions of frame
        bx, by, bw, bh = int(fx * sw), int(fy * sh), int(fw * sw), int(fhh * sh)
        want = W / fh_band                      # band aspect
        if bw / bh > want:                      # box too wide: trim sides
            cw, chh = int(bh * want), bh
        else:                                   # box too tall: trim top/bottom
            cw, chh = bw, int(bw / want)
        cw, chh = cw // 2 * 2, chh // 2 * 2
        fcx = bx + (bw - cw) // 2
        fcy = by + (bh - chh) // 2
        # gameplay crop: full frame height, width to match the band aspect
        gzoom = float(spec.get("gzoom", zoom))
        gch = int(sh / gzoom) // 2 * 2
        gcw = min(sw, int(gch * W / gh_band) // 2 * 2)
        gcx = int((sw - gcw) * x)
        gcy = (sh - gch) // 2 + y_off
        v = (f"[{i}:v]split=2[fsrc{i}][gsrc{i}];"
             f"[fsrc{i}]crop={cw}:{chh}:{fcx}:{fcy + y_off},scale={W}:{fh_band}:"
             f"flags=lanczos,setsar=1[face{i}];"
             f"[gsrc{i}]crop={gcw}:{gch}:{gcx}:{gcy},scale={W}:{gh_band}:"
             f"flags=lanczos,setsar=1[game{i}];"
             f"[face{i}][game{i}]vstack=inputs=2,fps={fps},format=yuv420p[v{i}]")
    else:  # fit
        ch = int(sh / zoom) // 2 * 2
        cw = int(ch * 4 / 3) // 2 * 2
        cx = int((sw - cw) * x)
        cy = (sh - ch) // 2 + y_off
        v = (f"[{i}:v]split=2[bgsrc{i}][fgsrc{i}];"
             f"[bgsrc{i}]crop={sw}:{sh}:0:{y_off},scale=-2:{H // 4},crop={W // 4}:{H // 4},"
             f"boxblur=12:2,eq=brightness=-0.18:saturation=1.25,"
             f"scale={W}:{H}:flags=bicubic,setsar=1[bg{i}];"
             f"[fgsrc{i}]crop={cw}:{ch}:{cx}:{cy},scale={W}:{FG_H}:flags=lanczos,"
             f"setsar=1[fg{i}];"
             f"[bg{i}][fg{i}]overlay=0:{FG_TOP},fps={fps},format=yuv420p[v{i}]")
    fade = min(0.06, dur / 4)
    a = (f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
         f"afade=t=in:st=0:d={fade},afade=t=out:st={dur - fade:.3f}:d={fade}[a{i}]")
    return v + ";" + a


# --------------------------------------------------------------------------
# Word-by-word captions (ASS, burned in with libass)
# --------------------------------------------------------------------------
PROFANITY = {"fuck": "f*ck", "fucking": "f*cking", "fucked": "f*cked", "shit": "sh*t",
             "bitch": "b*tch", "motherfucker": "m*therf*cker", "fuckin": "f*ckin",
             "bullshit": "bullsh*t", "dick": "d*ck", "pussy": "p*ssy", "ass": "a*s"}


def _clean_word(w: str) -> str:
    w = w.replace("{", "").replace("}", "").replace("\\", "").strip()
    core = re.sub(r"[^a-z]", "", w.lower())
    if core in PROFANITY:
        w = re.sub(core, PROFANITY[core], w, flags=re.I)
    return w.upper()


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def map_words(spec: dict) -> list[tuple[str, float, float]]:
    """Words from spec['words'] ([word, start, end] in SOURCE seconds) mapped
    onto the clip timeline across all segments."""
    out, offset = [], 0.0
    for seg in spec["segments"]:
        for w, ws, we in spec.get("words", []):
            if ws >= seg["start"] - 0.05 and ws < seg["end"]:
                out.append((w, max(0, ws - seg["start"]) + offset,
                            min(we, seg["end"]) - seg["start"] + offset))
        offset += seg["end"] - seg["start"]
    return out


def write_ass(words, path: Path, y: int, size: int = 80,
              max_words: int = 3, max_chars: int = 16) -> None:
    """Chunks of up to 3 words, centred; the word being spoken is highlighted."""
    chunks, cur = [], []
    for w in words:
        txt = _clean_word(w[0])
        if not txt:
            continue
        gap = cur and (w[1] - cur[-1][2] > 0.7)
        too_long = cur and len(" ".join(c[0] for c in cur + [(txt,)])) > max_chars
        ends_sentence = cur and cur[-1][0][-1:] in ".?!"
        if cur and (len(cur) >= max_words or gap or too_long or ends_sentence):
            chunks.append(cur)
            cur = []
        cur.append((txt, w[1], w[2]))
    if cur:
        chunks.append(cur)
    hi = "&H000AD6FF&"   # ASS colours are &HAABBGGRR -> #FFD60A (yellow)
    lines = []
    for ci, ch in enumerate(chunks):
        nxt_start = chunks[ci + 1][0][1] if ci + 1 < len(chunks) else ch[-1][2] + 0.4
        for wi, (txt, ws, we) in enumerate(ch):
            end = ch[wi + 1][1] if wi + 1 < len(ch) else min(we + 0.35, nxt_start)
            parts = []
            for wj, (t2, _, _) in enumerate(ch):
                parts.append(f"{{\\c{hi}}}{t2}{{\\c&H00FFFFFF&}}" if wj == wi else t2)
            pop = "{\\fscx108\\fscy108\\t(0,90,\\fscx100\\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{_ass_time(ws)},{_ass_time(max(end, ws + 0.08))},"
                         f"Cap,,0,0,0,,{{\\pos({W // 2},{y})}}{pop}{' '.join(parts)}")
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display Black,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,7,3,5,{SAFE_LEFT},{W - SAFE_RIGHT},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    path.write_text(head + "\n".join(lines) + "\n")


# Output profiles. "social" = Instagram Reels / TikTok (1080x1920). "youtube" =
# YouTube Shorts master: 1440x2560 so YouTube serves its higher-quality VP9
# encode, with a slower, higher-bitrate x264 encode. Takes longer; looks better.
PROFILES = {
    "social": {"size": None, "crf": "20", "preset": None, "maxrate": None, "abr": "192k",
               "suffix": ""},
    "youtube": {"size": (1440, 2560), "crf": "16", "preset": "slow", "maxrate": "40M",
                "abr": "320k", "suffix": "_yt"},
}


def build(spec_path: Path, raw_dir: Path, out_dir: Path, preview: bool,
          profile: str = "social") -> Path:
    spec = json.loads(spec_path.read_text())
    clip_id = spec["id"]
    src = Path(spec["source"]) if Path(spec["source"]).is_absolute() else raw_dir / spec["source"]
    if not src.exists():
        sys.exit(f"[{clip_id}] missing source {src}. Download it first "
                 f"(see media/raw/SOURCES.md).")
    sw, full_h = probe_size(src)
    sh = spec.get("content_height") or (full_h if spec.get("no_letterbox")
                                         else detect_letterbox(src, sw, full_h))
    y_off = (full_h - sh) // 2
    layout = spec.get("layout", "fit")
    fps = int(spec.get("fps", FPS))
    segs = spec["segments"]
    total = sum(s["end"] - s["start"] for s in segs)
    face_h = int(spec.get("facecam_h", STACK_FACE_H))

    tmp = Path(tempfile.mkdtemp(prefix=f"clip_{clip_id}_"))
    try:
        overlays = []  # (png, start, end)
        hook_end = spec.get("hook_until", 3.5 if layout == "stack" else total)
        if spec.get("hook"):
            render_hook(spec["hook"], tmp / "hook.png", spec.get("hook_size", 84))
            overlays.append((tmp / "hook.png", 0, hook_end))
        if spec.get("credit"):
            cy = {"fit": FG_TOP + FG_H - 50, "stack": face_h - 52}.get(layout, SAFE_BOTTOM - 40)
            render_credit(spec["credit"], tmp / "credit.png", cy)
            overlays.append((tmp / "credit.png", 0, total))
        label_top = {"fit": LABEL_TOP, "stack": face_h + 40}.get(layout, 1180)
        for n, lab in enumerate(spec.get("labels", [])):
            p = tmp / f"label{n}.png"
            render_label(lab["text"], p, lab.get("top", label_top), lab.get("size", 50))
            overlays.append((p, lab["start"], lab["end"]))

        cmd = ["ffmpeg", "-v", "error", "-y"]
        for s in segs:
            cmd += ["-ss", f"{s['start']:.3f}", "-t", f"{s['end'] - s['start']:.3f}",
                    "-i", str(src)]
        first_png = len(segs)
        for png, _, _ in overlays:
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{total:.3f}",
                    "-i", str(png)]

        if layout == "full":
            cw = int(sh * 9 / 16)
            for sg in segs:
                if sg.get("x", spec.get("gx", "auto")) == "auto":
                    sg["x"] = round(auto_x(src, sg["start"], sg["end"], sw, sh, y_off, cw), 3)
            print(f"[{clip_id}] framing: " + ", ".join(
                str(sg.get("x", spec.get("gx", 0.5))) for sg in segs))
        parts = [segment_filter(i, s, layout, sw, sh, y_off, fps, spec)
                 for i, s in enumerate(segs)]
        concat_in = "".join(f"[v{i}][a{i}]" for i in range(len(segs)))
        parts.append(f"{concat_in}concat=n={len(segs)}:v=1:a=1[vc][ac]")
        last = "vc"
        for k, (_, st, en) in enumerate(overlays):
            nxt = f"o{k}"
            parts.append(f"[{last}][{first_png + k}:v]overlay=0:0:"
                         f"enable='between(t,{st},{en})':shortest=1[{nxt}]")
            last = nxt
        words = map_words(spec) if spec.get("words") else []
        if words:
            cap_y = spec.get("caption_y") or {"stack": face_h + 190, "fit": 1440}.get(layout, 1200)
            ass = tmp / "captions.ass"
            write_ass(words, ass, int(cap_y), int(spec.get("caption_size", 80)))
            parts.append(f"[{last}]subtitles=filename={ass}:fontsdir={FONTS}[subs]")
            last = "subs"
        prof = PROFILES[profile]
        if prof["size"]:
            pw, ph = prof["size"]
            parts.append(f"[{last}]scale={pw}:{ph}:flags=lanczos,"
                         f"unsharp=5:5:0.35:5:5:0.0[up]")
            last = "up"
        # gentle loudness normalisation so clips sit at a consistent level
        parts.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{clip_id}{prof['suffix']}.mp4"
        preset = "veryfast" if preview else (prof["preset"] or spec.get("preset", "slow"))
        maxrate = prof["maxrate"] or ("16M" if fps > 30 else "12M")
        cmd += ["-filter_complex", ";".join(parts), "-map", f"[{last}]",
                "-map", "[aout]", "-t", f"{total:.3f}",
                "-c:v", "libx264", "-profile:v", "high", "-preset", preset,
                "-crf", prof["crf"], "-maxrate", maxrate, "-bufsize", "64M",
                "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", prof["abr"],
                "-ar", "48000", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)

        if profile == "social":
            # Cover frame (Reels/TikTok cover): frame at cover_at seconds
            cover_at = spec.get("cover_at", min(1.0, total / 2))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(cover_at), "-i",
                            str(out), "-frames:v", "1", "-q:v", "2",
                            str(out_dir / f"{clip_id}_cover.jpg")], check=True)
            write_captions(spec, out_dir / f"{clip_id}_captions.txt", total)
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def write_captions(spec: dict, path: Path, total: float) -> None:
    c = spec.get("captions", {})
    lines = [f"CLIP {spec['id']}  |  {total:.1f}s  |  pillar: {spec.get('pillar', '')}",
             f"Source: {spec.get('source_url', spec['source'])}", ""]
    for platform in ("instagram", "tiktok", "youtube_shorts", "x"):
        if platform in c:
            lines += [f"===== {platform.upper()} =====", c[platform].strip(), ""]
    if spec.get("notes"):
        lines += ["===== NOTES =====", spec["notes"].strip(), ""]
    path.write_text("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="+", type=Path)
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "media" / "raw")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "media" / "edits")
    ap.add_argument("--preview", action="store_true", help="fast encode for checking")
    ap.add_argument("--profile", choices=list(PROFILES), default="social",
                    help="social = 1080x1920 for Reels/TikTok; youtube = 1440x2560 Shorts master")
    a = ap.parse_args()
    for s in a.specs:
        out = build(s, a.raw_dir, a.out_dir, a.preview, a.profile)
        print(f"rendered {out}")


if __name__ == "__main__":
    main()
