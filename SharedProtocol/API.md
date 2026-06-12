# API Protocol

## POST /mode

Purpose: Select mode, check server connection, and return mode audio.

Request:
```json
( object search )
{
  "type": "mode_request",
  "mode": "object_search"
}
( conversation )
{
 "type": "mode_request",
 "mode": "conversation_mode"
}
( mobility )
{
 "type": "mode_request",
 "mode": "mobility_mode"
}
Response

Success
Status: 200 OK
Content-Type: audio/wav
Body: Binary WAV File

Failure
{
  "status": false,
  "message": "Unsupported mode"
}