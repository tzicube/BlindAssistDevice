import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import db
from Auth.SignIn.sign_in import authenticate_account
from Auth.SignUp.sign_up import create_account

HOST = "0.0.0.0"
PORT = 8001

SIGNUP_PATHS = {"/api/auth/signup", "/signup"}
LOGIN_PATHS = {"/api/auth/login", "/login"}
HEALTH_PATHS = {"/", "/health", "/api/health"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("blind_assist.auth")


class AuthHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        logger.info("Incoming GET request | path=%s", self.path)

        if self.path in HEALTH_PATHS:
            self.send_json_response(
                HTTPStatus.OK,
                {
                    "status": True,
                    "message": "Auth server is running.",
                    "available_routes": sorted(SIGNUP_PATHS | LOGIN_PATHS | HEALTH_PATHS),
                },
            )
            return

        self.send_json_error(HTTPStatus.NOT_FOUND, "Route not found.")

    def do_POST(self):
        logger.info("Incoming POST request | path=%s", self.path)

        if self.path in SIGNUP_PATHS:
            self.handle_signup()
            return

        if self.path in LOGIN_PATHS:
            self.handle_login()
            return

        self.send_json_error(HTTPStatus.NOT_FOUND, "Route not found.")

    def handle_signup(self):
        try:
            payload = self.read_json_body()
            result = create_account(payload)
            self.send_json_response(HTTPStatus.CREATED, result)
        except ValueError as exc:
            self.send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:
            logger.exception("Signup handler failed")
            self.send_json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def handle_login(self):
        try:
            payload = self.read_json_body()
            result = authenticate_account(payload)
            self.send_json_response(HTTPStatus.OK, result)
        except ValueError as exc:
            self.send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:
            logger.exception("Login handler failed")
            self.send_json_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def read_json_body(self) -> dict:
        content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Content-Type phai la application/json.")

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            raise ValueError("Request body khong duoc de trong.")

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("JSON body khong hop le.") from exc

        if not isinstance(payload, dict):
            raise ValueError("JSON body phai la object.")

        return payload

    def send_json_response(self, status: HTTPStatus, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json_error(self, status: HTTPStatus, message: str):
        logger.error("Sending error response | status=%s | message=%s", status, message)

        data = json.dumps(
            {
                "status": False,
                "error": message,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    db.create_tables()

    server = ThreadingHTTPServer((HOST, PORT), AuthHandler)
    logger.info("Auth server running at http://%s:%s", HOST, PORT)
    logger.info("Available endpoints: POST /api/auth/signup, POST /api/auth/login, GET /api/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        logger.info("Stopping auth server")
        server.server_close()


if __name__ == "__main__":
    main()
