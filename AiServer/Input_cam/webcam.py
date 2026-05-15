from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Generator, Iterable

import cv2

if TYPE_CHECKING:
    from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ZONE_COLOR = (0, 255, 0)
OUTSIDE_COLOR = (0, 0, 255)
BOX_COLOR = (0, 165, 255)
TEXT_FONT = cv2.FONT_HERSHEY_SIMPLEX
DEFAULT_TARGET_LABEL = "bottle"
TARGET_ALIASES = {
    "chai": "bottle",
    "chai nuoc": "bottle",
    "binh nuoc": "bottle",
    "coc": "cup",
    "ly": "cup",
    "tach": "cup",
    "ghe": "chair",
    "sach": "book",
    "dien thoai": "cell phone",
    "phone": "cell phone",
    "remote": "remote",
    "dieu khien": "remote",
    "ban phim": "keyboard",
    "chuot": "mouse",
    "laptop": "laptop",
}


@dataclass(slots=True)
class TargetDetection:
    """Single target detection with derived center point."""

    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    cx: int
    cy: int

    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


@dataclass(slots=True)
class AlignmentState:
    """Tracks how many consecutive frames the target stays centered."""

    required_center_frames: int = 10
    center_count: int = 0

    @property
    def is_aligned(self) -> bool:
        return self.center_count >= self.required_center_frames


def get_model_path(model_path: str | Path | None = None) -> Path:
    """Resolve the YOLO model path from an explicit argument or environment."""

    configured_path = Path(model_path or os.getenv("YOLO_MODEL_PATH", "yolov8s.pt"))
    if not configured_path.is_absolute():
        configured_path = PROJECT_ROOT / configured_path
    return configured_path


@lru_cache(maxsize=2)
def _load_yolo_model_cached(model_path_text: str) -> YOLO:
    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "ultralytics is not installed in the active Python environment."
        ) from exc

    return YOLO(model_path_text)


def load_yolo_model(model_path: str | Path | None = None) -> YOLO:
    """Load the YOLOv8 model once and reuse it for realtime frames."""

    resolved_path = get_model_path(model_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"YOLO model not found: {resolved_path}")
    return _load_yolo_model_cached(str(resolved_path))


