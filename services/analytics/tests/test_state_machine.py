"""
Module: test_state_machine
Service: analytics
Purpose: Verify time-based seated and hand-raise state transitions.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.ai_worker.schemas import Track, TrackOutput, TrackState
from services.analytics.state_machine import TrackStateMachine
from services.analytics.zone_mapper import ZoneMatch


@dataclass
class FakeStateStore:
    state: TrackState | None = None

    def get(self, track_id: str) -> TrackState | None:
        return self.state if self.state and self.state.track_id == track_id else None


def test_seated_event_fires_after_same_zone_time_delta() -> None:
    store = FakeStateStore()
    machine = _machine(store)
    track = _track(hand_raised=False)
    zone = _zone()

    first = machine.evaluate(_output(100.0, track), track, zone)
    store.state = first.state
    assert first.events == []
    assert first.state.state == "STANDING"

    almost = machine.evaluate(_output(103.0, track), track, zone)
    store.state = almost.state
    assert almost.events == []
    assert almost.state.state == "STANDING"

    seated = machine.evaluate(_output(103.1, track), track, zone)

    assert [event.event_type for event in seated.events] == ["customer_seated"]
    assert seated.state.is_seated is True
    assert seated.state.state == "SEATED"
    assert seated.state.seated_at == 103.1


def test_hand_raise_does_not_fire_until_track_is_seated() -> None:
    store = FakeStateStore(
        TrackState(
            track_id="track-1",
            camera_id="camera-1",
            current_zone_id="zone-1",
            zone_entered_at=199.0,
            is_seated=False,
            last_seen_at=199.0,
            state="STANDING",
        )
    )
    machine = _machine(store)
    track = _track(hand_raised=True)

    result = machine.evaluate(_output(200.0, track), track, _zone())

    assert result.events == []
    assert result.state.state == "STANDING"
    assert result.state.hand_raise_started_at is None


def test_hand_raise_event_requires_duration_and_honors_cooldown() -> None:
    store = FakeStateStore(
        TrackState(
            track_id="track-1",
            camera_id="camera-1",
            current_zone_id="zone-1",
            zone_entered_at=90.0,
            is_seated=True,
            seated_at=93.1,
            hand_raise_started_at=100.0,
            last_seen_at=100.0,
            state="SEATED",
        )
    )
    machine = _machine(store)
    track = _track(hand_raised=True)
    zone = _zone()

    fired = machine.evaluate(_output(101.6, track), track, zone)
    store.state = fired.state
    cooldown = machine.evaluate(_output(105.0, track), track, zone)

    assert [event.event_type for event in fired.events] == ["hand_raise"]
    assert fired.state.state == "HAND_RAISING"
    assert fired.state.last_hand_raise_fired_at == 101.6
    assert cooldown.events == []
    assert cooldown.state.state == "HAND_RAISING"


def _machine(store: FakeStateStore) -> TrackStateMachine:
    return TrackStateMachine(
        store=store,
        seated_threshold_seconds=3.0,
        hand_raise_threshold_seconds=1.5,
        hand_raise_cooldown_seconds=10.0,
    )


def _output(timestamp: float, track: Track) -> TrackOutput:
    return TrackOutput(
        frame_id=f"frame-{timestamp}",
        timestamp=timestamp,
        camera_id="camera-1",
        tracks=[track],
    )


def _track(hand_raised: bool) -> Track:
    keypoints = [(0.1, 0.1, 0.9)] * 17
    keypoints[5] = (0.3, 0.5, 0.9)
    keypoints[6] = (0.7, 0.5, 0.9)
    keypoints[9] = (0.3, 0.44 if hand_raised else 0.7, 0.9)
    keypoints[10] = (0.7, 0.7, 0.9)
    keypoints[11] = (0.3, 0.8, 0.9)
    keypoints[12] = (0.7, 0.8, 0.9)
    return Track(
        track_id="track-1",
        bbox=(0.2, 0.2, 0.5, 0.6),
        keypoints=keypoints,
        confidence=0.9,
    )


def _zone() -> ZoneMatch:
    return ZoneMatch(zone_id="zone-1", camera_id="camera-1", zone_name="Table 1")
