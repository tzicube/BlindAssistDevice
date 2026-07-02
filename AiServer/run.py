import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path



HOST = "0.0.0.0"
PORT = 3012

UPLOAD_DIR = Path(r"F:\BlindAssistDevice\AiServer\ai\lastAudio")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_next_audio_path():
    audio_files = list(UPLOAD_DIR.glob("conversation_*.wav"))
    next_number = len(audio_files) + 1

    filename = f"conversation_{next_number:04d}.wav"
    return UPLOAD_DIR / filename


class BlindAssistHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self):
        if self.path == "/mode":
            self.handle_mode()
            return

        if self.path == "/conversation":
            self.handle_conversation()
            return

        self.send_json_error(HTTPStatus.NOT_FOUND, "Route not found")

    def handle_mode(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            request_data = json.loads(body.decode("utf-8"))

            mode = request_data.get("mode")




            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "audio/wav")


        except json.JSONDecodeError:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")

        except ValueError as e:
            self.send_json_error(HTTPStatus.BAD_REQUEST, str(e))

        except FileNotFoundError as e:
            self.send_json_error(HTTPStatus.NOT_FOUND, f"Audio file not found: {e}")

        except Exception as e:
            self.send_json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def handle_conversation(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            audio_bytes = self.rfile.read(content_length)

            save_path = get_next_audio_path()
            save_path.write_bytes(audio_bytes)

            print("Received audio")
            print("Saved to:", save_path)
            print("Size:", len(audio_bytes), "bytes")


            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "audio/wav")



        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def send_json_error(self, status_code, message):
        response = {
            "status": False,
            "message": message
        }

        data = json.dumps(response).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    server = ThreadingHTTPServer((HOST, PORT), BlindAssistHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()