def normalize_label_text(text: str) -> str:
    """Normalize English or Vietnamese user input into a simple lookup key."""

    normalized = unicodedata.normalize("NFKD", text.strip().lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = ascii_text.replace("_", " ").replace("-", " ")
    return " ".join(ascii_text.split())


def get_model_name_map(model: YOLO) -> dict[str, str]:
    """Return a normalized-name -> original-name map from YOLO labels."""

    names = model.names
    if isinstance(names, dict):
        iterable: Iterable[tuple[int, str]] = names.items()
    else:
        iterable = enumerate(names)

    name_map: dict[str, str] = {}
    for _, name in iterable:
        original_name = str(name)
        name_map[normalize_label_text(original_name)] = original_name
    return name_map


def resolve_target_label(model: YOLO, target_label: str) -> str:
    """Map user input to a valid YOLO label, including common Vietnamese aliases."""

    cleaned_label = normalize_label_text(target_label or DEFAULT_TARGET_LABEL)
    cleaned_label = normalize_label_text(TARGET_ALIASES.get(cleaned_label, cleaned_label))
    name_map = get_model_name_map(model)

    if cleaned_label in name_map:
        return name_map[cleaned_label]

    supported_labels = ", ".join(get_detectable_object_labels(model)[:12])
    raise ValueError(
        f"Object `{target_label}` is not supported by the current YOLO model. "
        f"Try labels like: {supported_labels}."
    )


def get_detectable_object_labels(model: YOLO | None = None) -> list[str]:
    """Return the list of class labels supported by the YOLO model."""

    active_model = model or load_yolo_model()
    return sorted(get_model_name_map(active_model).values())


def get_target_class_id(model: YOLO, target_label: str) -> tuple[int, str]:
    """Resolve the numeric class id for the requested target object."""

    resolved_label = resolve_target_label(model, target_label)
    names = model.names
    if isinstance(names, dict):
        iterable: Iterable[tuple[int, str]] = names.items()
    else:
        iterable = enumerate(names)

    for class_id, name in iterable:
        if str(name) == resolved_label:
            return int(class_id), resolved_label

    raise ValueError(f"Unable to resolve class id for target `{resolved_label}`.")


def open_camera(camera_index: int) -> cv2.VideoCapture:
    """Open a camera and fall back across backends when Windows drivers vary."""

    if os.name != "nt":
        return cv2.VideoCapture(camera_index)

    candidate_backends = []
    if hasattr(cv2, "CAP_DSHOW"):
        candidate_backends.append(cv2.CAP_DSHOW)
    if hasattr(cv2, "CAP_MSMF"):
        candidate_backends.append(cv2.CAP_MSMF)

    for backend in candidate_backends:
        capture = cv2.VideoCapture(camera_index, backend)
        if capture.isOpened():
            return capture
        capture.release()

    return cv2.VideoCapture(camera_index)


def is_camera_available(camera_index: int) -> bool:
    """Check whether a camera index can be opened successfully."""

    capture = open_camera(camera_index)
    try:
        if not capture.isOpened():
            return False
        success, _ = capture.read()
        return bool(success)
    finally:
        capture.release()


def get_available_camera_indexes(max_cameras: int = 5) -> list[dict[str, int | str]]:
    """Probe a small set of camera indexes for the web app selector."""

    cameras: list[dict[str, int | str]] = []
    for camera_index in range(max_cameras):
        if is_camera_available(camera_index):
            cameras.append(
                {
                    "index": camera_index,
                    "label": f"Camera {camera_index}",
                }
            )
    return cameras


def compute_center_zone(
    frame_shape: tuple[int, ...],
    width_ratio: float = 0.30,
    height_ratio: float = 0.30,
) -> tuple[int, int, int, int]:
    """Create a centered rectangle that covers 30% of width and height."""

    frame_height, frame_width = frame_shape[:2]
    zone_width = int(frame_width * width_ratio)
    zone_height = int(frame_height * height_ratio)

    zone_x1 = (frame_width - zone_width) // 2
    zone_y1 = (frame_height - zone_height) // 2
    zone_x2 = zone_x1 + zone_width
    zone_y2 = zone_y1 + zone_height
    return zone_x1, zone_y1, zone_x2, zone_y2


def is_point_inside_zone(cx: int, cy: int, zone: tuple[int, int, int, int]) -> bool:
    """Check whether the target center point is inside the center zone."""

    zone_x1, zone_y1, zone_x2, zone_y2 = zone
    return zone_x1 <= cx <= zone_x2 and zone_y1 <= cy <= zone_y2


def get_guidance_text(cx: int, cy: int, zone: tuple[int, int, int, int]) -> str:
    """
    Return one simple movement instruction.

    When the point is outside both axes, choose the larger offset so the user
    receives a single, clear direction.
    """

    zone_x1, zone_y1, zone_x2, zone_y2 = zone
    horizontal_offset = 0
    vertical_offset = 0
    horizontal_text = ""
    vertical_text = ""

    if cx < zone_x1:
        horizontal_offset = zone_x1 - cx
        horizontal_text = "MOVE LEFT"
    elif cx > zone_x2:
        horizontal_offset = cx - zone_x2
        horizontal_text = "MOVE RIGHT"

    if cy < zone_y1:
        vertical_offset = zone_y1 - cy
        vertical_text = "MOVE UP"
    elif cy > zone_y2:
        vertical_offset = cy - zone_y2
        vertical_text = "MOVE DOWN"

    if horizontal_offset >= vertical_offset and horizontal_text:
        return horizontal_text
    if vertical_text:
        return vertical_text
    return "CENTERED"


def detect_target_objects(
    frame,
    model: YOLO,
    target_class_id: int,
    confidence_threshold: float = 0.35,
) -> list[TargetDetection]:
    """Run YOLO on a frame and return target boxes with center points."""

    detections: list[TargetDetection] = []
    results = model.predict(
        frame,
        conf=confidence_threshold,
        classes=[target_class_id],
        verbose=False,
    )

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            detections.append(
                TargetDetection(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    confidence=float(box.conf[0]),
                    cx=cx,
                    cy=cy,
                )
            )

    return detections


def select_primary_detection(detections: list[TargetDetection]) -> TargetDetection | None:
    """Choose the most prominent target to drive guidance."""

    if not detections:
        return None
    return max(detections, key=lambda detection: (detection.area, detection.confidence))


def draw_status_text(frame, text: str, color: tuple[int, int, int], origin: tuple[int, int]) -> None:
    """Small wrapper to keep text drawing consistent."""

    cv2.putText(frame, text, origin, TEXT_FONT, 0.9, color, 2, cv2.LINE_AA)


def process_alignment_frame(
    frame,
    model: YOLO,
    target_class_id: int,
    target_label: str,
    state: AlignmentState,
) -> tuple[object, str]:
    """
    Detect the selected object and annotate the frame with center guidance.

    Returns the processed frame plus the current guidance text so voice logic can
    reuse the same result later.
    """

    zone = compute_center_zone(frame.shape)
    zone_x1, zone_y1, zone_x2, zone_y2 = zone
    normalized_target = target_label.upper()
    cv2.rectangle(frame, (zone_x1, zone_y1), (zone_x2, zone_y2), ZONE_COLOR, 2)

    detections = detect_target_objects(frame, model, target_class_id)
    primary_detection = select_primary_detection(detections)

    for detection in detections:
        cv2.rectangle(
            frame,
            (detection.x1, detection.y1),
            (detection.x2, detection.y2),
            BOX_COLOR,
            2,
        )
        draw_status_text(
            frame,
            f"{target_label} {detection.confidence:.2f}",
            BOX_COLOR,
            (detection.x1, max(30, detection.y1 - 10)),
        )

    draw_status_text(frame, f"TARGET: {normalized_target}", ZONE_COLOR, (20, 145))

    if primary_detection is None:
        state.center_count = 0
        draw_status_text(frame, f"SEARCHING FOR {normalized_target}", OUTSIDE_COLOR, (20, 40))
        draw_status_text(
            frame,
            f"STABLE: {state.center_count}/{state.required_center_frames}",
            OUTSIDE_COLOR,
            (20, 75),
        )
        return frame, f"SEARCHING FOR {target_label}"

    inside_zone = is_point_inside_zone(primary_detection.cx, primary_detection.cy, zone)

    if inside_zone:
        state.center_count += 1
        cv2.circle(frame, (primary_detection.cx, primary_detection.cy), 6, ZONE_COLOR, -1)
        draw_status_text(frame, "CENTERED", ZONE_COLOR, (20, 40))
    else:
        state.center_count = 0
        cv2.circle(
            frame,
            (primary_detection.cx, primary_detection.cy),
            6,
            OUTSIDE_COLOR,
            -1,
        )
        guidance_text = get_guidance_text(primary_detection.cx, primary_detection.cy, zone)
        draw_status_text(frame, guidance_text, OUTSIDE_COLOR, (20, 40))

    draw_status_text(
        frame,
        f"STABLE: {state.center_count}/{state.required_center_frames}",
        ZONE_COLOR if inside_zone else OUTSIDE_COLOR,
        (20, 75),
    )

    if state.is_aligned:
        draw_status_text(frame, "OBJECT ALIGNED", ZONE_COLOR, (20, 110))
        return frame, "OBJECT ALIGNED"

    if inside_zone:
        return frame, "CENTERED"

    return frame, get_guidance_text(primary_detection.cx, primary_detection.cy, zone)


def generate_mjpeg_stream(
    camera_index: int = 0,
    model_path: str | Path | None = None,
    target_label: str = DEFAULT_TARGET_LABEL,
) -> Generator[bytes, None, None]:
    """Yield processed webcam frames as MJPEG for a Django streaming response."""

    model = load_yolo_model(model_path)
    target_class_id, resolved_target_label = get_target_class_id(model, target_label)
    state = AlignmentState()
    capture = open_camera(camera_index)

    if not capture.isOpened():
        raise RuntimeError(f"Unable to open webcam index {camera_index}.")

    try:
        while True:
            success, frame = capture.read()
            if not success:
                break

            processed_frame, _ = process_alignment_frame(
                frame,
                model,
                target_class_id,
                resolved_target_label,
                state,
            )
            encoded, buffer = cv2.imencode(".jpg", processed_frame)
            if not encoded:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
    finally:
        capture.release()


def run_webcam_alignment_demo(
    camera_index: int = 0,
    model_path: str | Path | None = None,
    target_label: str = DEFAULT_TARGET_LABEL,
) -> None:
    """Open a local OpenCV window for quick realtime MVP testing."""

    model = load_yolo_model(model_path)
    target_class_id, resolved_target_label = get_target_class_id(model, target_label)
    state = AlignmentState()
    capture = open_camera(camera_index)

    if not capture.isOpened():
        raise RuntimeError(f"Unable to open webcam index {camera_index}.")

    try:
        while True:
            success, frame = capture.read()
            if not success:
                break

            processed_frame, _ = process_alignment_frame(
                frame,
                model,
                target_class_id,
                resolved_target_label,
                state,
            )
            cv2.imshow("BlindAssist Center Alignment", processed_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_webcam_alignment_demo()
