import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


# =========================================================
# SERVER CONFIG
# =========================================================

HOST = "0.0.0.0"
PORT = 8000


# =========================================================
# DATA FILE
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "savedPlaces.json"


DATA_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# JSON HELPERS
# =========================================================

def load_places():
    if not DATA_FILE.exists():
        DATA_FILE.write_text(
            "[]",
            encoding="utf-8"
        )
        return []

    try:
        content = DATA_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            return []

        data = json.loads(content)

        if not isinstance(data, list):
            return []

        return data

    except (json.JSONDecodeError, OSError):
        return []


def save_places(places):
    DATA_FILE.write_text(
        json.dumps(
            places,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# =========================================================
# HTTP HANDLER
# =========================================================

class PlacesHandler(BaseHTTPRequestHandler):

    # -----------------------------------------------------
    # CORS
    # -----------------------------------------------------

    def end_headers(self):
        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, DELETE, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        super().end_headers()

    # -----------------------------------------------------
    # OPTIONS
    # -----------------------------------------------------

    def do_OPTIONS(self):
        self.send_response(
            HTTPStatus.NO_CONTENT
        )

        self.end_headers()

    # -----------------------------------------------------
    # GET /api/places
    # -----------------------------------------------------

    def do_GET(self):

        if self.path == "/api/places":

            places = load_places()

            self.send_json(
                HTTPStatus.OK,
                places
            )

            return

        self.send_json(
            HTTPStatus.NOT_FOUND,
            {
                "status": False,
                "message": "Route not found"
            }
        )

    # -----------------------------------------------------
    # POST /api/places
    # -----------------------------------------------------

    def do_POST(self):

        if self.path != "/api/places":

            self.send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "status": False,
                    "message": "Route not found"
                }
            )

            return

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                content_length
            )

            place = json.loads(
                body.decode("utf-8")
            )

            if not isinstance(place, dict):

                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "status": False,
                        "message": "Invalid place data"
                    }
                )

                return

            # ---------------------------------------------
            # Validate required fields
            # ---------------------------------------------

            required_fields = [
                "id",
                "name",
                "lat",
                "lng"
            ]

            for field in required_fields:

                if field not in place:

                    self.send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "status": False,
                            "message":
                                f"Missing field: {field}"
                        }
                    )

                    return

            # ---------------------------------------------
            # Load current places
            # ---------------------------------------------

            places = load_places()

            # ---------------------------------------------
            # Prevent duplicate ID
            # ---------------------------------------------

            places = [
                existing
                for existing in places
                if existing.get("id") != place["id"]
            ]

            # ---------------------------------------------
            # Add new place
            # ---------------------------------------------

            places.append(place)

            save_places(places)

            self.send_json(
                HTTPStatus.CREATED,
                place
            )

        except json.JSONDecodeError:

            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "status": False,
                    "message": "Invalid JSON"
                }
            )

        except Exception as error:

            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "status": False,
                    "message": str(error)
                }
            )

    # -----------------------------------------------------
    # DELETE /api/places/:id
    # -----------------------------------------------------

    def do_DELETE(self):

        prefix = "/api/places/"

        if not self.path.startswith(prefix):

            self.send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "status": False,
                    "message": "Route not found"
                }
            )

            return

        try:

            place_id = int(
                self.path[len(prefix):]
            )

        except ValueError:

            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "status": False,
                    "message": "Invalid place ID"
                }
            )

            return

        places = load_places()

        new_places = [
            place
            for place in places
            if place.get("id") != place_id
        ]

        if len(new_places) == len(places):

            self.send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "status": False,
                    "message": "Place not found"
                }
            )

            return

        save_places(new_places)

        self.send_json(
            HTTPStatus.OK,
            {
                "status": True,
                "message": "Place deleted"
            }
        )

    # =====================================================
    # JSON RESPONSE
    # =====================================================

    def send_json(
        self,
        status_code,
        data
    ):

        response = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
        )

        self.end_headers()

        self.wfile.write(response)


# =========================================================
# START SERVER
# =========================================================

def main():

    server = ThreadingHTTPServer(
        (HOST, PORT),
        PlacesHandler
    )

    print(
        f"Saved Places server running at "
        f"http://localhost:{PORT}"
    )

    print(
        f"Data file: {DATA_FILE}"
    )

    server.serve_forever()


if __name__ == "__main__":
    main()