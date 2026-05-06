"""
Module: redis_client
Service: api
Purpose: Publish configuration invalidation messages to Redis Pub/Sub.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from api.core.config import get_redis_url

CONFIG_RELOAD_CHANNEL = "config:reload"
ZONE_CACHE_KEY = "zone:config:cache"
ZONE_UPDATE_CHANNEL = "zone:config:updated"


class NotificationError(RuntimeError):
    pass


@contextmanager
def redis_connection() -> Iterator[Redis]:
    client = Redis.from_url(get_redis_url(), decode_responses=True, socket_timeout=2)
    try:
        yield client
    finally:
        client.close()


def publish_camera_reload(action: str, camera_id: str) -> None:
    payload = _payload(action=action, camera_id=camera_id)
    _publish(CONFIG_RELOAD_CHANNEL, payload)


def publish_zone_config_updated(action: str, zone_id: str, camera_id: str) -> None:
    payload = _payload(
        action=action,
        zone_id=zone_id,
        camera_id=camera_id,
        cache_key=ZONE_CACHE_KEY,
    )
    try:
        with redis_connection() as client:
            client.delete(ZONE_CACHE_KEY)
            client.publish(ZONE_UPDATE_CHANNEL, payload)
    except RedisError as exc:
        raise NotificationError("Failed to publish zone config update") from exc


def _publish(channel: str, payload: str) -> None:
    try:
        with redis_connection() as client:
            client.publish(channel, payload)
    except RedisError as exc:
        raise NotificationError(
            f"Failed to publish Redis notification: {channel}"
        ) from exc


def _payload(**values: Any) -> str:
    return json.dumps(values, separators=(",", ":"), sort_keys=True)
