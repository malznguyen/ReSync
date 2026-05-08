"""
Module: main
Service: api
Purpose: Assemble the FastAPI control API application.
"""

from __future__ import annotations

from fastapi import FastAPI

from api.routers import analytics, auth, cameras, system, webhooks, zones

app = FastAPI(
    title="AI Restaurant Vision Control API",
    version="0.7.0",
    description=(
        "Control API for camera, zone, webhook, and analytics access in the "
        "AI Restaurant Vision System."
    ),
)

app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(zones.router)
app.include_router(webhooks.router)
app.include_router(analytics.router)
app.include_router(system.router)


@app.get("/health", include_in_schema=False)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
