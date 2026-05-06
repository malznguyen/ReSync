"""
Module: logger
Service: dispatcher
Purpose: Persist dispatcher event processing records into PostgreSQL asynchronously.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.ai_worker.schemas import WebhookEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EventLogRecord:
    event_type: str
    customer_id: str | None
    zone_id: str | None
    camera_id: str | None
    track_id: str | None
    timestamp: datetime
    status: str
    payload: dict[str, Any]
    webhook_response: dict[str, Any] | None = None


class EventLogWriter:
    """Write analytics.events rows through async SQLAlchemy background tasks."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._tasks: set[asyncio.Task[None]] = set()

    def log_event(
        self,
        event: WebhookEvent,
        status: str,
        webhook_response: dict[str, Any] | None = None,
    ) -> asyncio.Task[None]:
        record = EventLogRecord(
            event_type=event.event_type,
            customer_id=event.customer_id,
            zone_id=event.zone_id,
            camera_id=event.camera_id,
            track_id=event.track_id,
            timestamp=datetime.fromtimestamp(event.timestamp, tz=timezone.utc),
            status=status,
            payload=event.model_dump(mode="json"),
            webhook_response=webhook_response,
        )
        return self.log_record(record)

    def log_invalid_message(
        self,
        raw_body: bytes,
        reason: str,
    ) -> asyncio.Task[None]:
        record = EventLogRecord(
            event_type="invalid",
            customer_id=None,
            zone_id=None,
            camera_id=None,
            track_id=None,
            timestamp=datetime.now(tz=timezone.utc),
            status="FAILED",
            payload={"raw_body": raw_body.decode("utf-8", errors="replace")},
            webhook_response={"error": reason},
        )
        return self.log_record(record)

    def log_record(self, record: EventLogRecord) -> asyncio.Task[None]:
        task = asyncio.create_task(self._insert_with_retry(record))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        task.add_done_callback(self._log_task_failure)
        return task

    async def wait_for(self, tasks: list[asyncio.Task[None]]) -> None:
        if not tasks:
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Failed to persist event log",
                    exc_info=(type(result), result, result.__traceback__),
                )

    async def aclose(self) -> None:
        await self.wait_for(list(self._tasks))

    async def _insert_with_retry(self, record: EventLogRecord) -> None:
        delays = (0.25, 0.5, 1.0)
        for attempt, delay in enumerate(delays, start=1):
            try:
                await self._insert(record)
                return
            except Exception:
                if attempt == len(delays):
                    raise
                logger.warning(
                    "Retrying event log insert",
                    extra={"event_type": record.event_type, "status": record.status},
                    exc_info=True,
                )
                await asyncio.sleep(delay)

    async def _insert(self, record: EventLogRecord) -> None:
        statement = text("""
            INSERT INTO analytics.events (
                event_type,
                customer_id,
                zone_id,
                camera_id,
                track_id,
                timestamp,
                status,
                payload,
                webhook_response
            )
            VALUES (
                :event_type,
                CAST(:customer_id AS UUID),
                CAST(:zone_id AS UUID),
                CAST(:camera_id AS UUID),
                :track_id,
                :timestamp,
                :status,
                CAST(:payload AS JSONB),
                CAST(:webhook_response AS JSONB)
            )
            """)

        async with self._session_factory() as session:
            await session.execute(
                statement,
                {
                    "event_type": record.event_type,
                    "customer_id": record.customer_id,
                    "zone_id": record.zone_id,
                    "camera_id": record.camera_id,
                    "track_id": record.track_id,
                    "timestamp": record.timestamp,
                    "status": record.status,
                    "payload": json.dumps(record.payload, default=str),
                    "webhook_response": (
                        json.dumps(record.webhook_response, default=str)
                        if record.webhook_response is not None
                        else None
                    ),
                },
            )
            await session.commit()

    def _log_task_failure(self, task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return

        exception = task.exception()
        if exception is None:
            return

        logger.error(
            "Failed to persist event log",
            exc_info=(type(exception), exception, exception.__traceback__),
        )
