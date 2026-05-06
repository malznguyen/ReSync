"""
Module: test_openapi
Service: api
Purpose: Verify OpenAPI exposes Phase 7 security and pagination contracts.
"""

from __future__ import annotations

from api.main import app


def test_phase_7_routes_are_documented_and_protected() -> None:
    schema = app.openapi()
    expected_paths = {
        "/analytics/events",
        "/analytics/visits",
        "/auth/token",
        "/cameras",
        "/cameras/{camera_id}",
        "/webhooks",
        "/webhooks/{webhook_id}",
        "/zones",
        "/zones/{zone_id}",
    }

    assert expected_paths.issubset(schema["paths"])
    for path, path_item in schema["paths"].items():
        if path == "/auth/token":
            continue
        for method, operation in path_item.items():
            if method in {"get", "post", "put", "delete"}:
                assert operation["security"] == [{"OAuth2PasswordBearer": []}]


def test_analytics_routes_document_pagination_parameters() -> None:
    schema = app.openapi()

    for path in ("/analytics/visits", "/analytics/events"):
        parameters = {
            parameter["name"]
            for parameter in schema["paths"][path]["get"].get("parameters", [])
        }
        assert {"limit", "offset"}.issubset(parameters)
