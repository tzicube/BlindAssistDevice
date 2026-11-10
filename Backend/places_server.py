import json
import math
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

from .database import BackendDatabase


MAX_JSON_BYTES = 64 * 1024

database = BackendDatabase()


class ApiError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


class PlacesHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        path = self.request_path
        if path == "/api/status":
            self.handle_status()
        elif path == "/api/telemetry":
            self.send_json(
                HTTPStatus.OK,
                {"status": True, "telemetry": database.get_latest_location()},
            )
        elif path == "/api/location":
            self.send_json(
                HTTPStatus.OK,
                {"status": True, "location": database.get_latest_location()},
            )
        elif path == "/api/places":
            self.send_json(HTTPStatus.OK, database.list_places())
        else:
            self.route_not_found()

    def do_POST(self):
        path = self.request_path
        if path == "/api/telemetry":
            self.handle_telemetry_update()
        elif path == "/api/location":
            self.handle_location_update()
        elif path == "/api/places":
            self.handle_create_place()
        else:
            self.route_not_found()

    def do_DELETE(self):
        path = self.request_path
        if path in {"/api/location", "/api/telemetry"}:
            database.clear_latest_location()
            self.send_json(
                HTTPStatus.OK,
                {"status": True, "message": "Telemetry cleared"},
            )
            return

        prefix = "/api/places/"
        if not path.startswith(prefix):
            self.route_not_found()
            return

        try:
            place_id = int(path[len(prefix):])
        except ValueError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid place ID")
            return

        if not database.delete_place(place_id):
            self.send_error_json(HTTPStatus.NOT_FOUND, "Place not found")
            return

        self.send_json(
            HTTPStatus.OK,
            {"status": True, "message": "Place deleted"},
        )

    @property
    def request_path(self) -> str:
        return urlsplit(self.path).path

    def handle_status(self):
        location = database.get_latest_location()
        gps = (
            f"{location['latitude']:.6f}, {location['longitude']:.6f}"
            if location
            else "Waiting for device"
        )
        self.send_json(
            HTTPStatus.OK,
            {
                "backendOnline": True,
                "online": location is not None,
                "battery": location.get("battery") if location else None,
                "address": location.get("address", "") if location else "",
                "heading": location.get("heading") if location else None,
                "direction": location.get("direction") if location else None,
                "gps": gps,
                "location": location,
                "signal": (
                    f"Telemetry: {location['source']}" if location else "API connected"
                ),
                "time": datetime.now().astimezone().strftime("%H:%M:%S"),
                "navigation": {
                    "heading": location.get("heading"),
                    "direction": location.get("direction"),
                } if location else {},
                "detections": [],
                "systemStatus": (
                    f"Telemetry received from {location['source']}"
                    if location
                    else "Backend reachable; waiting for device telemetry"
                ),
            },
        )

    def handle_create_place(self):
        try:
            payload = self.read_json_object()
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ApiError("Place name is required")
            address = str(payload.get("address") or "").strip()
            if not address:
                raise ApiError("Place address is required")
            if len(address) > 500:
                raise ApiError("Place address must be 500 characters or fewer")

            latitude = coordinate(payload, "lat", "latitude", -90, 90)
            longitude = coordinate(payload, "lng", "longitude", -180, 180)
            x_percent = percentage(payload.get("xPercent"), "xPercent")
            y_percent = percentage(payload.get("yPercent"), "yPercent")

            place = database.create_place(
                name=name,
                latitude=latitude,
                longitude=longitude,
                x_percent=x_percent,
                y_percent=y_percent,
                address=address,
            )
            self.send_json(HTTPStatus.CREATED, place)
        except ApiError as error:
            self.send_error_json(error.status, str(error))
        except Exception as error:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

    def handle_location_update(self):
        try:
            payload = self.read_json_object()
            latitude = coordinate(payload, "latitude", "lat", -90, 90)
            longitude = coordinate(payload, "longitude", "lng", -180, 180)
            source = str(payload.get("source") or "simulator")[:80]
            updated_at = datetime.now().astimezone().isoformat(timespec="seconds")
            location = database.set_latest_location(
                latitude=latitude,
                longitude=longitude,
                source=source,
                updated_at=updated_at,
            )
            self.send_json(HTTPStatus.OK, {"status": True, "location": location})
        except ApiError as error:
            self.send_error_json(error.status, str(error))
        except Exception as error:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

    def handle_telemetry_update(self):
        try:
            payload = self.read_json_object()
            latitude = coordinate(payload, "latitude", "lat", -90, 90)
            longitude = coordinate(payload, "longitude", "lng", -180, 180)

            address = str(payload.get("address") or "").strip()
            if not address:
                raise ApiError("address is required")
            if len(address) > 500:
                raise ApiError("address must be 500 characters or fewer")

            heading = number_in_range(
                payload.get("heading", payload.get("direction")),
                "heading",
                0,
                360,
                maximum_inclusive=False,
            )
            battery = number_in_range(payload.get("battery"), "battery", 0, 100)
            direction = compass_direction(heading)
            source = str(payload.get("source") or "esp32")[:80]
            updated_at = datetime.now().astimezone().isoformat(timespec="seconds")

            telemetry = database.set_latest_location(
                latitude=latitude,
                longitude=longitude,
                address=address,
                heading=heading,
                direction=direction,
                battery=battery,
                source=source,
                updated_at=updated_at,
            )
            self.send_json(
                HTTPStatus.OK,
                {"status": True, "telemetry": telemetry},
            )
        except ApiError as error:
            self.send_error_json(error.status, str(error))
        except Exception as error:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

    def read_json_object(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError as error:
            raise ApiError("Invalid Content-Length") from error
        if content_length <= 0:
            raise ApiError("Request body is empty")
        if content_length > MAX_JSON_BYTES:
            raise ApiError("JSON request is too large")

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApiError("Invalid JSON") from error
        if not isinstance(payload, dict):
            raise ApiError("JSON body must be an object")
        return payload

    def route_not_found(self):
        self.send_error_json(HTTPStatus.NOT_FOUND, "Route not found")

    def send_error_json(self, status: HTTPStatus, message: str):
        self.send_json(status, {"status": False, "message": message})

    def send_json(self, status: HTTPStatus, payload):
        response = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def coordinate(
    payload: dict,
    primary: str,
    fallback: str,
    minimum: float,
    maximum: float,
) -> float:
    value = payload.get(primary, payload.get(fallback))
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ApiError(f"{primary} must be a number") from error
    if not math.isfinite(parsed) or not minimum <= parsed <= maximum:
        raise ApiError(f"{primary} must be between {minimum:g} and {maximum:g}")
    return parsed


def percentage(value, field: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ApiError(f"{field} must be a number") from error
    if not math.isfinite(parsed) or not 0 <= parsed <= 1:
        raise ApiError(f"{field} must be between 0 and 1")
    return parsed


def number_in_range(
    value,
    field: str,
    minimum: float,
    maximum: float,
    *,
    maximum_inclusive: bool = True,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ApiError(f"{field} must be a number") from error

    in_range = (
        minimum <= parsed <= maximum
        if maximum_inclusive
        else minimum <= parsed < maximum
    )
    if not math.isfinite(parsed) or not in_range:
        range_text = (
            f"between {minimum:g} and {maximum:g}"
            if maximum_inclusive
            else f"at least {minimum:g} and less than {maximum:g}"
        )
        raise ApiError(f"{field} must be {range_text}")
    return parsed


def compass_direction(heading: float) -> str:
    labels = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return labels[int((heading + 22.5) // 45) % len(labels)]
