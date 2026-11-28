#!/usr/bin/env python3
"""Turn speech in a source clip into timed caption labels for a clip spec.

Prints a JSON "labels" list (times relative to the start of the cut) that
you can paste into clips/<id>.json. Always read the output against the
audio: fix names and slang by hand before rendering.

Needs: pip install faster-whisper   (first run downloads the model)

Usage
  python3 tools/transcribe.py media/raw/GTAVI_Trailer_2.mp4 --start 8.15 --end 25.6
"""
from __future__ import annotations

import argparse
import json
import subprocess

import numpy as np
from faster_whisper import WhisperModel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--max-words", type=int, default=7,
                    help="split long sentences into chunks of this many words")
    a = ap.parse_args()

    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(a.start), "-t", str(a.end - a.start),
         "-i", a.source, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, word_timestamps=True, vad_filter=True)

    labels = []
    for seg in segments:
        words = list(seg.words)
        for i in range(0, len(words), a.max_words):
            chunk = words[i:i + a.max_words]
            text = " ".join(w.word.strip() for w in chunk)
            labels.append({"start": round(chunk[0].start, 2),
                           "end": round(chunk[-1].end + 0.25, 2),
                           "text": text})
    # never let a caption run into the next one
    for cur, nxt in zip(labels, labels[1:]):
        cur["end"] = min(cur["end"], nxt["start"])
    print(json.dumps(labels, indent=2))


if __name__ == "__main__":
    main()
