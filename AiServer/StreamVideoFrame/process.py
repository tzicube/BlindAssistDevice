import logging

try:
    from AiServer.imageProcess.last_image_store import (
        get_last_image_path,
        store_last_image_bytes,
    )
except ModuleNotFoundError:
    from imageProcess.last_image_store import get_last_image_path, store_last_image_bytes


logger = logging.getLogger("blind_assist.stream_video_frame")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg"}


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def process_video_frame_request(
    image_bytes: bytes,
    content_type: str | None = None,
) -> dict[str, bool]:
    normalized_content_type = _normalize_content_type(content_type)

    if normalized_content_type not in ALLOWED_CONTENT_TYPES:
        logger.error("Unsupported video frame content type: %s", normalized_content_type)
        raise ValueError("Content-Type must be image/jpeg")

    if not image_bytes:
        logger.error("Video frame payload is empty")
        raise ValueError("Image payload is empty")

    last_image_path = store_last_image_bytes(image_bytes)

    logger.debug(
        "Video frame request completed successfully | last_image=%s",
        last_image_path,
    )
    return {"status": True}
