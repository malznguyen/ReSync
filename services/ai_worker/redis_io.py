"""
Module: redis_io
Service: ai_worker
Purpose: Read latest frames from Redis and overwrite validated track output.
"""

from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError
from schemas import FrameEnvelope, FrameMetadata, TrackOutput


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
