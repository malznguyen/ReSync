"""
Module: redis_io
Service: analytics
Purpose: Read track output and persist per-track analytics state in Redis.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError

from services.ai_worker.schemas import TrackOutput, TrackState

TRACK_STATE_TTL_SECONDS = 300

logger = logging.getLogger(__name__)


class RedisTrackReader:
    """Read the latest AI track output for one camera."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def read_latest(self, camera_id: str) -> TrackOutput | None:
        key = f"cam:{camera_id}:tracks:latest"
        try:
            payload = self._redis.get(key)
        except RedisError as exc:
            raise RuntimeError(f"Failed to read latest tracks for {camera_id}") from exc

        if payload is None:
            return None

        return TrackOutput.model_validate_json(_decode(payload))


class RedisTrackStateStore:
    """Persist track state using the strict track:{id}:state Redis key."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def get(self, track_id: str) -> TrackState | None:
        try:
            payload = self._redis.get(_state_key(track_id))
        except RedisError as exc:
            raise RuntimeError(f"Failed to read state for track {track_id}") from exc

        if payload is None:
            return None

        return TrackState.model_validate_json(_decode(payload))

    def set(self, state: TrackState) -> None:
        try:
            self._redis.setex(
                _state_key(state.track_id),
                TRACK_STATE_TTL_SECONDS,
                state.model_dump_json(),
            )
        except RedisError as exc:
            raise RuntimeError(
                f"Failed to write state for track {state.track_id}"
            ) from exc

    def cleanup_missing_tracks(
        self,
        camera_id: str,
        now: float,
        missing_after_seconds: float,
    ) -> int:
        deleted = 0
        for raw_key in self._redis.scan_iter(match="track:*:state"):
            key = _decode(raw_key)
            try:
                payload = self._redis.get(key)
            except RedisError as exc:
                raise RuntimeError(
                    f"Failed to read stale state candidate {key}"
                ) from exc

            if payload is None:
                continue

            try:
                state = TrackState.model_validate_json(_decode(payload))
            except ValidationError:
                logger.warning(
                    "Skipping invalid track state during cleanup", extra={"key": key}
                )
                continue

            if state.camera_id != camera_id:
                continue

            if now - state.last_seen_at > missing_after_seconds:
                self.delete(state.track_id)
                deleted += 1

        return deleted

    def delete(self, track_id: str) -> None:
        try:
            with self._redis.pipeline(transaction=True) as pipe:
                pipe.delete(_state_key(track_id))
                pipe.delete(f"track:{track_id}:customer_id")
                pipe.execute()
        except RedisError as exc:
            raise RuntimeError(f"Failed to delete state for track {track_id}") from exc


def create_redis_client(redis_url: str, socket_timeout_seconds: float) -> Redis:
    return Redis.from_url(
        redis_url,
        socket_connect_timeout=socket_timeout_seconds,
        socket_timeout=socket_timeout_seconds,
        health_check_interval=30,
    )


def _state_key(track_id: str) -> str:
    return f"track:{track_id}:state"


def _decode(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
