"""
Module: mock_webhook
Service: e2e_tests
Purpose: Receive dispatcher webhook calls and validate HMAC-SHA256 signatures.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status

logger = logging.getLogger("phase9.mock_webhook")


def get_test_secret() -> str:
    secret = os.getenv("TEST_WEBHOOK_SECRET") or os.getenv("E2E_TEST_WEBHOOK_SECRET")
    if secret is None or secret == "":
        raise RuntimeError(
            "Set TEST_WEBHOOK_SECRET or E2E_TEST_WEBHOOK_SECRET before starting "
            "the mock webhook server."
        )
    if len(secret) < 16:
        raise RuntimeError("The test webhook secret must be at least 16 characters.")
    return secret


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_test_secret()
    logger.info("Mock webhook server ready on port 8001")
    yield


app = FastAPI(
    title="Phase 9 Mock Webhook",
    version="0.1.0",
    lifespan=lifespan,
)


@app.post("/webhook")
async def receive_webhook(request: Request) -> dict[str, bool | str]:
    body = await request.body()
    expected_signature = sign_payload(body, get_test_secret())
    received_signature = request.headers.get("X-Webhook-Signature", "")

    if not received_signature:
        logger.warning("Signature Verify Fail: missing X-Webhook-Signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing webhook signature",
        )

    if not hmac.compare_digest(received_signature, expected_signature):
        logger.warning(
            "Signature Verify Fail: expected=%s received=%s",
            expected_signature,
            received_signature,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid webhook signature",
        )

    payload = parse_json_payload(body)
    logger.info("Signature Verify Pass")
    logger.info("Webhook payload: %s", json.dumps(payload, sort_keys=True))
    return {"status": "accepted", "signature_verified": True}


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def parse_json_payload(payload_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid JSON payload",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="webhook payload must be a JSON object",
        )
    return payload


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=8001)
