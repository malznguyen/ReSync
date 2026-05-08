"""
Module: overlay
Service: ai_worker
Purpose: Render exact AI-annotated frames for monitoring streams.
"""

from __future__ import annotations

import cv2
import numpy as np

from schemas import Track

BOX_COLOR = (224, 255, 96)
TEXT_COLOR = (24, 24, 24)
TEXT_BACKGROUND = (235, 248, 255)
KEYPOINT_COLOR = (76, 122, 255)
KEYPOINT_BORDER_COLOR = (255, 255, 255)
KEYPOINT_CONFIDENCE_THRESHOLD = 0.5
OVERLAY_JPEG_QUALITY = 85


def render_overlay_frame(frame_bytes: bytes, tracks: list[Track]) -> bytes:
    frame = _decode_frame(frame_bytes)
    frame_height, frame_width = frame.shape[:2]

    for track in tracks:
        _draw_track(frame, track, frame_width, frame_height)

    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), OVERLAY_JPEG_QUALITY]
    success, encoded = cv2.imencode(".jpg", frame, encode_params)
    if not success:
        raise RuntimeError("Failed to encode overlay frame")

    return encoded.tobytes()


def normalized_bbox_to_pixels(
    bbox: tuple[float, float, float, float],
    frame_width: int,
    frame_height: int,
) -> tuple[int, int, int, int]:
    x, y, width, height = bbox
    x1 = int(round(x * frame_width))
    y1 = int(round(y * frame_height))
    x2 = int(round((x + width) * frame_width))
    y2 = int(round((y + height) * frame_height))

    x1 = int(np.clip(x1, 0, max(frame_width - 1, 0)))
    y1 = int(np.clip(y1, 0, max(frame_height - 1, 0)))
    x2 = int(np.clip(x2, x1 + 1, frame_width))
    y2 = int(np.clip(y2, y1 + 1, frame_height))
    return x1, y1, x2, y2


def normalized_point_to_pixels(
    point_x: float,
    point_y: float,
    frame_width: int,
    frame_height: int,
) -> tuple[int, int]:
    x = int(round(point_x * frame_width))
    y = int(round(point_y * frame_height))
    x = int(np.clip(x, 0, max(frame_width - 1, 0)))
    y = int(np.clip(y, 0, max(frame_height - 1, 0)))
    return x, y


def _draw_track(
    frame: np.ndarray,
    track: Track,
    frame_width: int,
    frame_height: int,
) -> None:
    x1, y1, x2, y2 = normalized_bbox_to_pixels(track.bbox, frame_width, frame_height)
    cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)

    label = f"TRACK {track.track_id} {int(round(track.confidence * 100))}%"
    (text_width, text_height), baseline = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        1,
    )
    label_top = max(y1 - text_height - baseline - 8, 0)
    label_bottom = min(label_top + text_height + baseline + 8, frame_height)
    label_right = min(x1 + text_width + 10, frame_width)
    cv2.rectangle(
        frame,
        (x1, label_top),
        (label_right, label_bottom),
        TEXT_BACKGROUND,
        thickness=-1,
    )
    cv2.putText(
        frame,
        label,
        (x1 + 5, label_bottom - baseline - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )

    for point_x, point_y, confidence in track.keypoints:
        if confidence < KEYPOINT_CONFIDENCE_THRESHOLD:
            continue

        point = normalized_point_to_pixels(
            point_x,
            point_y,
            frame_width,
            frame_height,
        )
        cv2.circle(frame, point, 4, KEYPOINT_BORDER_COLOR, thickness=-1)
        cv2.circle(frame, point, 3, KEYPOINT_COLOR, thickness=-1)


def _decode_frame(frame_bytes: bytes) -> np.ndarray:
    encoded = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode frame bytes as an image")
    return frame
