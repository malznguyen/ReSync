"""
Module: test_e2e_pipeline
Service: e2e_tests
Purpose: Validate demo.mp4 through MediaMTX, control API setup, analytics, and webhooks.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

logger = logging.getLogger(__name__)

REQUIRED_EVENTS = {"hand_raise", "customer_seated"}


@dataclass(frozen=True)
class E2ESettings:
    api_base_url: str
    api_username: str
    api_password: str
    demo_video_path: Path
    ffmpeg_path: str
    ffmpeg_push_url: str
    camera_rtsp_url: str
    webhook_url: str
    webhook_secret: str
    wait_seconds: float
    poll_seconds: float

    @classmethod
    def from_env(cls) -> "E2ESettings":
        repo_root = Path(__file__).resolve().parents[1]
        api_password = os.getenv("E2E_API_PASSWORD") or os.getenv(
            "API_ADMIN_PASSWORD",
            "",
        )
        webhook_secret = os.getenv("E2E_TEST_WEBHOOK_SECRET") or os.getenv(
            "TEST_WEBHOOK_SECRET",
            "",
        )
        settings = cls(
            api_base_url=os.getenv(
                "E2E_API_BASE_URL",
                "http://localhost:8000",
            ).rstrip("/"),
            api_username=os.getenv("E2E_API_USERNAME")
            or os.getenv("API_ADMIN_USERNAME", "admin"),
            api_password=api_password,
            demo_video_path=Path(
                os.getenv("E2E_DEMO_VIDEO_PATH", str(repo_root / "demo.mp4"))
            ),
            ffmpeg_path=os.getenv("E2E_FFMPEG_PATH", "ffmpeg"),
            ffmpeg_push_url=os.getenv(
                "E2E_FFMPEG_PUSH_URL",
                "rtsp://localhost:8554/test",
            ),
            # ffmpeg publishes from the host. Ingestion reads from inside Docker.
            camera_rtsp_url=os.getenv(
                "E2E_CAMERA_RTSP_URL",
                "rtsp://mediamtx:8554/test",
            ),
            webhook_url=os.getenv(
                "E2E_WEBHOOK_URL",
                "http://host.docker.internal:8001/webhook",
            ),
            webhook_secret=webhook_secret,
            wait_seconds=_env_float("E2E_WAIT_SECONDS", 120.0),
            poll_seconds=_env_float("E2E_POLL_SECONDS", 2.0),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.api_password == "":
            pytest.fail("Set E2E_API_PASSWORD or API_ADMIN_PASSWORD for API login.")
        if self.webhook_secret == "":
            pytest.fail(
                "Set E2E_TEST_WEBHOOK_SECRET or TEST_WEBHOOK_SECRET for HMAC validation."
            )
        if len(self.webhook_secret) < 16:
            pytest.fail("The test webhook secret must be at least 16 characters.")
        if not self.demo_video_path.exists():
            pytest.fail(f"demo video not found: {self.demo_video_path}")


@pytest.mark.e2e
def test_demo_video_pipeline_emits_mvp_events() -> None:
    settings = E2ESettings.from_env()
    started_at = datetime.now(timezone.utc)

    with run_ffmpeg(settings) as ffmpeg_process:
        with httpx.Client(base_url=settings.api_base_url, timeout=10.0) as client:
            token = issue_token(client, settings)
            headers = {"Authorization": f"Bearer {token}"}
            camera: dict[str, object] | None = None
            webhook: dict[str, object] | None = None
            try:
                camera = create_camera(client, headers, settings)
                create_whole_frame_zone(client, headers, str(camera["id"]))
                webhook = create_webhook(client, headers, settings)
                wait_for_events(
                    client=client,
                    headers=headers,
                    camera_id=str(camera["id"]),
                    started_at=started_at,
                    settings=settings,
                    ffmpeg_process=ffmpeg_process,
                )
            finally:
                if webhook is not None:
                    delete_resource(client, headers, f"/webhooks/{webhook['id']}")
                if camera is not None:
                    delete_resource(client, headers, f"/cameras/{camera['id']}")


@contextmanager
def run_ffmpeg(settings: E2ESettings) -> Iterator[subprocess.Popen[bytes]]:
    command = [
        settings.ffmpeg_path,
        "-re",
        "-i",
        str(settings.demo_video_path),
        "-f",
        "rtsp",
        settings.ffmpeg_push_url,
    ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        logger.error("ffmpeg executable not found: %s", exc)
        pytest.fail(f"ffmpeg not found: {settings.ffmpeg_path}")

    time.sleep(2.0)
    if process.poll() is not None:
        pytest.fail(
            "ffmpeg exited before the pipeline test started. "
            "Confirm MediaMTX is running and rtsp://localhost:8554/test is writable."
        )

    try:
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)


def issue_token(client: httpx.Client, settings: E2ESettings) -> str:
    response = client.post(
        "/auth/token",
        data={"username": settings.api_username, "password": settings.api_password},
    )
    assert_ok(response, "issue API token")
    payload = response.json()
    token = payload.get("access_token")
    if not isinstance(token, str) or token == "":
        pytest.fail("API token response did not contain access_token.")
    return token


def create_camera(
    client: httpx.Client,
    headers: dict[str, str],
    settings: E2ESettings,
) -> dict[str, object]:
    response = client.post(
        "/cameras",
        headers=headers,
        json={
            "name": "Phase 9 E2E Camera",
            "rtsp_url": settings.camera_rtsp_url,
            "status": "active",
        },
    )
    assert_ok(response, "create E2E camera")
    return response.json()


def create_whole_frame_zone(
    client: httpx.Client,
    headers: dict[str, str],
    camera_id: str,
) -> dict[str, object]:
    response = client.post(
        "/zones",
        headers=headers,
        json={
            "camera_id": camera_id,
            "name": "Phase 9 Whole Frame Dining Zone",
            "polygon": [
                [0.0, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.0, 1.0],
                [0.0, 0.0],
            ],
            "active": True,
        },
    )
    assert_ok(response, "create whole-frame zone")
    return response.json()


def create_webhook(
    client: httpx.Client,
    headers: dict[str, str],
    settings: E2ESettings,
) -> dict[str, object]:
    response = client.post(
        "/webhooks",
        headers=headers,
        json={
            "url": settings.webhook_url,
            "secret": settings.webhook_secret,
            "active": True,
            "test_on_create": False,
        },
    )
    assert_ok(response, "create mock webhook")
    return response.json()


def wait_for_events(
    client: httpx.Client,
    headers: dict[str, str],
    camera_id: str,
    started_at: datetime,
    settings: E2ESettings,
    ffmpeg_process: subprocess.Popen[bytes],
) -> None:
    deadline = time.monotonic() + settings.wait_seconds
    found: set[str] = set()
    seen_events: list[str] = []

    while time.monotonic() < deadline:
        response = client.get(
            "/analytics/events",
            headers=headers,
            params={
                "start_at": started_at.isoformat(),
                "limit": 500,
            },
        )
        assert_ok(response, "list analytics events")

        items = response.json().get("items", [])
        if not isinstance(items, list):
            pytest.fail("analytics events response did not contain an items list.")

        for item in items:
            if not isinstance(item, dict):
                continue
            event_type = str(item.get("event_type", "")).lower()
            event_camera_id = str(item.get("camera_id", ""))
            if event_type in REQUIRED_EVENTS:
                seen_events.append(f"{event_type}@{event_camera_id}")
            if event_camera_id == camera_id and event_type in REQUIRED_EVENTS:
                found.add(event_type)

        if REQUIRED_EVENTS.issubset(found):
            return

        if ffmpeg_process.poll() not in (None, 0):
            pytest.fail("ffmpeg failed while the E2E test was waiting for events.")

        time.sleep(settings.poll_seconds)

    missing = ", ".join(sorted(REQUIRED_EVENTS - found))
    seen_summary = ", ".join(sorted(set(seen_events))) or "none"
    pytest.fail(
        f"Timed out waiting for required events for camera {camera_id}. "
        f"Missing: {missing}. Seen required event types by camera: {seen_summary}. "
        "If events appear under another camera ID, restart ai_worker and analytics "
        "with CAMERA_ID set to the API-created camera ID for this run."
    )


def delete_resource(
    client: httpx.Client,
    headers: dict[str, str],
    path: str,
) -> None:
    response = client.delete(path, headers=headers)
    if response.status_code not in {204, 404}:
        logger.warning(
            "Cleanup request failed path=%s status=%s body=%s",
            path,
            response.status_code,
            response.text,
        )


def assert_ok(response: httpx.Response, action: str) -> None:
    if response.is_success:
        return
    pytest.fail(
        f"Failed to {action}: status={response.status_code} body={response.text}"
    )


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    value = float(raw_value)
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")
    return value
