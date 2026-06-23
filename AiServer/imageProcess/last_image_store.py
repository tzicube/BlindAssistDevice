from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from threading import RLock


logger = logging.getLogger("blind_assist.last_image_store")

BASE_DIR = Path(__file__).resolve().parent
LAST_IMAGE_PATH = BASE_DIR / "Lastimage.jpg"

_last_image_lock = RLock()
_last_image_bytes: bytes | None = None


def get_last_image_path() -> Path:
    return LAST_IMAGE_PATH


def load_last_image_bytes() -> bytes | None:
    with _last_image_lock:
        if _last_image_bytes is None:
            return None
        return bytes(_last_image_bytes)


def store_last_image_bytes(image_bytes: bytes) -> Path:
    global _last_image_bytes

    if not image_bytes:
        raise ValueError("Image payload is empty")

    image_bytes = bytes(image_bytes)

    with _last_image_lock:
        _last_image_bytes = image_bytes

        logger.info(
            "Updating in-memory last image store | path=%s | payload_size=%s bytes",
            LAST_IMAGE_PATH,
            len(image_bytes),
        )
        return LAST_IMAGE_PATH


def persist_last_image_bytes() -> Path | None:
    with _last_image_lock:
        if _last_image_bytes is None:
            logger.info("Skipping last image persistence because no in-memory frame exists")
            return None

        image_bytes = bytes(_last_image_bytes)

    LAST_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Persisting final in-memory last image to disk | path=%s | payload_size=%s bytes",
        LAST_IMAGE_PATH,
        len(image_bytes),
    )

    persisted_to_disk = _persist_last_image_to_disk(image_bytes)

    if not persisted_to_disk:
        raise OSError(f"Could not persist last image to disk: {LAST_IMAGE_PATH}")

    logger.info("Final last image persisted to disk successfully")
    return LAST_IMAGE_PATH


def _persist_last_image_to_disk(image_bytes: bytes) -> bool:
    temp_path = LAST_IMAGE_PATH.with_name(
        f"{LAST_IMAGE_PATH.stem}.{uuid.uuid4().hex}.tmp"
    )

    try:
        logger.info("Writing last image to temporary file: %s", temp_path)
        temp_path.write_bytes(image_bytes)

        if _try_atomic_replace(temp_path):
            return True

        return _try_direct_overwrite(image_bytes)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                logger.warning("Could not remove temporary image file: %s", temp_path)


def _try_atomic_replace(temp_path: Path) -> bool:
    for attempt in range(1, 4):
        try:
            logger.info(
                "Replacing last image on disk | attempt=%s | target=%s",
                attempt,
                LAST_IMAGE_PATH,
            )
            temp_path.replace(LAST_IMAGE_PATH)
            return True
        except PermissionError:
            logger.warning(
                "Atomic replace was blocked by Windows | attempt=%s | target=%s",
                attempt,
                LAST_IMAGE_PATH,
            )
            time.sleep(0.05 * attempt)

    return False


def _try_direct_overwrite(image_bytes: bytes) -> bool:
    for attempt in range(1, 4):
        try:
            logger.info(
                "Trying direct overwrite for last image | attempt=%s | target=%s",
                attempt,
                LAST_IMAGE_PATH,
            )
            LAST_IMAGE_PATH.write_bytes(image_bytes)
            return True
        except PermissionError:
            logger.warning(
                "Direct overwrite was blocked by Windows | attempt=%s | target=%s",
                attempt,
                LAST_IMAGE_PATH,
            )
            time.sleep(0.05 * attempt)

    return False
