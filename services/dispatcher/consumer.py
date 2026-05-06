"""
Module: consumer
Service: dispatcher
Purpose: Consume RabbitMQ events with manual ack and dispatch them to webhooks.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, IncomingMessage, Message
from pydantic import ValidationError

from services.ai_worker.schemas import WebhookEvent
from services.dispatcher.config import DispatcherSettings
from services.dispatcher.http_poster import PostResult, WebhookPoster
from services.dispatcher.logger import EventLogWriter
from services.dispatcher.models import DispatchOutcome, WebhookConfig
from services.dispatcher.repository import WebhookRepository
from services.dispatcher.signature import json_payload_bytes

logger = logging.getLogger(__name__)
SleepFunc = Callable[[float], Awaitable[None]]


class EventDispatcher:
    """Coordinate webhook lookup, bounded retry, and event log creation."""

    def __init__(
        self,
        repository: WebhookRepository,
        poster: WebhookPoster,
        log_writer: EventLogWriter,
        max_retries: int,
        retry_backoff_seconds: tuple[float, ...],
        sleep: SleepFunc = asyncio.sleep,
    ) -> None:
        self._repository = repository
        self._poster = poster
        self._log_writer = log_writer
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._sleep = sleep

    async def dispatch(self, event: WebhookEvent) -> DispatchOutcome:
        webhooks = await self._repository.list_active_webhooks()
        log_tasks: list[asyncio.Task[None]] = []

        if not webhooks:
            log_tasks.append(
                self._log_writer.log_event(
                    event,
                    "FAILED",
                    {"error": "no_active_webhooks"},
                )
            )
            return DispatchOutcome(
                delivered=False,
                failed_deliveries=[{"reason": "no_active_webhooks"}],
                log_tasks=log_tasks,
            )

        failed_deliveries: list[dict[str, Any]] = []
        for webhook in webhooks:
            failure = await self._deliver_to_webhook(event, webhook, log_tasks)
            if failure is not None:
                failed_deliveries.append(failure)

        return DispatchOutcome(
            delivered=not failed_deliveries,
            failed_deliveries=failed_deliveries,
            log_tasks=log_tasks,
        )

    async def _deliver_to_webhook(
        self,
        event: WebhookEvent,
        webhook: WebhookConfig,
        log_tasks: list[asyncio.Task[None]],
    ) -> dict[str, Any] | None:
        total_attempts = self._max_retries + 1
        last_result: PostResult | None = None

        for attempt in range(1, total_attempts + 1):
            result = await self._poster.post(webhook, event)
            last_result = result

            if result.ok:
                log_tasks.append(
                    self._log_writer.log_event(
                        event,
                        "SUCCESS",
                        result.to_log_response(webhook, attempt),
                    )
                )
                return None

            if result.retryable and attempt <= self._max_retries:
                delay = self._retry_backoff_seconds[attempt - 1]
                log_tasks.append(
                    self._log_writer.log_event(
                        event,
                        "RETRY",
                        result.to_log_response(webhook, attempt, delay),
                    )
                )
                await self._sleep(delay)
                continue

            log_tasks.append(
                self._log_writer.log_event(
                    event,
                    "FAILED",
                    result.to_log_response(webhook, attempt),
                )
            )
            return {
                "webhook_id": webhook.webhook_id,
                "attempts": attempt,
                "status_code": result.status_code,
                "error": result.error,
            }

        return {
            "webhook_id": webhook.webhook_id,
            "attempts": total_attempts,
            "status_code": last_result.status_code if last_result else None,
            "error": last_result.error if last_result else "unknown_failure",
        }


class RabbitMQConsumer:
    """Consume the dispatcher queue with prefetch_count=1 and manual ack."""

    def __init__(
        self,
        settings: DispatcherSettings,
        dispatcher: EventDispatcher,
        log_writer: EventLogWriter,
    ) -> None:
        self._settings = settings
        self._dispatcher = dispatcher
        self._log_writer = log_writer
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._dlq_exchange: aio_pika.abc.AbstractExchange | None = None

    async def run(self, shutdown_event: asyncio.Event) -> None:
        await self._connect()
        logger.info(
            "Started dispatcher consumer",
            extra={"queue": self._settings.dispatch_queue_name},
        )
        try:
            await shutdown_event.wait()
        finally:
            await self.aclose()
            logger.info(
                "Stopped dispatcher consumer",
                extra={"queue": self._settings.dispatch_queue_name},
            )

    async def aclose(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

    async def _connect(self) -> None:
        self._connection = await aio_pika.connect_robust(
            host=self._settings.rabbitmq_host,
            port=self._settings.rabbitmq_port,
            login=self._settings.rabbitmq_user,
            password=self._settings.rabbitmq_password,
            virtualhost=self._settings.rabbitmq_vhost,
        )
        channel = await self._connection.channel(publisher_confirms=True)
        await channel.set_qos(prefetch_count=1)

        events_exchange = await channel.declare_exchange(
            self._settings.events_exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )
        self._dlq_exchange = await channel.declare_exchange(
            self._settings.dlq_exchange_name,
            ExchangeType.DIRECT,
            durable=True,
        )
        dlq_queue = await channel.declare_queue(
            self._settings.dlq_queue_name,
            durable=True,
        )
        await dlq_queue.bind(
            self._dlq_exchange,
            routing_key=self._settings.dlq_routing_key,
        )

        queue = await channel.declare_queue(
            self._settings.dispatch_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self._settings.dlq_exchange_name,
                "x-dead-letter-routing-key": self._settings.dlq_routing_key,
            },
        )
        await queue.bind(
            events_exchange, routing_key=self._settings.dispatch_routing_key
        )
        await queue.consume(self._handle_message, no_ack=False)

    async def _handle_message(self, message: IncomingMessage) -> None:
        try:
            event = WebhookEvent.model_validate_json(message.body)
        except (ValueError, ValidationError) as exc:
            self._log_writer.log_invalid_message(message.body, str(exc))
            await self._route_to_dlq(
                message,
                {
                    "reason": "invalid_event_payload",
                    "error": str(exc),
                    "raw_body": message.body.decode("utf-8", errors="replace"),
                },
            )
            await message.ack()
            return

        try:
            outcome = await self._dispatcher.dispatch(event)
            if outcome.delivered:
                await message.ack()
                logger.info(
                    "Dispatched event",
                    extra={"event_id": event.event_id, "event_type": event.event_type},
                )
                return

            await self._route_to_dlq(
                message,
                {
                    "reason": "webhook_delivery_failed",
                    "event": event.model_dump(mode="json"),
                    "failed_deliveries": outcome.failed_deliveries,
                },
            )
            await message.ack()
            logger.error(
                "Routed failed event to DLQ",
                extra={
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "failures": outcome.failed_deliveries,
                },
            )
        except Exception as exc:
            logger.exception(
                "Unexpected dispatcher failure",
                extra={"routing_key": getattr(message, "routing_key", None)},
            )
            try:
                await self._route_to_dlq(
                    message,
                    {
                        "reason": "unexpected_dispatcher_failure",
                        "error": str(exc),
                        "raw_body": message.body.decode("utf-8", errors="replace"),
                    },
                )
                await message.ack()
            except Exception:
                logger.exception("Failed to route message to DLQ; requeueing original")
                await message.nack(requeue=True)

    async def _route_to_dlq(
        self,
        message: IncomingMessage,
        payload: dict[str, Any],
    ) -> None:
        if self._dlq_exchange is None:
            raise RuntimeError("DLQ exchange is not initialized")

        headers = {
            "x-original-routing-key": getattr(message, "routing_key", ""),
            "x-original-exchange": getattr(message, "exchange", ""),
        }
        await self._dlq_exchange.publish(
            Message(
                body=json_payload_bytes(payload),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                headers=headers,
            ),
            routing_key=self._settings.dlq_routing_key,
        )
