# Saved-Place Voice Navigation — Server and Android Integration Guide

## 1. Purpose

This document describes the implemented server-side design for resolving an Android voice navigation request against locations saved by the web frontend.

Example requests:

- `Navigate to Home`
- `Take me to school`
- `帶我回家`
- `请带我去学校`

The expected behavior is:

1. Android converts speech to text.
2. Android sends the text to the BlindAssist server.
3. The server searches saved place names and spoken aliases.
4. If one saved place matches, the server returns its coordinates.
5. If several places match, Android asks the user to choose.
6. If no saved place matches, Android searches for the destination with its map/Places provider.

Android never needs access to the complete SQLite database.

## 2. Implementation status

The backend implementation is complete in this repository.

Implemented components:

- SQLite table for spoken place aliases.
- Optional aliases in `POST /api/places`.
- Alias replacement with `PUT /api/places/{id}/aliases`.
- Voice destination resolution with `POST /api/navigation/resolve`.
- Exact, accent-insensitive, multi-word, and guarded fuzzy matching.
- `saved_place`, `ambiguous`, and `not_found` outcomes.
- Unit and HTTP integration tests.
- Compatibility with the existing frontend and existing saved places.

Relevant files:

```text
Backend/database.py                  SQLite schema and persistence
Backend/navigation.py                Text normalization and matching
Backend/places_server.py             HTTP routes and validation
Backend/tests/test_database.py       Database and alias tests
Backend/tests/test_navigation.py     Resolver unit tests
Backend/tests/test_unified_server.py HTTP integration tests
unified_server.py                    Unified server entry point
```

## 3. Architecture

```text
Web frontend
    -> POST /api/places
    -> saves name, address, coordinates, and optional aliases

Android speech recognition
    -> recognized text
    -> POST /api/navigation/resolve
        -> normalize the request
        -> search saved place names and aliases
        -> return one of:
             saved_place
             ambiguous
             not_found

Android result handling
    -> saved_place: start a walking route to returned lat/lng
    -> ambiguous: speak the candidates and ask the user to choose
    -> not_found: search with Google Places/Maps or the selected map provider
```

The server is the online source of truth. Android may keep a local Room cache of `GET /api/places` only as an offline fallback.

## 4. Why the server does not return the complete database

The SQLite file may contain telemetry, application metadata, account data, and future private information. Android only requires saved-place data or, preferably, one resolved destination.

The resolver endpoint provides these benefits:

- Smaller responses.
- One matching implementation for every Android device.
- Immediate access to places added by the frontend.
- Central alias management.
- Easier authentication and user scoping in the future.
- No exposure of unrelated database tables.

## 5. Server startup and network address

Start the unified server from the repository root:

```powershell
python unified_server.py
```

The default configuration is:

```text
Bind host: 0.0.0.0
Port:      8787
```

For a physical Android phone, use the LAN IP address of the computer running the server:

```text
http://192.168.1.100:8787/
```

Do not use `0.0.0.0` as the Android destination. It is only the server bind address.

For an Android Emulator running on the same development computer, use:

```text
http://10.0.2.2:8787/
```

The phone and server must be able to reach each other on the local network. The computer firewall must allow inbound TCP traffic on port `8787`.

## 6. Database schema

The existing `saved_places` table stores the canonical place:

```text
saved_places
- id
- name
- address
- latitude
- longitude
- x_percent
- y_percent
- created_at
```

The server now creates this alias table automatically during startup:

```sql
CREATE TABLE IF NOT EXISTS place_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    FOREIGN KEY (place_id) REFERENCES saved_places(id) ON DELETE CASCADE,
    UNIQUE (place_id, normalized_alias)
);

CREATE INDEX IF NOT EXISTS idx_place_aliases_normalized
ON place_aliases(normalized_alias);
```

Deleting a saved place also deletes its aliases.

Example alias configuration:

| Saved name | Spoken aliases |
|---|---|
| `Home` | `home`, `家`, `回家`, `我的家` |
| `School` | `school`, `學校`, `学校` |

The place name is always searchable even when the alias list is empty.

## 7. API reference

### 7.1 List saved places

This endpoint already existed. Its response now includes `aliases`.

```http
GET /api/places HTTP/1.1
Host: 192.168.1.100:8787
Accept: application/json
```

Response:

```json
[
  {
    "id": 1,
    "name": "Home",
    "address": "1 Home Road, Taipei",
    "lat": 25.033,
    "lng": 121.5654,
    "aliases": ["家", "回家", "my home"]
  }
]
```

This endpoint returns saved places, not the complete database.

### 7.2 Create a saved place

`aliases` is optional. Existing frontend requests without it remain valid.

```http
POST /api/places HTTP/1.1
Host: 192.168.1.100:8787
Content-Type: application/json

{
  "name": "Home",
  "address": "1 Home Road, Taipei",
  "lat": 25.033,
  "lng": 121.5654,
  "aliases": ["家", "回家", "my home"]
}
```

Success status: `201 Created`

Response:

