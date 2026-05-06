"""
Module: event_publisher
Service: analytics
Purpose: Publish validated analytics events to the RabbitMQ events exchange.
"""

from __future__ import annotations

import logging

import pika
from pika.exceptions import AMQPError

from services.ai_worker.schemas import WebhookEvent

EVENTS_EXCHANGE = "events"
ROUTING_KEYS = {
    "hand_raise": "events.hand_raise",
    "customer_seated": "events.customer_seated",
}

logger = logging.getLogger(__name__)


class RabbitMQEventPublisher:
    """Publish event payloads to a durable RabbitMQ topic exchange."""

    def __init__(self, host: str, port: int, user: str, password: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._connection: pika.BlockingConnection | None = None
        self._channel: pika.channel.Channel | None = None

    def publish(self, event: WebhookEvent) -> None:
        routing_key = ROUTING_KEYS[event.event_type]
        payload = event.model_dump_json()

        for attempt in range(2):
            try:
                channel = self._get_channel()
                channel.basic_publish(
                    exchange=EVENTS_EXCHANGE,
                    routing_key=routing_key,
                    body=payload.encode("utf-8"),
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=2,
                    ),
                )
                logger.info(
                    "Published analytics event",
                    extra={
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "routing_key": routing_key,
                    },
                )
                return
            except AMQPError as exc:
                self.close()
                if attempt == 1:
                    raise RuntimeError(
                        f"Failed to publish analytics event {event.event_id}"
                    ) from exc

    def close(self) -> None:
        if self._connection is not None and self._connection.is_open:
            self._connection.close()
        self._connection = None
        self._channel = None

    def _get_channel(self) -> pika.channel.Channel:
        if self._channel is not None and self._channel.is_open:
            return self._channel

        credentials = pika.PlainCredentials(self._user, self._password)
        parameters = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=10,
        )
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=EVENTS_EXCHANGE,
            exchange_type="topic",
            durable=True,
        )
        return self._channel
