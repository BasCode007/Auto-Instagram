#!/usr/bin/env python3
"""Build an ASS subtitle file (hook + word-timed captions) for a narrated Reel.

Usage:
  make_captions.py --out captions.ass --duration 31.2 \
      [--alignment tts.json] [--text script.txt] [--hook "..."] [--font Inter]

Timing comes from an ElevenLabs "with-timestamps" response when --alignment is
given. Without it (e.g. a pre-recorded voice file) word times are estimated by
spreading the words across the audio in proportion to their length, which is
close enough for 2-3 word caption chunks.

Everything is positioned inside the Reels UI safe zone: clear of the top bar,
the bottom caption overlay and the right-hand button column.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

MAX_WORDS = 3          # words per caption chunk
MAX_CHARS = 18         # ...or fewer if the words are long
HOOK_SECONDS = 3.0


def words_from_alignment(path: str) -> list[tuple[str, float, float]]:
    data = json.load(open(path, encoding="utf-8"))
    al = data.get("alignment") or data.get("normalized_alignment") or {}
    chars = al.get("characters") or []
    starts = al.get("character_start_times_seconds") or []
    ends = al.get("character_end_times_seconds") or []
    words, cur, w_start, w_end = [], "", None, 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append((cur, w_start, w_end))
                cur, w_start = "", None
            continue
        if w_start is None:
            w_start = s
        cur += ch
        w_end = e
    if cur:
        words.append((cur, w_start, w_end))
    return words


def words_estimated(text: str, duration: float) -> list[tuple[str, float, float]]:
    tokens = text.split()
    if not tokens:
        return []
    weights = [len(t) + 1.5 for t in tokens]   # +1.5 ~ the pause after a word
    total = sum(weights)
    out, t = [], 0.0
    for tok, w in zip(tokens, weights):
        span = duration * w / total
        out.append((tok, t, t + span))
        t += span
    return out


def chunk(words):
    """Group words into short caption chunks, breaking at sentence ends."""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        text_len = sum(len(x[0]) for x in cur) + len(cur) - 1
        if len(cur) >= MAX_WORDS or text_len >= MAX_CHARS or re.search(r"[.!?]$", w[0]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [(" ".join(x[0] for x in c), c[0][1], c[-1][2]) for c in chunks]


def ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def build(words, hook: str, duration: float, font: str) -> str:
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},84,&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,0,0,1,6,2,5,110,190,0,1
Style: Hook,{font},70,&H00FFFFFF,&H00FFFFFF,&H00101010,&HB4000000,-1,0,0,0,100,100,0,0,3,18,0,8,110,190,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if hook:
        lines.append(f"Dialogue: 1,{ts(0)},{ts(min(HOOK_SECONDS, duration))},Hook,,0,0,0,,{esc(hook)}")
    chunks = chunk(words)
    for i, (text, start, end) in enumerate(chunks):
        # hold each chunk until the next one starts, so captions never flicker off
        nxt = chunks[i + 1][1] if i + 1 < len(chunks) else min(end + 0.4, duration)
        end = max(end, min(nxt, end + 0.6))
        # {\pos} pins captions at 62% height: below the hook, above the IG caption overlay
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{{\\pos(500,1190)\\fad(60,0)}}{esc(text)}")
    return head + "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--alignment")
    ap.add_argument("--text")
    ap.add_argument("--hook", default="")
    ap.add_argument("--font", default="Inter")
    a = ap.parse_args()

    words = []
    if a.alignment:
        try:
            words = words_from_alignment(a.alignment)
        except (OSError, ValueError) as exc:
            print(f"make_captions: bad alignment file ({exc}); estimating", file=sys.stderr)
    if not words and a.text:
        words = words_estimated(open(a.text, encoding="utf-8").read(), a.duration)

    open(a.out, "w", encoding="utf-8").write(build(words, a.hook.strip(), a.duration, a.font))
    return 0


if __name__ == "__main__":
    sys.exit(main())