```json
{
  "id": 1,
  "name": "Home",
  "address": "1 Home Road, Taipei",
  "lat": 25.033,
  "lng": 121.5654,
  "aliases": ["家", "回家", "my home"]
}
```

Validation rules:

- `name` is required and limited to 100 characters.
- `address` is required and limited to 500 characters.
- `lat` must be between `-90` and `90`.
- `lng` must be between `-180` and `180`.
- `aliases` must be an array of strings when provided.
- A place may contain at most 20 aliases.
- Each alias is limited to 100 characters.
- Empty aliases are rejected.
- Duplicate normalized aliases for the same place are stored only once.

### 7.3 Replace aliases for an existing place

Use this endpoint to add aliases to a place that was created by the current frontend without aliases.

```http
PUT /api/places/1/aliases HTTP/1.1
Host: 192.168.1.100:8787
Content-Type: application/json

{
  "aliases": ["家", "回家", "my home"]
}
```

Success status: `200 OK`

The request replaces the complete alias list. Send an empty array to remove all aliases:

```json
{
  "aliases": []
}
```

An unknown place ID returns `404 Not Found`.

### 7.4 Resolve a spoken destination

```http
POST /api/navigation/resolve HTTP/1.1
Host: 192.168.1.100:8787
Content-Type: application/json

{
  "utterance": "帶我回家",
  "language": "zh-TW"
}
```

Fields:

- `utterance`: required non-empty speech-to-text result, maximum 500 characters.
- `language`: optional BCP-47 language tag, maximum 35 characters. The default is `en-US`.

The server officially accepts only English (`en-*`) and Chinese (`zh-*`) language tags. Chinese support includes Traditional Chinese such as `zh-TW` and Simplified Chinese such as `zh-CN`.

This endpoint accepts text, not an audio file.

#### Result: one saved place matched

```json
{
  "status": true,
  "matchType": "saved_place",
  "confidence": 1.0,
  "matchedText": "回家",
  "destination": {
    "id": 1,
    "name": "Home",
    "address": "1 Home Road, Taipei",
    "lat": 25.033,
    "lng": 121.5654
  }
}
```

Android should start navigation using `destination.lat` and `destination.lng`. It should not geocode the saved address again.

#### Result: no saved place matched

```json
{
  "status": true,
  "matchType": "not_found",
  "query": "taipei 101",
  "destination": null
}
```

Android should pass `query` to Google Places/Maps search. A valid `not_found` result uses HTTP `200`; it is not a server error.

#### Result: multiple saved places matched

```json
{
  "status": true,
  "matchType": "ambiguous",
  "query": "學校",
  "confidence": 1.0,
  "candidates": [
    {
      "id": 2,
      "name": "School North",
      "address": "North Campus",
      "lat": 25.01,
      "lng": 121.51
    },
    {
      "id": 3,
      "name": "School South",
      "address": "South Campus",
      "lat": 25.02,
      "lng": 121.52
    }
  ]
}
```

Android must not choose a candidate randomly. It should read the names/addresses and ask the user to select one.

### 7.5 Delete a place

```http
DELETE /api/places/1 HTTP/1.1
Host: 192.168.1.100:8787
```

The place and all of its aliases are deleted.

## 8. Matching behavior

The resolver is implemented in `Backend/navigation.py`.

Processing order:

1. Normalize Unicode with NFKC.
2. Convert text to lowercase with Unicode case folding.
3. Remove punctuation and collapse repeated whitespace.
4. Remove known navigation command prefixes.
5. Remove a small set of polite suffixes.
6. Compare the destination with each saved place name and alias.
7. Prefer an exact accented match.
8. Accept an exact accent-insensitive match for Latin-script English names.
9. Allow safe multi-word alias matching inside a longer request.
10. Use fuzzy matching only for labels of at least four characters and only above the configured threshold.
11. Return `ambiguous` when top candidates are too close.

Examples of recognized command wrappers include:

```text
navigate to ...
take me to ...
i want to go to ...
show me the way to ...
帶我去...
請帶我到...
導航到...
去...
带我去...
请带我到...
导航到...
```

Examples:

```text
"帶我回家"
-> extracted query: "回家"
-> alias: "回家"
-> saved_place: Home

"请带我去学校"
-> extracted query: "学校"
-> alias: "学校"
-> saved_place: School

"Navigate to schol"
-> extracted query: "schol"
-> guarded fuzzy match: "School"
-> saved_place: School
```

Short single-word aliases are not matched merely because they appear inside an unrelated longer word. This reduces unsafe navigation choices.

## 9. Android Retrofit contract

Example interface:

```kotlin
interface BlindAssistApi {
    @POST("api/navigation/resolve")
    suspend fun resolveDestination(
        @Body request: ResolveDestinationRequest
    ): ResolveDestinationResponse

    @GET("api/places")
    suspend fun getSavedPlaces(): List<SavedPlaceDto>
}
```

Example DTOs:

