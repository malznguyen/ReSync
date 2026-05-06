"""
Module: test_retry
Service: dispatcher
Purpose: Verify webhook retry limits and retry status logging.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.ai_worker.schemas import WebhookEvent
from services.dispatcher.consumer import EventDispatcher
from services.dispatcher.http_poster import PostResult
from services.dispatcher.models import WebhookConfig


def test_retryable_failure_retries_then_succeeds() -> None:
    asyncio.run(_assert_retryable_failure_retries_then_succeeds())


def test_retryable_failure_stops_after_three_retries() -> None:
    asyncio.run(_assert_retryable_failure_stops_after_three_retries())


def test_missing_webhook_logs_failed_without_retry() -> None:
    asyncio.run(_assert_missing_webhook_logs_failed_without_retry())


async def _assert_retryable_failure_retries_then_succeeds() -> None:
    delays: list[float] = []
    poster = FakePoster(
        [
            PostResult(ok=False, retryable=True, status_code=500, response_body="err"),
            PostResult(ok=True, retryable=False, status_code=200, response_body="ok"),
        ]
    )
    log_writer = FakeLogWriter()
    dispatcher = EventDispatcher(
        repository=FakeRepository([_make_webhook()]),
        poster=poster,
        log_writer=log_writer,
        max_retries=3,
        retry_backoff_seconds=(1.0, 2.0, 4.0),
        sleep=_fake_sleep(delays),
    )

    outcome = await dispatcher.dispatch(_make_event())
    await log_writer.wait_for(outcome.log_tasks)

    assert outcome.delivered is True
    assert poster.calls == 2
    assert delays == [1.0]
    assert [record["status"] for record in log_writer.records] == ["RETRY", "SUCCESS"]


async def _assert_retryable_failure_stops_after_three_retries() -> None:
    delays: list[float] = []
    poster = FakePoster(
        [
            PostResult(ok=False, retryable=True, status_code=500, response_body="err1"),
            PostResult(ok=False, retryable=True, status_code=500, response_body="err2"),
            PostResult(ok=False, retryable=True, status_code=500, response_body="err3"),
            PostResult(ok=False, retryable=True, status_code=500, response_body="err4"),
        ]
    )
    log_writer = FakeLogWriter()
    dispatcher = EventDispatcher(
        repository=FakeRepository([_make_webhook()]),
        poster=poster,
        log_writer=log_writer,
        max_retries=3,
        retry_backoff_seconds=(1.0, 2.0, 4.0),
        sleep=_fake_sleep(delays),
    )

    outcome = await dispatcher.dispatch(_make_event())
    await log_writer.wait_for(outcome.log_tasks)

    assert outcome.delivered is False
    assert poster.calls == 4
    assert delays == [1.0, 2.0, 4.0]
    assert [record["status"] for record in log_writer.records] == [
        "RETRY",
        "RETRY",
        "RETRY",
        "FAILED",
    ]


async def _assert_missing_webhook_logs_failed_without_retry() -> None:
    log_writer = FakeLogWriter()
    dispatcher = EventDispatcher(
        repository=FakeRepository([]),
        poster=FakePoster([]),
        log_writer=log_writer,
        max_retries=3,
        retry_backoff_seconds=(1.0, 2.0, 4.0),
        sleep=_fake_sleep([]),
    )

    outcome = await dispatcher.dispatch(_make_event())
    await log_writer.wait_for(outcome.log_tasks)

    assert outcome.delivered is False
    assert outcome.failed_deliveries == [{"reason": "no_active_webhooks"}]
    assert [record["status"] for record in log_writer.records] == ["FAILED"]


class FakeRepository:
    def __init__(self, webhooks: list[WebhookConfig]) -> None:
        self._webhooks = webhooks

    async def list_active_webhooks(self) -> list[WebhookConfig]:
        return self._webhooks


class FakePoster:
    def __init__(self, results: list[PostResult]) -> None:
        self._results = results
        self.calls = 0

    async def post(self, _webhook: WebhookConfig, _event: WebhookEvent) -> PostResult:
        self.calls += 1
        return self._results.pop(0)


class FakeLogWriter:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def log_event(
        self,
        _event: WebhookEvent,
        status: str,
        webhook_response: dict[str, Any] | None = None,
    ) -> asyncio.Task[None]:
        self.records.append({"status": status, "response": webhook_response})
        return asyncio.create_task(_noop())

    async def wait_for(self, tasks: list[asyncio.Task[None]]) -> None:
        await asyncio.gather(*tasks)


def _fake_sleep(delays: list[float]):
    async def sleep(delay: float) -> None:
        delays.append(delay)

    return sleep


async def _noop() -> None:
    return None


def _make_event() -> WebhookEvent:
    return WebhookEvent(
        event_id="event-001",
        event_type="hand_raise",
        camera_id="00000000-0000-0000-0000-000000000101",
        zone_id="00000000-0000-0000-0000-000000000201",
        zone_name="Dining",
        track_id="track-001",
        customer_id="00000000-0000-0000-0000-000000000301",
        timestamp=1_715_000_000.0,
        payload={},
    )


def _make_webhook() -> WebhookConfig:
    return WebhookConfig(
        webhook_id="wh_001",
        url="https://restaurant.example/webhook",
        secret="top-secret",
    )
