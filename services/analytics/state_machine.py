"""
Module: state_machine
Service: analytics
Purpose: Apply per-track state transitions and validated event rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import uuid4

from services.ai_worker.schemas import Track, TrackOutput, TrackState, WebhookEvent
from services.analytics.detectors.hand_raise import is_hand_raised_pose
from services.analytics.detectors.seated import stayed_in_zone_long_enough
from services.analytics.zone_mapper import ZoneMatch


class TrackStateStore(Protocol):
    def get(self, track_id: str) -> TrackState | None: ...


@dataclass(frozen=True)
class StateTransition:
    state: TrackState
    events: list[WebhookEvent]


class TrackStateMachine:
    """Evaluate one track against zone and posture rules."""

    def __init__(
        self,
        store: TrackStateStore,
        seated_threshold_seconds: float,
        hand_raise_threshold_seconds: float,
        hand_raise_cooldown_seconds: float,
    ) -> None:
        self._store = store
        self._seated_threshold_seconds = seated_threshold_seconds
        self._hand_raise_threshold_seconds = hand_raise_threshold_seconds
        self._hand_raise_cooldown_seconds = hand_raise_cooldown_seconds

    def evaluate(
        self,
        output: TrackOutput,
        track: Track,
        zone_match: ZoneMatch | None,
    ) -> StateTransition:
        now = output.timestamp
        state = self._load_state(track.track_id, output.camera_id, now)
        state.last_seen_at = now
        events: list[WebhookEvent] = []

        if zone_match is None:
            _mark_standing(state, current_zone_id=None, entered_at=None)
            return StateTransition(state=state, events=events)

        if state.current_zone_id != zone_match.zone_id:
            _mark_standing(
                state,
                current_zone_id=zone_match.zone_id,
                entered_at=now,
            )
        elif state.zone_entered_at is None:
            state.zone_entered_at = now

        if not state.is_seated and stayed_in_zone_long_enough(
            state.zone_entered_at,
            now,
            self._seated_threshold_seconds,
        ):
            state.is_seated = True
            state.seated_at = now
            state.state = "SEATED"
            events.append(_build_event("customer_seated", output, track, zone_match))
        elif state.is_seated:
            state.state = "SEATED"
        else:
            state.state = "STANDING"

        hand_raise_event = self._evaluate_hand_raise(state, output, track, zone_match)
        if hand_raise_event is not None:
            events.append(hand_raise_event)

        return StateTransition(state=state, events=events)

    def _load_state(self, track_id: str, camera_id: str, now: float) -> TrackState:
        state = self._store.get(track_id)
        if state is None or state.camera_id != camera_id:
            return TrackState(track_id=track_id, camera_id=camera_id, last_seen_at=now)

        return state.model_copy(deep=True)

    def _evaluate_hand_raise(
        self,
        state: TrackState,
        output: TrackOutput,
        track: Track,
        zone_match: ZoneMatch,
    ) -> WebhookEvent | None:
        if not state.is_seated:
            state.hand_raise_started_at = None
            return None

        if not is_hand_raised_pose(track):
            state.hand_raise_started_at = None
            state.state = "SEATED"
            return None

        now = output.timestamp
        if state.hand_raise_started_at is None:
            state.hand_raise_started_at = now

        state.state = "HAND_RAISING"
        if now - state.hand_raise_started_at <= self._hand_raise_threshold_seconds:
            return None

        if (
            state.last_hand_raise_fired_at is not None
            and now - state.last_hand_raise_fired_at < self._hand_raise_cooldown_seconds
        ):
            return None

        state.last_hand_raise_fired_at = now
        return _build_event("hand_raise", output, track, zone_match)


def _mark_standing(
    state: TrackState,
    current_zone_id: str | None,
    entered_at: float | None,
) -> None:
    state.current_zone_id = current_zone_id
    state.zone_entered_at = entered_at
    state.is_seated = False
    state.seated_at = None
    state.hand_raise_started_at = None
    state.state = "STANDING"


def _build_event(
    event_type: Literal["hand_raise", "customer_seated"],
    output: TrackOutput,
    track: Track,
    zone_match: ZoneMatch,
) -> WebhookEvent:
    return WebhookEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        camera_id=output.camera_id,
        zone_id=zone_match.zone_id,
        zone_name=zone_match.zone_name,
        track_id=track.track_id,
        customer_id=track.customer_id,
        timestamp=output.timestamp,
        payload={
            "frame_id": output.frame_id,
            "state": "HAND_RAISING" if event_type == "hand_raise" else "SEATED",
        },
    )
