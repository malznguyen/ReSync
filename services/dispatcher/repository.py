"""
Module: repository
Service: dispatcher
Purpose: Read active webhook configuration from PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.dispatcher.models import WebhookConfig


class WebhookRepository:
    """Read active webhook endpoints from the config schema."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_active_webhooks(self) -> list[WebhookConfig]:
        statement = text("""
            SELECT id::text AS webhook_id, url, secret
            FROM config.webhooks
            WHERE active = TRUE
            ORDER BY created_at ASC, id ASC
            """)

        async with self._session_factory() as session:
            result = await session.execute(statement)
            rows = result.mappings().all()

        return [
            WebhookConfig(
                webhook_id=str(row["webhook_id"]),
                url=str(row["url"]),
                secret=str(row["secret"]),
            )
            for row in rows
        ]
