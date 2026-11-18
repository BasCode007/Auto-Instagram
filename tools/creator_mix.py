#!/usr/bin/env python3
"""Show how our clips split across creators vs. the owner's rough target.

Target (a guide, not a quota): ~50% TheBurntPeanut, ~50% shared by IShowSpeed,
Lacy, xQc and TypicalGamer. Better moments always beat the mix.

Usage
  python3 tools/creator_mix.py            # all clips in registry/used.jsonl
  python3 tools/creator_mix.py --last 20  # only the most recent 20 clips
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = {"theburntpeanut": 0.50, "ishowspeed": 0.125, "lacy": 0.125,
          "xqc": 0.125, "typicalgamer": 0.125}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=0)
    a = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / "registry" / "used.jsonl").read_text().splitlines() if l.strip()]
    if a.last:
        rows = rows[-a.last:]
    n = len(rows) or 1
    count = collections.Counter(r.get("creator") or "?" for r in rows)
    print(f"{'creator':<16} {'clips':>5} {'share':>6} {'target':>7}  next")
    for c in sorted(set(count) | set(TARGET), key=lambda k: -TARGET.get(k, 0)):
        share, tgt = count[c] / n, TARGET.get(c, 0.0)
        hint = "more" if share < tgt - 0.05 else ("less" if share > tgt + 0.05 else "ok")
        print(f"{c:<16} {count[c]:>5} {share:>6.0%} {tgt:>7.0%}  {hint if tgt else 'only great moments'}")


if __name__ == "__main__":
    main()
