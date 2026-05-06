"""
Module: signature
Service: dispatcher
Purpose: Build canonical JSON payload bytes and HMAC-SHA256 signatures.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any


def json_payload_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize payload JSON exactly once so POST body and signature match."""

    return json.dumps(
        payload,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Return the hex HMAC-SHA256 signature for payload bytes."""

    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
