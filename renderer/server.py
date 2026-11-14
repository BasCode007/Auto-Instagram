#!/usr/bin/env python3
"""Tiny HTTP front end for the render scripts.

n8n 2.x ships without the Execute Command node and on a hardened image that
cannot install ffmpeg, so rendering lives in this sidecar instead. n8n calls:

    POST /render   {"type": "montage" | "quote", ...}  ->  {"video_url", "duration"}
    ("narrated" is accepted as an alias of "montage")
    GET  /healthz

The service is only reachable on the compose network; it is never published
to the host or the internet. API keys come from its own environment.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPTS = Path(os.environ.get("SCRIPTS_DIR", Path(__file__).resolve().parent.parent / "scripts"))
TIMEOUT = int(os.environ.get("RENDER_TIMEOUT_SECONDS", "900"))
MUSIC_DIR = os.environ.get("MUSIC_DIR", "")


def pick_music() -> str:
    """Rotate through MUSIC_DIR if the owner has dropped licensed tracks in it."""
    if not MUSIC_DIR or not os.path.isdir(MUSIC_DIR):
        return ""
    tracks = sorted(p for p in Path(MUSIC_DIR).iterdir() if p.suffix.lower() in {".mp3", ".m4a", ".wav"})
    if not tracks:
        return ""
    return str(tracks[int.from_bytes(os.urandom(2), "big") % len(tracks)])


def render(payload: dict) -> dict:
    kind = payload.get("type")
    env = dict(os.environ)
    env["HANDLE"] = str(payload.get("handle") or env.get("IG_HANDLE", ""))
    music = pick_music()
    if music:
        env["MUSIC"] = music

    if kind == "quote":
        quote = str(payload.get("quote") or "").strip()
        if not quote:
            raise ValueError("quote is required")
        env["QUOTE"] = quote
        env["PILLAR"] = str(payload.get("pillar") or "")
        script = "render_quote_card.sh"
    elif kind in ("montage", "narrated"):
        kind = "montage"
        text = str(payload.get("script") or "").strip()
        if not text:
            raise ValueError("script is required")
        keywords = payload.get("keywords") or ""
        if isinstance(keywords, list):
            keywords = ", ".join(str(k) for k in keywords)
        env["SCRIPT_TEXT"] = text
        env["BROLL_KEYWORDS"] = str(keywords)
        hero = payload.get("hero_prompts") or []
        if isinstance(hero, list):
            hero = "||".join(str(h) for h in hero if str(h).strip())
        env["HERO_PROMPTS"] = str(hero)
        script = "render_montage.sh"
    else:
        raise ValueError("type must be 'montage' or 'quote'")

    work = tempfile.mkdtemp(prefix="render-")
    env["OUT_DIR"] = work
    try:
        proc = subprocess.run(
            ["bash", str(SCRIPTS / script)], env=env, capture_output=True, text=True, timeout=TIMEOUT
        )
        if proc.returncode != 0:
            raise RuntimeError(f"{script} failed ({proc.returncode}): {proc.stderr.strip()[-600:]}")
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        result["type"] = kind
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path == "/healthz":
            self._send(200, {"status": "ok", "ffmpeg": bool(shutil.which("ffmpeg")),
                             "imagemagick": bool(shutil.which("convert"))})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/render":
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, render(payload))
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        except subprocess.TimeoutExpired:
            self._send(504, {"error": f"render exceeded {TIMEOUT}s"})
        except Exception as exc:  # surfaced to n8n, which alerts the owner
            print("renderer error:", str(exc)[-800:], flush=True)
            self._send(500, {"error": str(exc)})

    def log_message(self, fmt, *args):
        print("renderer:", fmt % args, flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"renderer listening on :{port}, scripts at {SCRIPTS}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
