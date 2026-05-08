"""
Module: redis_io
Service: ai_worker
Purpose: Read latest frames from Redis and overwrite validated track output.
"""

from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError
from schemas import FrameEnvelope, FrameMetadata, TrackOutput

SYSTEM_INFERENCE_ENABLED_KEY = "system:inference:enabled"
SYSTEM_REID_ENABLED_KEY = "system:reid:enabled"


class RedisFrameReader:
    """Read the latest frame bytes and metadata for one camera."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def read_latest(self, camera_id: str) -> FrameEnvelope | None:
        frame_key = f"cam:{camera_id}:frame:latest"
        meta_key = f"cam:{camera_id}:frame:meta"

        try:
            with self._redis.pipeline(transaction=False) as pipe:
                pipe.get(frame_key)
                pipe.hgetall(meta_key)
                frame_bytes, raw_metadata = pipe.execute()
        except RedisError as exc:
            raise RuntimeError(
                f"Failed to read latest frame for camera {camera_id}"
            ) from exc

        if frame_bytes is None or not raw_metadata:
            return None

        metadata = FrameMetadata.model_validate(_decode_hash(raw_metadata))
        return FrameEnvelope(metadata=metadata, frame_bytes=frame_bytes)


class RedisTrackWriter:
    """Overwrite the latest validated track output for one camera."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def write_tracks(self, output: TrackOutput) -> None:
        key = f"cam:{output.camera_id}:tracks:latest"
        payload = output.model_dump_json()

        try:
            self._redis.set(key, payload)
        except RedisError as exc:
            raise RuntimeError(
                f"Failed to write latest tracks for camera {output.camera_id}"
            ) from exc


class RedisOverlayWriter:
    """Overwrite the latest backend-composited monitoring frame for one camera."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def write_overlay(
        self,
        camera_id: str,
        frame_id: str,
        timestamp: float,
        frame_bytes: bytes,
    ) -> None:
        frame_key = f"cam:{camera_id}:overlay:latest"
        meta_key = f"cam:{camera_id}:overlay:meta"
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
            raise RuntimeError(
                f"Failed to write latest overlay frame for camera {camera_id}"
            ) from exc


class RedisSystemControls:
    """Read runtime control flags shared with the Control API."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def is_inference_enabled(self) -> bool:
        return self._get_bool(SYSTEM_INFERENCE_ENABLED_KEY, default=True)

    def is_reid_enabled(self, default: bool) -> bool:
        return self._get_bool(SYSTEM_REID_ENABLED_KEY, default=default)

    def _get_bool(self, key: str, default: bool) -> bool:
        try:
            value = self._redis.get(key)
        except RedisError as exc:
            raise RuntimeError(f"Failed to read system control flag {key}") from exc
        return _decode_bool(value, default)


def create_redis_client(redis_url: str, socket_timeout_seconds: float) -> Redis:
    return Redis.from_url(
        redis_url,
        socket_connect_timeout=socket_timeout_seconds,
        socket_timeout=socket_timeout_seconds,
        health_check_interval=30,
    )


def _decode_hash(raw_metadata: dict[bytes, bytes]) -> dict[str, str]:
    return {
        key.decode("utf-8"): value.decode("utf-8")
        for key, value in raw_metadata.items()
    }


def _decode_bool(value: bytes | str | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default
