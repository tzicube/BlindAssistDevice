import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from Recognize.process import process_recognize_request
from StreamVideoFrame.process import process_video_frame_request

HOST = "0.0.0.0"
PORT = 8765

VIDEOFRAME_PATHS = {"/api/videoframe", "/videoframe"}
RECOGNIZE_PATHS = {"/api/recognize", "/recognize"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blind_assist.http")



class BlindAssistHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self):
        logger.info("Incoming POST request | path=%s", self.path)

        if self.path in VIDEOFRAME_PATHS:
            self.handle_videoframe()
            return

        if self.path in RECOGNIZE_PATHS:
            self.handle_recognize()
            return

        logger.warning("Route not found: %s", self.path)
        self.send_json_error(HTTPStatus.NOT_FOUND, "Route not found")

    def handle_videoframe(self):
        try:
            request_body = self.read_request_body()
            content_type = self.headers.get("Content-Type")

            logger.info(
                "Handling /api/videoframe | content_type=%s | payload_size=%s bytes",
                content_type or "missing",
                len(request_body),
            )

            result = process_video_frame_request(request_body, content_type)
            self.send_json_response(HTTPStatus.OK, result)
        except ValueError as exc:
            self.send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:
            logger.exception("Video frame handler failed")
            self.send_json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def handle_recognize(self):
        try:
            request_body = self.read_request_body()
            content_type = self.headers.get("Content-Type")

            logger.info(
                "Handling /api/recognize | content_type=%s | payload_size=%s bytes",
                content_type or "missing",
                len(request_body),
            )

            audio_response = process_recognize_request(request_body, content_type)
            self.send_binary_response(HTTPStatus.OK, audio_response, "audio/wav")
        except ValueError as exc:
            self.send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except FileNotFoundError as exc:
            self.send_json_error(HTTPStatus.NOT_FOUND, str(exc))
        except Exception as exc:
            logger.exception("Recognize handler failed")
            self.send_json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def read_request_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", 0))
        logger.info("Reading request body | content_length=%s bytes", content_length)
        return self.rfile.read(content_length)

    def send_json_response(self, status: HTTPStatus, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_binary_response(self, status: HTTPStatus, payload: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json_error(self, status, message):
        logger.error("Sending error response | status=%s | message=%s", status, message)

        data = json.dumps({
            "status": False,
            "error": message
        }, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    server = ThreadingHTTPServer((HOST, PORT), BlindAssistHandler)
    logger.info("Server running at http://%s:%s", HOST, PORT)
    logger.info("Available endpoints: POST /api/videoframe, POST /api/recognize")
    server.serve_forever()


if __name__ == "__main__":
    main()
