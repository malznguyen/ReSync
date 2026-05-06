"""
Module: redis_writer
Service: ingestion
Purpose: Encode frames and atomically overwrite the latest frame keys in Redis.
"""

from __future__ import annotations

import cv2
import numpy as np
from redis import Redis
from redis.exceptions import RedisError


class RedisFrameWriter:
    """Write only the latest frame and metadata for each camera."""

    def __init__(self, redis_client: Redis, jpeg_quality: int) -> None:
        self._redis = redis_client
        self._jpeg_quality = jpeg_quality

    def write_frame(
        self,
        camera_id: str,
        frame_id: str,
        timestamp: float,
        frame: np.ndarray,
    ) -> None:
        frame_bytes = self._encode_jpeg(frame)
        frame_key = f"cam:{camera_id}:frame:latest"
        meta_key = f"cam:{camera_id}:frame:meta"
        metadata = {
            "frame_id": frame_id,
            "timestamp": f"{timestamp:.6f}",
            "camera_id": camera_id,
        }

        try:
            with self._redis.pipeline(transaction=True) as pipe:
                pipe.set(frame_key, frame_bytes)
                pipe.hset(meta_key, mapping=metadata)
                pipe.execute()
        except RedisError as exc:
            raise RuntimeError(f"Failed to write frame for camera {camera_id}") from exc

    def _encode_jpeg(self, frame: np.ndarray) -> bytes:
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality]
        success, encoded_frame = cv2.imencode(".jpg", frame, encode_params)
        if not success:
            raise RuntimeError("Failed to JPEG encode frame")
        return encoded_frame.tobytes()


def create_redis_client(redis_url: str, socket_timeout_seconds: float) -> Redis:
    return Redis.from_url(
        redis_url,
        socket_connect_timeout=socket_timeout_seconds,
        socket_timeout=socket_timeout_seconds,
        health_check_interval=30,
    )
