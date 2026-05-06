"""
Module: seated
Service: analytics
Purpose: Evaluate time-based seated detection windows.
"""

from __future__ import annotations


def stayed_in_zone_long_enough(
    zone_entered_at: float | None,
    now: float,
    threshold_seconds: float,
) -> bool:
    if zone_entered_at is None:
        return False
    return now - zone_entered_at > threshold_seconds
