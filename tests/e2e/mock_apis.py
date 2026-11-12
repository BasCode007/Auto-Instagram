#!/usr/bin/env python3
"""Stand-ins for every external API the pipeline calls, for end-to-end tests.

Serves an OpenAI-style chat endpoint, ElevenLabs with-timestamps, Pexels video
search, the Instagram Graph publish flow and Telegram sendMessage, and records
every request so a test can assert on what the pipeline actually sent.

  mock_apis.py --port 9911 --fixtures DIR --public DIR [--graph-mode ok|error|stuck]

fixtures DIR must hold voice.mp3 and one or more clip*.mp4.
"""
import argparse
import base64
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ARGS = None
LOG = []
STATE = {"polls": 0}
LOCK = threading.Lock()

NARRATED = {
    "on_screen_hook": "The habit that builds wealth",
    "hook": "The habit that quietly builds wealth is boring.",
    "script": ("The habit that quietly builds wealth is boring. You automate one transfer the day you get paid, "
               "before you can spend it. You never see the money, so you never miss it. Do that for ten years and "
               "the amount stops mattering. What matters is that you became someone who pays themselves first. "
               "Wealth is not a number you reach. It is a system you repeat. Start with one percent this week. "
               "Save this so future you actually does it."),
    "caption": "Pay yourself first, automatically. Start small and let time do the heavy lifting. Save this for payday.",
    "hashtags": ["MoneyHabits", "#payyourselffirst", "moneyhabits", "wealth building", "savingmoney", "extra1", "extra2"],
    "broll_keywords": ["city skyline sunrise", "person writing notebook", "coffee desk morning", "walking street", "calm ocean"],
}
QUOTE = {
    "quote": "Calm is a financial strategy. Panic is just expensive.",
    "hook": "Calm is a financial strategy. Panic is just expensive.",
    "caption": "Most money mistakes are made in a hurry. Slow down, breathe, decide tomorrow. Follow for one wealth habit a day.",
    "hashtags": ["wealthmindset", "moneymindset", "calm"],
}


class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def _file(self, path: Path, ctype):
        if not path.is_file():
            return self._json(404, {"error": "no such file"})
        data = path.read_bytes()
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def _record(self, body):
        with LOCK:
            LOG.append({"method": self.command, "path": self.path, "body": body,
                        "auth": self.headers.get("Authorization") or self.headers.get("xi-api-key") or ""})

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path); p = u.path
        if p == "/_log":
            return self._json(200, LOG)
        if p.startswith("/pub/"):
            return self._file(Path(ARGS.public) / p[5:], "video/mp4")
        if p.startswith("/clips/"):
            return self._file(Path(ARGS.fixtures) / p[7:], "video/mp4")
        self._record(None)
        if p == "/videos/search":
            clips = sorted(Path(ARGS.fixtures).glob("clip*.mp4"))
            base = f"http://127.0.0.1:{ARGS.port}/clips/"
            return self._json(200, {"videos": [{"video_files": [
                {"width": 1920, "height": 1080, "link": base + "landscape.mp4"},
                {"width": 2160, "height": 3840, "link": base + c.name},
                {"width": 1080, "height": 1920, "link": base + c.name}]} for c in clips]})
        if re.fullmatch(r"/v[\d.]+/CONTAINER1", p):
            with LOCK:
                STATE["polls"] += 1; n = STATE["polls"]
            if ARGS.graph_mode == "error":
                return self._json(200, {"status_code": "ERROR", "status": "Error: unsupported format", "id": "CONTAINER1"})
            if ARGS.graph_mode == "stuck" or n < 3:
                return self._json(200, {"status_code": "IN_PROGRESS", "id": "CONTAINER1"})
            return self._json(200, {"status_code": "FINISHED", "id": "CONTAINER1"})
        if re.fullmatch(r"/v[\d.]+/MEDIA1", p):
            return self._json(200, {"permalink": "https://www.instagram.com/reel/MOCK123/", "id": "MEDIA1"})
        self._json(404, {"error": {"message": "mock: unknown GET " + p}})

    def do_POST(self):  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8", "replace")
        ctype = self.headers.get("Content-Type", "")
        if "json" in ctype:
            try: body = json.loads(raw or "{}")
            except ValueError: body = raw
        else:
            body = {k: v[0] for k, v in parse_qs(raw).items()}
        self._record(body); p = urlparse(self.path).path
        if p.endswith("/chat/completions"):
            system = body["messages"][0]["content"]
            out = NARRATED if "narrated Reel" in system else QUOTE
            return self._json(200, {"choices": [{"message": {"role": "assistant", "content": json.dumps(out)}}]})
        if "/text-to-speech/" in p and p.endswith("/with-timestamps"):
            text = body["text"]; audio = (Path(ARGS.fixtures) / "voice.mp3").read_bytes()
            dur = float(ARGS.voice_seconds); step = dur / max(len(text), 1)
            return self._json(200, {"audio_base64": base64.b64encode(audio).decode(), "alignment": {
                "characters": list(text),
                "character_start_times_seconds": [round(i * step, 3) for i in range(len(text))],
                "character_end_times_seconds": [round((i + 1) * step, 3) for i in range(len(text))]}})
        if re.fullmatch(r"/v[\d.]+/[^/]+/media", p):
            return self._json(200, {"id": "CONTAINER1"})
        if re.fullmatch(r"/v[\d.]+/[^/]+/media_publish", p):
            return self._json(200, {"id": "MEDIA1"})
        if re.fullmatch(r"/bot[^/]*/sendMessage", p):
            return self._json(200, {"ok": True, "result": {"message_id": 1}})
        self._json(404, {"error": {"message": "mock: unknown POST " + p}})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9911)
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--public", required=True)
    ap.add_argument("--graph-mode", default="ok", choices=["ok", "error", "stuck"])
    ap.add_argument("--voice-seconds", default="29")
    ARGS = ap.parse_args()
    ThreadingHTTPServer(("0.0.0.0", ARGS.port), H).serve_forever()
