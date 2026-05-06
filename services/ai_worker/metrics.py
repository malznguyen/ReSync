"""
Module: metrics
Service: ai_worker
Purpose: Track simple processing FPS and latency samples for AI worker logs.
"""

from __future__ import annotations

import logging
from collections import deque


class ProcessingMetrics:
    """Measure processed FPS and frame-read-to-Redis-push latency."""

    def __init__(self, log_interval_seconds: float, logger: logging.Logger) -> None:
        self._log_interval_seconds = log_interval_seconds
        self._logger = logger
        self._processed_at: deque[float] = deque()
        self._latencies: deque[float] = deque(maxlen=300)
        self._last_log_at: float | None = None

    def record(self, processed_at: float, latency_seconds: float) -> None:
        self._processed_at.append(processed_at)
        self._latencies.append(latency_seconds)
        self._trim(processed_at)

    def log_if_due(
        self,
        camera_id: str,
        frame_id: str,
        track_count: int,
        timestamp: float,
    ) -> None:
        if self._last_log_at is None:
            self._last_log_at = timestamp
            return

        if timestamp - self._last_log_at < self._log_interval_seconds:
            return

        self._last_log_at = timestamp
        self._trim(timestamp)
        avg_latency = (
            sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        )
        self._logger.info(
            "AI worker performance sample",
            extra={
                "camera_id": camera_id,
                "frame_id": frame_id,
                "processed_fps": round(float(len(self._processed_at)), 2),
                "avg_latency_ms": round(avg_latency * 1000.0, 2),
                "latest_track_count": track_count,
            },
        )

    def _trim(self, timestamp: float) -> None:
        window_start = timestamp - 1.0
        while self._processed_at and self._processed_at[0] <= window_start:
            self._processed_at.popleft()
