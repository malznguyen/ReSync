"""
Module: models
Service: dispatcher
Purpose: Define small data containers shared by dispatcher components.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WebhookConfig:
    webhook_id: str
    url: str
    secret: str


@dataclass(frozen=True)
class DispatchOutcome:
    delivered: bool
    failed_deliveries: list[dict[str, Any]] = field(default_factory=list)
    log_tasks: list[asyncio.Task[None]] = field(default_factory=list)
