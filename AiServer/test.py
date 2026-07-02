import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from Recognize.process import process_recognize_request
from StreamVideoFrame.process import process_video_frame_request
from StreamVideoFrame.streamingForFe import process_image_request
from imageProcess.last_image_store import persist_last_image_bytes

HOST = "0.0.0.0"
PORT = 8765

VIDEOFRAME_PATHS = {"/api/videoframe", "/videoframe"}
RECOGNIZE_PATHS = {"/api/recognize", "/recognize"}
IMAGE_PATHS = {"/api/image", "/image"}
QUIET_REQUEST_PATHS = VIDEOFRAME_PATHS | IMAGE_PATHS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blind_assist.http")



class BlindAssistHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def log_message(self, format, *args):
        if self.path in QUIET_REQUEST_PATHS:
            return
        logger.info("%s - %s", self.address_string(), format % args)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        if self.path not in QUIET_REQUEST_PATHS:
            logger.info("Incoming GET request | path=%s", self.path)

        if self.path in IMAGE_PATHS:
            self.handle_image()
            return

        logger.warning("Route not found: %s", self.path)
        self.send_json_error(HTTPStatus.NOT_FOUND, "Route not found")

    def do_POST(self):
        if self.path not in QUIET_REQUEST_PATHS:
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

    def handle_image(self):
        try:
            image_response = process_image_request()
            self.send_binary_response(
                HTTPStatus.OK,
                image_response,
                "image/jpeg",
                extra_headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        except FileNotFoundError as exc:
            self.send_json_error(HTTPStatus.NOT_FOUND, str(exc), log_error=False)
        except Exception as exc:
            logger.exception("Image handler failed")
            self.send_json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def read_request_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length)

    def send_json_response(self, status: HTTPStatus, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_binary_response(
        self,
        status: HTTPStatus,
        payload: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if extra_headers:
            for header_name, header_value in extra_headers.items():
                self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(payload)

    def send_json_error(self, status, message, log_error: bool = True):
        if log_error:
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
    logger.info(
        "Available endpoints: GET /api/image, POST /api/videoframe, POST /api/recognize"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        logger.info("Stopping HTTP server")
        server.server_close()

        try:
            persisted_path = persist_last_image_bytes()
            if persisted_path is not None:
                logger.info("Saved final last image to disk: %s", persisted_path)
        except Exception:
            logger.exception("Failed to persist final last image during shutdown")


if __name__ == "__main__":
    main()
