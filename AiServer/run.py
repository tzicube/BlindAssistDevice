import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai.pipelines.mode.modeCheck import get_mode_audio


HOST = "0.0.0.0"
PORT = 8765


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

        self.send_json_error(HTTPStatus.NOT_FOUND, "Route not found")

    def handle_mode(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            request_data = json.loads(body.decode("utf-8"))

            mode = request_data.get("mode")
            audio_path = get_mode_audio(mode)

            audio_bytes = audio_path.read_bytes()

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio_bytes)))
            self.end_headers()
            self.wfile.write(audio_bytes)

        except json.JSONDecodeError:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")

        except ValueError as e:
            self.send_json_error(HTTPStatus.BAD_REQUEST, str(e))

        except FileNotFoundError as e:
            self.send_json_error(HTTPStatus.NOT_FOUND, f"Audio file not found: {e}")

        except Exception as e:
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
