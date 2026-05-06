"""
Module: test_signature
Service: dispatcher
Purpose: Verify canonical JSON payload signing for webhook security.
"""

from __future__ import annotations

import hashlib
import hmac

from services.dispatcher.signature import json_payload_bytes, sign_payload


def test_sign_payload_uses_hmac_sha256_hex_digest() -> None:
    payload = {"event_type": "hand_raise", "track_id": "t001"}
    body = json_payload_bytes(payload)

    signature = sign_payload(body, "top-secret")

    assert (
        signature
        == hmac.new(
            b"top-secret",
            body,
            hashlib.sha256,
        ).hexdigest()
    )
