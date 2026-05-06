"""
Module: test_consumer
Service: dispatcher
Purpose: Verify failed messages are routed to DLQ before manual ack.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

from services.ai_worker.schemas import WebhookEvent
from services.dispatcher.consumer import RabbitMQConsumer
from services.dispatcher.models import DispatchOutcome


def test_failed_dispatch_routes_to_dlq_then_acks_original() -> None:
    asyncio.run(_assert_failed_dispatch_routes_to_dlq_then_acks_original())


def test_invalid_payload_routes_to_dlq_then_acks_original() -> None:
    asyncio.run(_assert_invalid_payload_routes_to_dlq_then_acks_original())


async def _assert_failed_dispatch_routes_to_dlq_then_acks_original() -> None:
    message = FakeMessage(_make_event().model_dump_json().encode("utf-8"))
    exchange = FakeExchange()
    consumer = RabbitMQConsumer(
        settings=_settings(),
        dispatcher=FakeDispatcher(
            DispatchOutcome(
                delivered=False,
                failed_deliveries=[{"webhook_id": "wh_001", "status_code": 500}],
                log_tasks=[asyncio.create_task(_noop())],
            )
        ),
        log_writer=FakeLogWriter(),
    )
    consumer._dlq_exchange = exchange

    await consumer._handle_message(message)

    assert message.acked is True
    assert message.nacked is False
    assert len(exchange.published) == 1
    published_body = json.loads(exchange.published[0]["message"].body)
    assert exchange.published[0]["routing_key"] == "dlq.webhook"
    assert published_body["reason"] == "webhook_delivery_failed"


async def _assert_invalid_payload_routes_to_dlq_then_acks_original() -> None:
    message = FakeMessage(b'{"bad": true}')
    exchange = FakeExchange()
    log_writer = FakeLogWriter()
    consumer = RabbitMQConsumer(
        settings=_settings(),
        dispatcher=FakeDispatcher(DispatchOutcome(delivered=True)),
        log_writer=log_writer,
    )
    consumer._dlq_exchange = exchange

    await consumer._handle_message(message)

    assert message.acked is True
    assert message.nacked is False
    assert len(exchange.published) == 1
    assert log_writer.invalid_messages == [b'{"bad": true}']


class FakeMessage:
    exchange = "events"
    routing_key = "events.hand_raise"

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.acked = False
        self.nacked = False

    async def ack(self) -> None:
        self.acked = True

    async def nack(self, requeue: bool = False) -> None:
        self.nacked = requeue


class FakeExchange:
    def __init__(self) -> None:
        self.published: list[dict[str, Any]] = []

    async def publish(self, message: Any, routing_key: str) -> None:
        self.published.append({"message": message, "routing_key": routing_key})


class FakeDispatcher:
    def __init__(self, outcome: DispatchOutcome) -> None:
        self._outcome = outcome

    async def dispatch(self, _event: WebhookEvent) -> DispatchOutcome:
        return self._outcome


class FakeLogWriter:
    def __init__(self) -> None:
        self.invalid_messages: list[bytes] = []

    def log_invalid_message(self, raw_body: bytes, _reason: str) -> asyncio.Task[None]:
        self.invalid_messages.append(raw_body)
        return asyncio.create_task(_noop())

    async def wait_for(self, tasks: list[asyncio.Task[None]]) -> None:
        await asyncio.gather(*tasks)


async def _noop() -> None:
    return None


def _settings() -> SimpleNamespace:
    return SimpleNamespace(dlq_routing_key="dlq.webhook")


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
