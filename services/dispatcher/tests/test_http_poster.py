"""
Module: test_http_poster
Service: dispatcher
Purpose: Verify signed async HTTP POST behavior.
"""

from __future__ import annotations

import asyncio

import httpx

from services.ai_worker.schemas import WebhookEvent
from services.dispatcher.http_poster import WebhookPoster
from services.dispatcher.models import WebhookConfig
from services.dispatcher.signature import json_payload_bytes, sign_payload


def test_post_sends_exact_signed_json_body() -> None:
    asyncio.run(_assert_signed_post())


async def _assert_signed_post() -> None:
    event = _make_event()
    webhook = WebhookConfig(
        webhook_id="wh_001",
        url="https://restaurant.example/webhook",
        secret="top-secret",
    )
    captured: dict[str, str | bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        captured["signature"] = request.headers["X-Webhook-Signature"]
        captured["content_type"] = request.headers["Content-Type"]
        return httpx.Response(200, text="ok")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    poster = WebhookPoster(timeout_seconds=5.0, client=client)

    result = await poster.post(webhook, event)
    await client.aclose()

    expected_body = json_payload_bytes(event.model_dump(mode="json"))
    assert result.ok is True
    assert captured["body"] == expected_body
    assert captured["signature"] == sign_payload(expected_body, webhook.secret)
    assert captured["content_type"] == "application/json"


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
        payload={"source": "test"},
    )
