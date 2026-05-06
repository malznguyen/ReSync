"""
Module: test_redis_client
Service: api
Purpose: Verify Redis Pub/Sub messages for service configuration reloads.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from api.core import redis_client


class FakeRedis:
    def __init__(self, operations: list[tuple[Any, ...]]) -> None:
        self.operations = operations

    def publish(self, channel: str, payload: str) -> int:
        self.operations.append(("publish", channel, json.loads(payload)))
        return 1

    def delete(self, key: str) -> int:
        self.operations.append(("delete", key))
        return 1

    def close(self) -> None:
        self.operations.append(("close",))


def test_camera_reload_publishes_config_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operations: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        redis_client.Redis, "from_url", lambda *args, **kwargs: FakeRedis(operations)
    )

    redis_client.publish_camera_reload("created", "camera-1")

    assert operations[0] == (
        "publish",
        "config:reload",
        {"action": "created", "camera_id": "camera-1"},
    )
    assert operations[-1] == ("close",)


def test_zone_update_deletes_cache_and_publishes_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operations: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        redis_client.Redis, "from_url", lambda *args, **kwargs: FakeRedis(operations)
    )

    redis_client.publish_zone_config_updated("updated", "zone-1", "camera-1")

    assert operations[0] == ("delete", "zone:config:cache")
    assert operations[1] == (
        "publish",
        "zone:config:updated",
        {
            "action": "updated",
            "cache_key": "zone:config:cache",
            "camera_id": "camera-1",
            "zone_id": "zone-1",
        },
    )
    assert operations[-1] == ("close",)