```kotlin
data class ResolveDestinationRequest(
    val utterance: String,
    val language: String = "en-US"
)

data class SavedPlaceDto(
    val id: Long,
    val name: String,
    val address: String,
    val lat: Double,
    val lng: Double,
    val aliases: List<String> = emptyList()
)

data class DestinationDto(
    val id: Long,
    val name: String,
    val address: String,
    val lat: Double,
    val lng: Double
)

data class ResolveDestinationResponse(
    val status: Boolean,
    val matchType: String,
    val confidence: Double? = null,
    val matchedText: String? = null,
    val query: String? = null,
    val destination: DestinationDto? = null,
    val candidates: List<DestinationDto> = emptyList()
)
```

Recommended Android result handling:

```kotlin
when (response.matchType) {
    "saved_place" -> {
        val destination = requireNotNull(response.destination)
        navigation.startWalkingRoute(destination.lat, destination.lng)
    }

    "ambiguous" -> {
        speech.askUserToChoose(response.candidates)
    }

    "not_found" -> {
        val mapQuery = response.query.orEmpty().ifBlank { recognizedText }
        placesSearch.search(mapQuery)
    }

    else -> {
        speech.say("The destination could not be resolved")
    }
}
```

Recommended client settings:

- Connection timeout: approximately 3–5 seconds.
- Retry at most once for a network failure.
- Do not retry HTTP `400` requests without obtaining new speech input.
- Treat `not_found` as a normal successful response.
- Do not send audio data to this endpoint.

## 10. Android map fallback

When the server returns `not_found`:

1. Search with `response.query` using Google Places SDK or the selected provider.
2. Bias results toward the phone's current GPS location.
3. If multiple results are plausible, read their names and addresses to the user.
4. Wait for explicit user confirmation.
5. Retrieve the selected result's coordinates.
6. Start a walking route with Google Routes/Directions.
7. Do not automatically save the external result. Save it only when the user asks.

If Android uses Google Places SDK directly, do not send its API key to this backend. Restrict the key by Android package name and signing certificate SHA fingerprint.

## 11. Offline fallback

The recommended online flow always uses `/api/navigation/resolve`. For temporary server or network failure, Android may:

1. Synchronize `GET /api/places` into Room when the app starts and when connectivity returns.
2. Store place aliases with each cached place.
3. Record the last synchronization time.
4. Run equivalent conservative matching against Room only after the resolver times out.
5. Tell the user when cached data may be outdated.

Do not download the database file. Cache only the JSON returned by `GET /api/places`.

## 12. HTTP errors

| HTTP status | Meaning | Android behavior |
|---|---|---|
| `200` | Resolution completed, including `not_found` and `ambiguous` | Handle `matchType` |
| `201` | Saved place created | Store/display returned place |
| `400` | Invalid request payload | Ask for new speech input or fix the payload |
| `404` | Place ID or route does not exist | Refresh local place data |
| `500` | Server/database failure | Announce temporary failure and use offline fallback |
| Timeout | Server cannot be reached | Use Room cache or map fallback carefully |

Error body format:

```json
{
  "status": false,
  "message": "utterance is required"
}
```

## 13. Android cleartext HTTP during development

If development uses `http://` instead of HTTPS, Android must permit cleartext traffic for the backend address through its manifest/network security configuration.

Production should use HTTPS. Do not enable unrestricted cleartext traffic in a production build.

## 14. Security and multi-user work still required for production

The current backend behaves as a single-user LAN service and allows all CORS origins. Before an internet or multi-user deployment, add:

- HTTPS.
- Authentication, such as a Bearer access token.
- `user_id` ownership on saved places and aliases.
- User-scoped database queries for every places and resolver endpoint.
- Rate limiting.
- Restricted CORS origins.
- Privacy-aware logging that does not retain complete spoken requests unnecessarily.

The resolver must never search or return another user's saved places.

## 15. Verification

Run all backend tests from the repository root:

```powershell
python -m unittest discover -s Backend/tests -p "test_*.py" -v
```

The tests cover:

- Database migration and existing-place compatibility.
- Alias creation, replacement, deduplication, and cascade deletion.
- English Unicode/case normalization.
- Traditional and Simplified Chinese commands without required spaces.
- English matching and small speech-to-text errors.
- Unsafe short partial-match rejection.
- Ambiguous results.
- `not_found` map fallback data.
- HTTP validation and integration with the unified server.

## 16. Handoff checklist for the Android AI/developer

1. Configure the Retrofit base URL for the server machine.
2. Add the request and response DTOs from this document.
3. Send the final Speech-to-Text string to `POST /api/navigation/resolve`.
4. Implement all three `matchType` branches.
5. Use returned coordinates directly for `saved_place`.
6. Add an accessible voice selection flow for `ambiguous`.
7. Search the map only for `not_found` or an intentional offline fallback.
8. Add Room caching from `GET /api/places` if offline support is required.
9. Confirm Android development cleartext configuration or use HTTPS.
10. Test on the same LAN with `Home`, `School`, `家`, `學校`, and `学校` aliases.

## 17. Final design decision

The production path is server-side destination resolution, not sending the complete database to Android. Android sends one recognized sentence to `POST /api/navigation/resolve`. The server returns a matched saved place, an ambiguity that requires confirmation, or a clean `not_found` result. Only the final case triggers a map/Places search.
