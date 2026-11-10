#!/usr/bin/env python3
"""Stand-in for the AI server in BlindAssistDevice (AiServer/test.py), for testing the app.

Same port and API, but needs no GPU, Whisper, Ollama or Piper -- only Python 3:

    POST /api/videoframe  image/jpeg -> {"status": true}      (keeps it as the "last frame")
    POST /api/recognize   audio/wav  -> audio/wav              (a short chime instead of a real answer)
    GET  /api/image                  -> the last frame          (what the family dashboard shows)

Everything the phone sends is saved in ./mock_ai_output/ so you can listen to the recorded
question and look at the frame.

    python mock_ai_server.py                      # port 8765
    python mock_ai_server.py --delay 3            # pretend the model takes 3 s
    python mock_ai_server.py --reply answer.wav   # play your own recorded answer back

Then in the app: long-press 「問問題」 and type the address printed below
(10.0.2.2 from the Android Studio emulator, the laptop's IP from a real phone).
On Windows, allow Python through the firewall when asked (tick Private AND Public networks,
because a phone hotspot is usually treated as a public network).
"""
import argparse
import io
import json
import math
import socket
import struct
import time
import wave
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OUT = Path("mock_ai_output")
state = {"last_frame": None, "reply": None, "delay": 0.0}


def chime_wav(sample_rate=22050):
    """Two rising tones, so you can hear that the answer came back."""
    frames = bytearray()
    for freq, dur in ((660, 0.18), (0, 0.06), (880, 0.25)):
        for i in range(int(sample_rate * dur)):
            env = min(1.0, i / 400, (int(sample_rate * dur) - i) / 400)
            v = 0 if freq == 0 else int(9000 * env * math.sin(2 * math.pi * freq * i / sample_rate))
            frames += struct.pack("<h", v)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def describe_wav(data):
    try:
        with wave.open(io.BytesIO(data)) as w:
            n = w.getnframes()
            rate = w.getframerate()
            raw = w.readframes(n)
            samples = struct.unpack("<%dh" % (len(raw) // 2), raw) if w.getsampwidth() == 2 else ()
            peak = max((abs(s) for s in samples), default=0)
            return "%.1f s, %d Hz, %d ch, peak %d%s" % (
                n / rate, rate, w.getnchannels(), peak, "  <- very quiet, check the mic" if peak < 1000 else "")
    except Exception as e:  # noqa: BLE001
        return "not a valid WAV (%s)" % e


def local_ips():
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if "/api/videoframe" not in self.path:
            print("%s  %s" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, payload):
        self._send(status, json.dumps(payload).encode(), "application/json")

    def _ctype(self):
        return (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()

    def do_GET(self):
        if self.path.split("?")[0] in ("/api/image", "/image"):
            if state["last_frame"] is None:
                return self._json(HTTPStatus.NOT_FOUND, {"status": False, "message": "No image yet"})
            return self._send(HTTPStatus.OK, state["last_frame"], "image/jpeg")
        self._json(HTTPStatus.NOT_FOUND, {"status": False, "message": "Route not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._body()
        if path in ("/api/videoframe", "/videoframe"):
            if self._ctype() not in ("image/jpeg", "image/jpg"):
                return self._json(HTTPStatus.BAD_REQUEST, {"status": False, "message": "Content-Type must be image/jpeg"})
            if not body:
                return self._json(HTTPStatus.BAD_REQUEST, {"status": False, "message": "Image payload is empty"})
            state["last_frame"] = body
            return self._json(HTTPStatus.OK, {"status": True})
        if path in ("/api/recognize", "/recognize"):
            if self._ctype() != "audio/wav":
                return self._json(HTTPStatus.BAD_REQUEST, {"status": False, "message": "Content-Type must be audio/wav"})
            if not body:
                return self._json(HTTPStatus.BAD_REQUEST, {"status": False, "message": "Audio payload is empty"})
            if state["last_frame"] is None:
                return self._json(HTTPStatus.NOT_FOUND, {
                    "status": False, "message": "No last image is available yet. Call /api/videoframe first."})
            stamp = datetime.now().strftime("%H%M%S")
            OUT.mkdir(exist_ok=True)
            (OUT / ("question_%s.wav" % stamp)).write_bytes(body)
            (OUT / ("frame_%s.jpg" % stamp)).write_bytes(state["last_frame"])
            print("    question: %s" % describe_wav(body))
            print("    frame:    %d bytes  -> saved in %s/" % (len(state["last_frame"]), OUT))
            if state["delay"]:
                time.sleep(state["delay"])
            return self._send(HTTPStatus.OK, state["reply"], "audio/wav")
        self._json(HTTPStatus.NOT_FOUND, {"status": False, "message": "Route not found"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--delay", type=float, default=0.0, help="seconds to wait before answering")
    ap.add_argument("--reply", type=Path, help="WAV file to send back instead of the chime")
    args = ap.parse_args()
    state["delay"] = args.delay
    state["reply"] = args.reply.read_bytes() if args.reply else chime_wav()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("Mock AI server on port %d" % args.port)
    print("In the app, long-press 問問題 and enter:")
    print("  Android Studio emulator:  10.0.2.2")
    for ip in local_ips() or ["(no network address found)"]:
        print("  Real phone on the same Wi-Fi / hotspot:  %s" % ip)
    print("Requests show up below. Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
