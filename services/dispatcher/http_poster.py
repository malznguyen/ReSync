"""
Module: http_poster
Service: dispatcher
Purpose: Send signed async webhook POST requests with retryable result metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from services.ai_worker.schemas import WebhookEvent
from services.dispatcher.models import WebhookConfig
from services.dispatcher.signature import json_payload_bytes, sign_payload

MAX_RESPONSE_BODY_CHARS = 4096


@dataclass(frozen=True)
class PostResult:
    ok: bool
    retryable: bool
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None

    def to_log_response(
        self,
        webhook: WebhookConfig,
        attempt: int,
        next_delay_seconds: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "webhook_id": webhook.webhook_id,
            "attempt": attempt,
            "ok": self.ok,
            "retryable": self.retryable,
        }
        if self.status_code is not None:
            payload["status_code"] = self.status_code
        if self.response_body is not None:
            payload["body"] = self.response_body
        if self.error is not None:
            payload["error"] = self.error
        if next_delay_seconds is not None:
            payload["next_delay_seconds"] = next_delay_seconds
        return payload


class WebhookPoster:
    """Post signed event payloads to restaurant webhook endpoints."""

    def __init__(
        self,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=self._timeout)

    async def post(self, webhook: WebhookConfig, event: WebhookEvent) -> PostResult:
        payload = event.model_dump(mode="json")
        body = json_payload_bytes(payload)
        signature = sign_payload(body, webhook.secret)

        try:
            response = await self._client.post(
                webhook.url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            return PostResult(ok=False, retryable=True, error=str(exc) or "timeout")
        except httpx.RequestError as exc:
            return PostResult(ok=False, retryable=True, error=str(exc))

        response_body = response.text[:MAX_RESPONSE_BODY_CHARS]
        return PostResult(
            ok=200 <= response.status_code < 300,
            retryable=response.status_code >= 500,
            status_code=response.status_code,
            response_body=response_body,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
