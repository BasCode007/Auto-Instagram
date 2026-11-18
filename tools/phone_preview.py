#!/usr/bin/env python3
"""Show clips the way they look on an iPhone in Instagram Reels.

For each clip, grabs a frame and draws it inside an iPhone 15 screen
(1179x2556) with the Reels interface on top: header, the like / comment /
share / more / audio column, the username + caption block and the bottom tab
bar. Anything important hidden under that UI shows up immediately.

Usage
  python3 tools/phone_preview.py media/edits/lacy-map-first-look.mp4 [...] \
      --at 0.35 --out phone_check.jpg
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
PW, PH = 1179, 2556            # iPhone 15 screen
VW, VH = 1179, 2096            # 9:16 video at full width
VY = 120                       # video top (under the status bar)
WHITE = (255, 255, 255, 255)


def grab(video: Path, at: float) -> Image.Image:
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
         str(video)]).decode())
    with tempfile.NamedTemporaryFile(suffix=".png") as t:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * at:.2f}", "-i",
                        str(video), "-frames:v", "1", t.name], check=True)
        return Image.open(t.name).convert("RGB").resize((VW, VH), Image.LANCZOS)


def phone(frame: Image.Image, label: str) -> Image.Image:
    f_b = ImageFont.truetype(str(FONTS / "Inter-Bold.otf"), 38)
    f_s = ImageFont.truetype(str(FONTS / "Inter-SemiBold.otf"), 34)
    img = Image.new("RGBA", (PW, PH), (0, 0, 0, 255))
    img.paste(frame, (0, VY))
    ui = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ui)
    # status bar + Reels header
    d.text((60, 40), "9:41", font=f_b, fill=WHITE)
    d.text((60, VY + 40), "Reels", font=ImageFont.truetype(str(FONTS / "Inter-Bold.otf"), 58),
           fill=WHITE)
    d.rounded_rectangle([PW - 120, VY + 45, PW - 60, VY + 100], 12, outline=WHITE, width=5)
    # right action column
    x = PW - 110
    for i, y in enumerate(range(VY + 1150, VY + 1900, 150)):
        d.ellipse([x, y, x + 64, y + 64], outline=WHITE, width=6)
        if i < 3:
            d.text((x + 6, y + 72), ["98K", "1.2K", "4K"][i], font=f_s, fill=WHITE)
    # caption block
    d.ellipse([40, VY + 1720, 110, VY + 1790], fill=(200, 200, 200, 255))
    d.text((130, VY + 1730), "yourgta6page  · Follow", font=f_b, fill=WHITE)
    d.text((40, VY + 1815), "Hook line of the caption goes here... more", font=f_s, fill=WHITE)
    d.text((40, VY + 1870), "♫  Original audio", font=f_s, fill=WHITE)
    # bottom tab bar
    d.rectangle([0, VY + VH, PW, PH], fill=(0, 0, 0, 255))
    for i in range(5):
        cx = 120 + i * 235
        d.rounded_rectangle([cx - 30, VY + VH + 60, cx + 30, VY + VH + 120], 10,
                            outline=WHITE, width=5)
    img.alpha_composite(ui)
    out = Image.new("RGB", (PW + 60, PH + 160), (235, 235, 240))
    mask = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, PW, PH], 110, fill=255)
    out.paste(img.convert("RGB"), (30, 30), mask)
    ImageDraw.Draw(out).text((40, PH + 60), label,
                             font=ImageFont.truetype(str(FONTS / "Inter-Bold.otf"), 48),
                             fill=(20, 20, 30))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--at", type=float, default=0.35, help="position in the clip, 0..1")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--scale", type=float, default=0.32)
    ap.add_argument("--out", type=Path, default=Path("phone_check.jpg"))
    a = ap.parse_args()
    tiles = [phone(grab(v, a.at), v.stem) for v in a.videos]
    tw, th = int(tiles[0].width * a.scale), int(tiles[0].height * a.scale)
    rows = (len(tiles) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (tw * min(a.cols, len(tiles)), th * rows), (235, 235, 240))
    for i, t in enumerate(tiles):
        sheet.paste(t.resize((tw, th), Image.LANCZOS), ((i % a.cols) * tw, (i // a.cols) * th))
    sheet.save(a.out, quality=88)
    print(f"wrote {a.out} ({len(tiles)} clips)")


if __name__ == "__main__":
    main()
