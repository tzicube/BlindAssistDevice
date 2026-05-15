from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from django.http import Http404, HttpResponse, JsonResponse, StreamingHttpResponse

from Input_cam.webcam import (
    DEFAULT_TARGET_LABEL,
    generate_mjpeg_stream,
    get_available_camera_indexes,
    get_detectable_object_labels,
    load_yolo_model,
    resolve_target_label,
)


DEMO_DIR = Path(__file__).resolve().parents[2] / "WepApp" / "A.iDemo"
DEMO_ASSET_TYPES = {
    "style.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}
OBJECT_SEARCH_STATE = {
    "target_label": DEFAULT_TARGET_LABEL,
    "camera_index": 0,
}


def with_cors(response):
    """Allow the standalone frontend file to call these GET endpoints."""

    response["Access-Control-Allow-Origin"] = "*"
    return response


def health_check(request):
    return with_cors(
        JsonResponse(
            {
                "service": "AiServer",
                "status": "ok",
            }
        )
    )


def aidemo_page(request):
    """Serve the A.iDemo frontend from Django so the app runs same-origin."""

    response = HttpResponse(
        (DEMO_DIR / "index.html").read_text(encoding="utf-8"),
        content_type="text/html; charset=utf-8",
    )
    response["Cache-Control"] = "no-store"
    return response


def aidemo_asset(request, asset_name: str):
    """Serve the A.iDemo CSS and JavaScript assets."""

    if asset_name not in DEMO_ASSET_TYPES:
        raise Http404("Asset not found.")

    asset_path = DEMO_DIR / asset_name
    if not asset_path.exists():
        raise Http404("Asset not found.")

    response = HttpResponse(
        asset_path.read_text(encoding="utf-8"),
        content_type=DEMO_ASSET_TYPES[asset_name],
    )
    response["Cache-Control"] = "no-store"
    return response


def available_cameras(request):
    """Return a simple list of camera indexes the server can open."""

    max_cameras = request.GET.get("max", "5")
    try:
        max_camera_count = max(1, min(10, int(max_cameras)))
    except ValueError:
        return with_cors(JsonResponse({"error": "max must be an integer"}, status=400))

    cameras = get_available_camera_indexes(max_cameras=max_camera_count)
    return with_cors(
        JsonResponse(
            {
                "cameras": cameras,
                "default_camera_index": OBJECT_SEARCH_STATE["camera_index"],
            }
        )
    )


def detectable_objects(request):
    """Expose the object labels supported by the active YOLO model."""

    model = load_yolo_model()
    return with_cors(
        JsonResponse(
            {
                "objects": get_detectable_object_labels(model),
                "examples": ["bottle", "cup", "chair", "book", "cell phone", "remote"],
            }
        )
    )


def object_search_config(request):
    """Save the selected object and camera so the web app can start a stream."""

    model = load_yolo_model()
    target_input = request.GET.get("target", OBJECT_SEARCH_STATE["target_label"])
    camera_input = request.GET.get("camera", str(OBJECT_SEARCH_STATE["camera_index"]))

    try:
        camera_index = int(camera_input)
    except ValueError:
        return with_cors(JsonResponse({"error": "camera must be an integer"}, status=400))

    if camera_index < 0:
        return with_cors(
            JsonResponse({"error": "camera must be zero or greater"}, status=400)
        )

    try:
        resolved_target = resolve_target_label(model, target_input)
    except ValueError as exc:
        return with_cors(JsonResponse({"error": str(exc)}, status=400))

    OBJECT_SEARCH_STATE["target_label"] = resolved_target
    OBJECT_SEARCH_STATE["camera_index"] = camera_index
    stream_query = urlencode({"camera": camera_index, "target": resolved_target})

    return with_cors(
        JsonResponse(
            {
                "target_label": resolved_target,
                "camera_index": camera_index,
                "stream_url": request.build_absolute_uri(
                    f"/webcam/alignment-stream/?{stream_query}"
                ),
                "message": f"Server is ready to search for {resolved_target}.",
            }
        )
    )


def webcam_alignment_stream(request):
    """Stream the YOLO center-alignment webcam feed as MJPEG."""

    model = load_yolo_model()
    target_input = request.GET.get("target", OBJECT_SEARCH_STATE["target_label"])
    camera_param = request.GET.get("camera", str(OBJECT_SEARCH_STATE["camera_index"]))

    try:
        camera_index = int(camera_param)
    except ValueError:
        return with_cors(JsonResponse({"error": "camera must be an integer"}, status=400))

    try:
        resolved_target = resolve_target_label(model, target_input)
    except ValueError as exc:
        return with_cors(JsonResponse({"error": str(exc)}, status=400))

    response = StreamingHttpResponse(
        generate_mjpeg_stream(camera_index=camera_index, target_label=resolved_target),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )
    response["Cache-Control"] = "no-store"
    return with_cors(response)
