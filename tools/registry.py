"""No-repeat registry: never cut the same moment twice.

Two checks before any clip is cut:
  1. Time overlap: the same source (same VOD/video id) and an overlapping
     time range is a repeat.
  2. Scene fingerprint: perceptual hashes (dHash) of frames sampled once a
     second. If most of a new clip's frames closely match frames of a clip we
     already made, it's the same scene, even from a different upload or a
     re-post of the same stream.

Data lives in registry/used.jsonl (one JSON object per clip), committed to git
so every session shares it.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "registry" / "used.jsonl"
HASH_W, HASH_H = 9, 8          # dHash 8x8 = 64 bits
MATCH_BITS = 10                # Hamming distance counted as "same frame"
MATCH_SHARE = 0.4              # share of frames matching -> same scene


def load() -> list[dict]:
    if not REG.exists():
        return []
    return [json.loads(l) for l in REG.read_text().splitlines() if l.strip()]


def frame_hashes(video: Path, start: float, end: float, fps: float = 1.0,
                 crop: str | None = None) -> list[int]:
    """dHash of frames sampled at `fps` between start and end (seconds).

    crop: optional ffmpeg crop expression applied first (e.g. to hash only the
    gameplay area and ignore the facecam/chat overlay).
    """
    vf = (f"{crop}," if crop else "") + \
        f"fps={fps},scale={HASH_W}:{HASH_H}:flags=area,format=gray"
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}",
         "-i", str(video), "-vf", vf, "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    px = np.frombuffer(raw, np.uint8)
    n = len(px) // (HASH_W * HASH_H)
    out = []
    for f in px[: n * HASH_W * HASH_H].reshape(n, HASH_H, HASH_W):
        bits = (f[:, 1:] > f[:, :-1]).flatten()
        out.append(int("".join("1" if b else "0" for b in bits), 2))
    return out


def _ham(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def scene_match(hashes: list[int], others: list[int]) -> float:
    """Share of `hashes` that have a near-identical frame in `others`."""
    if not hashes or not others:
        return 0.0
    # ignore near-uniform frames (black screens, loading) - they match anything
    useful = [h for h in hashes if 8 < bin(h).count("1") < 56]
    if not useful:
        return 0.0
    hits = sum(1 for h in useful if min(_ham(h, o) for o in others) <= MATCH_BITS)
    return hits / len(useful)


def check(source_id: str, start: float, end: float,
          hashes: list[int] | None = None) -> list[str]:
    """Return reasons this range is a repeat (empty list = OK to cut)."""
    problems = []
    for e in load():
        if e["source_id"] == source_id and start < e["end"] and end > e["start"]:
            problems.append(f"overlaps {e['clip_id']} ({e['start']:.0f}-{e['end']:.0f}s "
                            f"of the same source)")
        elif hashes and e.get("hashes"):
            share = scene_match(hashes, e["hashes"])
            if share >= MATCH_SHARE:
                problems.append(f"same scene as {e['clip_id']} "
                                f"({share:.0%} of frames match)")
    return problems


def add(clip_id: str, source_id: str, source_url: str, start: float, end: float,
        hashes: list[int], creator: str = "") -> None:
    REG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"clip_id": clip_id, "source_id": source_id, "source_url": source_url,
           "creator": creator, "start": round(start, 2), "end": round(end, 2),
           "hashes": hashes}
    # a re-render of the same clip replaces its old entry instead of adding a second one
    keep = [json.dumps(e) for e in load() if e.get("clip_id") != clip_id]
    REG.write_text("".join(line + "\n" for line in keep + [json.dumps(rec)]))


def used_ranges(source_id: str) -> list[tuple[float, float]]:
    return [(e["start"], e["end"]) for e in load() if e["source_id"] == source_id]
