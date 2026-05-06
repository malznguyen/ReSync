"""
Module: detector
Service: ai_worker
Purpose: Run YOLO pose tracking and convert detections to normalized track schemas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from schemas import Track

logger = logging.getLogger(__name__)
KEYPOINT_COUNT = 17
KEYPOINT_CONFIDENCE_THRESHOLD = 0.5


class PoseTracker:
    """Wrap Ultralytics YOLO pose tracking with ByteTrack persistence."""

    def __init__(
        self,
        model_path: str,
        tracker_config_path: str,
        confidence_threshold: float,
        iou_threshold: float,
        image_size: int,
        device: str | None,
    ) -> None:
        from ultralytics import YOLO

        self._model = YOLO(_resolve_model_path(model_path))
        self._tracker_config_path = tracker_config_path
        self._confidence_threshold = confidence_threshold
        self._iou_threshold = iou_threshold
        self._image_size = image_size
        self._device = device

    def track(self, frame_bytes: bytes) -> list[Track]:
        frame = _decode_frame(frame_bytes)
        height, width = frame.shape[:2]
        results = self._model.track(
            source=frame,
            persist=True,
            classes=[0],
            tracker=self._tracker_config_path,
            conf=self._confidence_threshold,
            iou=self._iou_threshold,
            imgsz=self._image_size,
            device=self._device,
            verbose=False,
        )

        if not results:
            return []

        return tracks_from_result(results[0], width=width, height=height)


def tracks_from_result(result: Any, width: int, height: int) -> list[Track]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or getattr(boxes, "id", None) is None:
        return []

    xyxy = _to_numpy(boxes.xyxy)
    track_ids = _to_numpy(boxes.id)
    confidences = _to_numpy(boxes.conf)
    keypoints = _extract_keypoints(result)

    tracks: list[Track] = []
    for index, track_id in enumerate(track_ids):
        bbox = normalize_xyxy_bbox(xyxy[index], width=width, height=height)
        track_keypoints = format_keypoints(keypoints, index)
        tracks.append(
            Track(
                track_id=str(int(track_id)),
                bbox=bbox,
                keypoints=track_keypoints,
                confidence=float(np.clip(confidences[index], 0.0, 1.0)),
            )
        )

    return tracks


def normalize_xyxy_bbox(
    xyxy: np.ndarray,
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = xyxy.astype(float)
    x1 = float(np.clip(x1 / width, 0.0, 1.0))
    y1 = float(np.clip(y1 / height, 0.0, 1.0))
    x2 = float(np.clip(x2 / width, 0.0, 1.0))
    y2 = float(np.clip(y2 / height, 0.0, 1.0))

    x = min(x1, x2)
    y = min(y1, y2)
    bbox_width = max(abs(x2 - x1), 0.0)
    bbox_height = max(abs(y2 - y1), 0.0)
    return (x, y, bbox_width, bbox_height)


def format_keypoints(
    keypoint_data: tuple[np.ndarray, np.ndarray] | None,
    track_index: int,
) -> list[tuple[float, float, float]]:
    if keypoint_data is None:
        return [(0.0, 0.0, 0.0)] * KEYPOINT_COUNT

    points, confidences = keypoint_data
    if track_index >= len(points):
        return [(0.0, 0.0, 0.0)] * KEYPOINT_COUNT

    formatted: list[tuple[float, float, float]] = []
    for point, confidence in zip(points[track_index], confidences[track_index]):
        confidence_value = float(np.clip(confidence, 0.0, 1.0))
        if confidence_value < KEYPOINT_CONFIDENCE_THRESHOLD:
            formatted.append((0.0, 0.0, 0.0))
            continue

        formatted.append(
            (
                float(np.clip(point[0], 0.0, 1.0)),
                float(np.clip(point[1], 0.0, 1.0)),
                confidence_value,
            )
        )

    while len(formatted) < KEYPOINT_COUNT:
        formatted.append((0.0, 0.0, 0.0))

    return formatted[:KEYPOINT_COUNT]


def _extract_keypoints(result: Any) -> tuple[np.ndarray, np.ndarray] | None:
    keypoints = getattr(result, "keypoints", None)
    if keypoints is None:
        return None

    normalized_points = getattr(keypoints, "xyn", None)
    confidences = getattr(keypoints, "conf", None)
    if normalized_points is None or confidences is None:
        return None

    return _to_numpy(normalized_points), _to_numpy(confidences)


def _decode_frame(frame_bytes: bytes) -> np.ndarray:
    encoded = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode frame bytes as an image")
    return frame


def _to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        return value.numpy()
    return np.asarray(value)


def _resolve_model_path(model_path: str) -> str:
    path = Path(model_path)
    if path.exists():
        return str(path)

    if path.name == model_path:
        return model_path

    logger.warning(
        "Configured YOLO model path does not exist; falling back to model name",
        extra={"model_path": model_path, "model_name": path.name},
    )
    return path.name
