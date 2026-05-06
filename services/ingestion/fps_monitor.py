"""
Module: fps_monitor
Service: ingestion
Purpose: Measure current camera FPS with a one-second sliding window.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class FpsSnapshot:
    fps: float
    frame_drop_rate: float
    frames_in_window: int


class SlidingWindowFpsMonitor:
    """Track true current FPS using only frames from the last second."""

    def __init__(
        self,
        expected_fps: float,
        fps_warning_threshold: float,
        drop_warning_rate: float,
        log_interval_seconds: float,
        logger: logging.Logger,
    ) -> None:
        self._expected_fps = expected_fps
        self._fps_warning_threshold = fps_warning_threshold
        self._drop_warning_rate = drop_warning_rate
        self._log_interval_seconds = log_interval_seconds
        self._logger = logger
        self._frame_times: deque[float] = deque()
        self._last_log_at: float | None = None

    def record_frame(self, timestamp: float) -> None:
        self._frame_times.append(timestamp)
        self._trim(timestamp)

    def current_snapshot(self, timestamp: float) -> FpsSnapshot:
        self._trim(timestamp)
        fps = float(len(self._frame_times))
        frame_drop_rate = max((self._expected_fps - fps) / self._expected_fps, 0.0)
        return FpsSnapshot(
            fps=fps,
            frame_drop_rate=frame_drop_rate,
            frames_in_window=len(self._frame_times),
        )

    def log_if_due(self, camera_id: str, timestamp: float) -> None:
        if self._last_log_at is None:
            self._last_log_at = timestamp
            return

        if timestamp - self._last_log_at < self._log_interval_seconds:
            return

        self._last_log_at = timestamp
        snapshot = self.current_snapshot(timestamp)
        log_extra = {
            "camera_id": camera_id,
            "fps": round(snapshot.fps, 2),
            "frame_drop_rate": round(snapshot.frame_drop_rate, 4),
            "frames_in_window": snapshot.frames_in_window,
            "expected_fps": self._expected_fps,
        }

        if (
            snapshot.fps < self._fps_warning_threshold
            or snapshot.frame_drop_rate > self._drop_warning_rate
        ):
            self._logger.warning("Camera ingestion FPS below target", extra=log_extra)
            return

        self._logger.info("Camera ingestion FPS sample", extra=log_extra)

    def _trim(self, timestamp: float) -> None:
        window_start = timestamp - 1.0
        while self._frame_times and self._frame_times[0] <= window_start:
            self._frame_times.popleft()
