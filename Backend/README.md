# BlindAssist unified server

The unified backend and AI server listens on port `8787` (`SERVER_PORT`) and
stores application data in `app.db`. It currently operates as a single-user
service.

Run it from the repository root:

```powershell
python unified_server.py
```

For development checks without Whisper, Ollama or Piper, use
`python unified_server.py --mock-ai`.

Endpoints:

- `GET /api/status`
- `GET`, `POST`, `DELETE /api/telemetry`
- `GET`, `POST`, `DELETE /api/location`
- `GET`, `POST /api/places`
- `DELETE /api/places/{id}`
- `GET /api/image`
- `POST /api/videoframe`
- `POST /api/recognize`

The ESP controls the telemetry interval. For example, it can send this request
every five seconds; the server only validates, stores and exposes the latest packet:

```http
POST /api/telemetry
Content-Type: application/json

{
  "latitude": 24.990782,
  "longitude": 121.346525,
  "address": "桃園市中壢區中大路300號",
  "heading": 45,
  "battery": 82,
  "source": "esp32"
}
```

`heading` is measured clockwise from north (`0 <= heading < 360`). Battery is a
percentage from 0 through 100. The response includes the normalized compass
direction (`N`, `NE`, `E`, `SE`, `S`, `SW`, `W` or `NW`).

On the first startup, existing entries from `data/savedPlaces.json` are imported
into SQLite once. New places and location updates are written only to SQLite.

Run the database tests with:

```powershell
python -m unittest discover -s Backend/tests -p "test_*.py"
```
