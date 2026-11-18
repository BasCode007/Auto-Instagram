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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
W, H = 1080, 1920
FPS = 30

# Safe area: Reels/TikTok UI covers roughly the top 220px, the bottom ~420px
# and a ~130px column on the right. Keep all text inside this box.
SAFE_LEFT, SAFE_RIGHT = 60, W - 130
HOOK_TOP = 250
FG_TOP = 540            # top of the 4:3 foreground in "fit" layout
FG_H = 810              # 1080 wide * 3/4
LABEL_TOP = FG_TOP + FG_H + 28

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


def segment_filter(i: int, seg: dict, layout: str, sw: int, sh: int,
                   y_off: int = 0) -> str:
    """Filter chain for input i -> [v{i}] (1080x1920) and [a{i}].

    sh is the picture height inside the letterbox, y_off its top edge.
    """
    dur = seg["end"] - seg["start"]
    x = float(seg.get("x", 0.5))
    zoom = float(seg.get("zoom", 1.0))
    if layout == "full":
        ch = int(sh / zoom) // 2 * 2
        cw = int(ch * 9 / 16) // 2 * 2
        cx = int((sw - cw) * x)
        cy = (sh - ch) // 2 + y_off
        v = (f"[{i}:v]crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:flags=lanczos,"
             f"setsar=1,fps={FPS},format=yuv420p[v{i}]")
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
             f"[bg{i}][fg{i}]overlay=0:{FG_TOP},fps={FPS},format=yuv420p[v{i}]")
    fade = min(0.06, dur / 4)
    a = (f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
         f"afade=t=in:st=0:d={fade},afade=t=out:st={dur - fade:.3f}:d={fade}[a{i}]")
    return v + ";" + a


def build(spec_path: Path, raw_dir: Path, out_dir: Path, preview: bool) -> Path:
    spec = json.loads(spec_path.read_text())
    clip_id = spec["id"]
    src = raw_dir / spec["source"]
    if not src.exists():
        sys.exit(f"[{clip_id}] missing source {src}. Download it first "
                 f"(see media/raw/SOURCES.md).")
    sw, full_h = probe_size(src)
    sh = spec.get("content_height") or detect_letterbox(src, sw, full_h)
    y_off = (full_h - sh) // 2
    layout = spec.get("layout", "fit")
    segs = spec["segments"]
    total = sum(s["end"] - s["start"] for s in segs)

    tmp = Path(tempfile.mkdtemp(prefix=f"clip_{clip_id}_"))
    try:
        overlays = []  # (png, start, end)
        hook_end = spec.get("hook_until", total)
        render_hook(spec["hook"], tmp / "hook.png", spec.get("hook_size", 84))
        overlays.append((tmp / "hook.png", 0, hook_end))
        if spec.get("credit"):
            cy = FG_TOP + FG_H - 50 if layout == "fit" else H - 470
            render_credit(spec["credit"], tmp / "credit.png", cy)
            overlays.append((tmp / "credit.png", 0, total))
        for n, lab in enumerate(spec.get("labels", [])):
            p = tmp / f"label{n}.png"
            top = lab.get("top", LABEL_TOP if layout == "fit" else 1280)
            render_label(lab["text"], p, top, lab.get("size", 50))
            overlays.append((p, lab["start"], lab["end"]))

        cmd = ["ffmpeg", "-v", "error", "-y"]
        for s in segs:
            cmd += ["-ss", f"{s['start']:.3f}", "-t", f"{s['end'] - s['start']:.3f}",
                    "-i", str(src)]
        first_png = len(segs)
        for png, _, _ in overlays:
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}",
                    "-i", str(png)]

        parts = [segment_filter(i, s, layout, sw, sh, y_off) for i, s in enumerate(segs)]
        concat_in = "".join(f"[v{i}][a{i}]" for i in range(len(segs)))
        parts.append(f"{concat_in}concat=n={len(segs)}:v=1:a=1[vc][ac]")
        last = "vc"
        for k, (_, st, en) in enumerate(overlays):
            nxt = f"o{k}"
            parts.append(f"[{last}][{first_png + k}:v]overlay=0:0:"
                         f"enable='between(t,{st},{en})':shortest=1[{nxt}]")
            last = nxt
        # gentle loudness normalisation so clips sit at a consistent level
        parts.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{clip_id}.mp4"
        cmd += ["-filter_complex", ";".join(parts), "-map", f"[{last}]",
                "-map", "[aout]", "-t", f"{total:.3f}",
                "-c:v", "libx264", "-profile:v", "high", "-preset",
                "veryfast" if preview else "slow", "-crf", "20",
                "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
                "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)

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
    a = ap.parse_args()
    for s in a.specs:
        out = build(s, a.raw_dir, a.out_dir, a.preview)
        print(f"rendered {out}")


if __name__ == "__main__":
    main()
