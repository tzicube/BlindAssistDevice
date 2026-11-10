from __future__ import annotations

import logging
from threading import RLock


logger = logging.getLogger("blind_assist.last_image_store")

_last_image_lock = RLock()
_last_image_bytes: bytes | None = None


def load_last_image_bytes() -> bytes | None:
    with _last_image_lock:
        if _last_image_bytes is None:
            return None
        return bytes(_last_image_bytes)


def store_last_image_bytes(image_bytes: bytes) -> None:
    global _last_image_bytes

    if not image_bytes:
        raise ValueError("Image payload is empty")

    image_bytes = bytes(image_bytes)

    with _last_image_lock:
        _last_image_bytes = image_bytes

        logger.debug("Updated in-memory last image | payload_size=%s bytes", len(image_bytes))
