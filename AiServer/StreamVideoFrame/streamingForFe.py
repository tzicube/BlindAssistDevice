import logging

from imageProcess.last_image_store import load_last_image_bytes


logger = logging.getLogger("blind_assist.stream_video_frame.fe")


def process_image_request() -> bytes:
    image_bytes = load_last_image_bytes()

    if image_bytes is None:
        logger.error("No in-memory last image is available for FE streaming")
        raise FileNotFoundError(
            "No last image is available yet. Call /api/videoframe first."
        )

    logger.info(
        "Serving in-memory last image to FE | payload_size=%s bytes",
        len(image_bytes),
    )
    return image_bytes
