#!/usr/bin/env python3
"""Build an ASS subtitle file of big, centred, word-revealed captions (docs/STANDARD.md).

Usage:
  make_captions.py --out captions.ass --duration 31.2 \
      [--alignment tts.json | --words-json words.json | --text script.txt] [--font Inter]

Word timing, in order of preference:
  --alignment   an ElevenLabs "with-timestamps" response (character timings)
  --words-json  [{"text","start","end"}, ...]  (Whisper / any transcriber)
  --text        no timings: words are spread across the audio by length

Style: 1-2 words per beat, Montserrat/Inter extra-bold at 112 px (1080-wide canvas),
white with a soft dark edge, centred a little above the middle of the frame. Words
appear as they are spoken; the word being spoken, and any emphasis word, is gold.
No hook box, no label, no CTA: the hook is the first spoken line.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

MAX_WORDS = 2
GOLD = r"\c&H48C9F7&"      # #F7C948 in ASS BGR
WHITE = r"\c&HFFFFFF&"
POS = r"\an5\pos(540,900)"
EMPHASIS = {
    "money", "time", "wealth", "wealthy", "rich", "invest", "investing", "assets", "asset", "income",
    "hours", "compounding", "discipline", "freedom", "profit", "profits", "habit", "habits", "risk",
    "focus", "patience", "leverage", "equity", "cash", "debt", "own", "earn", "build", "buy",
}


def words_from_alignment(path):
    data = json.load(open(path, encoding="utf-8"))
    al = data.get("alignment") or data.get("normalized_alignment") or {}
    chars, starts, ends = al.get("characters") or [], al.get("character_start_times_seconds") or [], al.get("character_end_times_seconds") or []
    words, cur, w_start, w_end = [], "", None, 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append((cur, w_start, w_end)); cur, w_start = "", None
            continue
        if w_start is None:
            w_start = s
        cur += ch; w_end = e
    if cur:
        words.append((cur, w_start, w_end))
    return words


def words_from_json(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("words") or [w for s in data.get("segments", []) for w in s.get("words", [])]
    return [(str(w["text"]).strip(), float(w["start"]), float(w["end"])) for w in data if str(w.get("text", "")).strip()]


def words_estimated(text, duration):
    tokens = text.split()
    if not tokens:
        return []
    weights = [len(t) + 1.5 for t in tokens]
    total = sum(weights); out, t = [], 0.0
    for tok, w in zip(tokens, weights):
        span = duration * w / total; out.append((tok, t, t + span)); t += span
    return out


def chunk(words):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= MAX_WORDS or re.search(r"[.!?,;:]$", w[0]):
            chunks.append(cur); cur = []
    if cur:
        if len(cur) == 1 and chunks and len(chunks[-1]) < MAX_WORDS and not re.search(r"[.!?]$", chunks[-1][-1][0]):
            chunks[-1].extend(cur)
        else:
            chunks.append(cur)
    return chunks


def ts(seconds):
    seconds = max(0.0, seconds); h, rem = divmod(seconds, 3600); m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def esc(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def is_emph(word):
    return re.sub(r"[^a-z']", "", word.lower()) in EMPHASIS


def build(words, duration, font):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},112,&H00FFFFFF,&H00FFFFFF,&H40000000,&H90000000,-1,0,0,0,100,100,1,0,1,5,6,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = chunk(words)
    for ci, ch in enumerate(chunks):
        if ci + 1 < len(chunks):
            chunk_end = chunks[ci + 1][0][1] - 0.02          # never overlap the next beat
        else:
            chunk_end = min(ch[-1][2] + 0.6, duration)
        chunk_end = max(chunk_end, ch[-1][1] + 0.08)
        for k, (text, start, _end) in enumerate(ch):
            end = ch[k + 1][1] if k + 1 < len(ch) else chunk_end
            if end <= start:
                continue
            parts = []
            for j, (t, _s, _e) in enumerate(ch[: k + 1]):
                colour = GOLD if (j == k or is_emph(t)) else WHITE
                parts.append("{" + colour + r"\be1}" + esc(t.upper()))
            fad = r"\fad(50,0)" if k == 0 else ""
            lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{{{POS}{fad}}}" + " ".join(parts))
    return head + "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--alignment"); ap.add_argument("--words-json"); ap.add_argument("--text")
    ap.add_argument("--hook", default="")          # accepted for compatibility; the hook is spoken, not boxed
    ap.add_argument("--font", default="Inter")
    a = ap.parse_args()
    words = []
    for loader, arg in ((words_from_alignment, a.alignment), (words_from_json, a.words_json)):
        if arg and not words:
            try:
                words = loader(arg)
            except (OSError, ValueError, KeyError) as exc:
                print(f"make_captions: cannot read {arg} ({exc}); falling back", file=sys.stderr)
    if not words and a.text:
        words = words_estimated(open(a.text, encoding="utf-8").read(), a.duration)
    open(a.out, "w", encoding="utf-8").write(build(words, a.duration, a.font))
    return 0


if __name__ == "__main__":
    sys.exit(main())
