#!/usr/bin/env python3
"""Build a 16:9 long-form compilation from existing clip specs.

    python3 tools/longform.py longform/funniest-1.json

Spec: {"id", "title", "clips": [{"id": "<clip spec id>", "title": "LOWER THIRD", "trim": [a, b]?}, ...]}
Clips play in the listed order, numbered from N down to 1. Each clip uses its
spec's source file and segments (full frame, so the streamer's facecam stays in),
swear words muted exactly like the Shorts, and a numbered lower third for 4 s.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_clip  # noqa: E402

FONT = ROOT / "tools/fonts/InterDisplay-Black.otf"
FONT2 = ROOT / "tools/fonts/Inter-Bold.otf"


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def part(src: Path, start: float, end: float, words, out: Path, label: str | None, banner: str | None):
    dur = end - start
    mutes = [(max(0, a - start), min(dur, b - start)) for a, b in make_clip.mute_windows(words)
             if b > start and a < end]
    af = "aresample=48000,aformat=channel_layouts=stereo"
    if mutes:
        af += ",volume=0:enable='" + "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in mutes) + "'"
    af += f",afade=t=in:st=0:d=0.05,afade=t=out:st={dur - 0.05:.2f}:d=0.05"
    vf = "scale=1920:1080:flags=bicubic,setsar=1,fps=60"
    if label:
        n, txt = label.split(" ", 1)
        vf += (f",drawtext=fontfile={FONT}:text='{esc(n)}':fontsize=120:fontcolor=0xFFD400:"
               f"borderw=7:bordercolor=black:x=80:y=770:enable='lt(t,4)',"
               f"drawtext=fontfile={FONT}:text='{esc(txt)}':fontsize=66:fontcolor=white:"
               f"borderw=5:bordercolor=black:x=80:y=905:enable='lt(t,4)'")
    if banner:
        vf += (f",drawtext=fontfile={FONT}:text='{esc(banner)}':fontsize=92:fontcolor=white:"
               f"borderw=7:bordercolor=black:x=(w-text_w)/2:y=110:enable='lt(t,3.5)'")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
                    "-vf", vf, "-af", af, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)], check=True)


def main(spec_path: str):
    spec = json.loads(Path(spec_path).read_text())
    work = ROOT / "media/longform" / spec["id"]
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    n = len(spec["clips"])
    for i, c in enumerate(spec["clips"]):
        if c.get("file"):   # a downloaded Twitch clip: {"file", "words_json"}
            src = ROOT / c["file"]
            words = json.loads((ROOT / c["words_json"]).read_text()).get(src.name, [])
            dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                 "-of", "csv=p=0", str(src)], text=True))
            cs = {"segments": [{"start": 0.0, "end": dur}], "words": words}
        else:
            cs = json.loads((ROOT / "clips" / f"{c['id']}.json").read_text())
            src = ROOT / "media/raw" / cs["source"]
        segs = cs["segments"]
        if c.get("trim"):
            segs = [{"start": c["trim"][0], "end": c["trim"][1]}]
        for j, g in enumerate(segs):
            out = work / f"p{i:02d}_{j}.mp4"
            label = f"#{n - i} {c['title']}" if j == 0 else None
            banner = spec.get("banner") if (i == 0 and j == 0) else None
            part(src, g["start"], g["end"], cs.get("words", []), out, label, banner)
            parts.append(out)
        print(f"  #{n - i} {c.get('id', c.get('file'))}")
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = ROOT / "media/longform" / f"{spec['id']}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-af", "loudnorm=I=-14:TP=-1.5", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(final)], check=True)
    print("rendered", final)


if __name__ == "__main__":
    main(sys.argv[1])
