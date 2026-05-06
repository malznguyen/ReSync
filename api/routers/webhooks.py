"""
Module: webhooks
Service: api
Purpose: Manage webhook destination configuration for event dispatch.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.security import get_current_subject
from api.db.session import get_session
from api.models import Webhook
from api.schemas import WebhookCreate, WebhookResponse, WebhookUpdate

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
    dependencies=[Depends(get_current_subject)],
)


@router.get(
    "",
    response_model=list[WebhookResponse],
    summary="List webhooks",
    description="Return configured webhook destinations without exposing stored secrets.",
)
def list_webhooks(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=500, examples=[100])] = 100,
    offset: Annotated[int, Query(ge=0, examples=[0])] = 0,
) -> list[Webhook]:
    statement = (
        select(Webhook).order_by(Webhook.created_at.desc()).limit(limit).offset(offset)
    )
    return list(session.scalars(statement).all())


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook",
    description=(
        "Create a webhook destination. When test_on_create is true, the URL "
        "is pinged with a 3-second timeout before saving."
    ),
)
def create_webhook(
    payload: WebhookCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Webhook:
    if payload.test_on_create:
        _ping_webhook_url(payload.url)

    webhook = Webhook(url=payload.url, secret=payload.secret, active=payload.active)
    session.add(webhook)
    session.commit()
    session.refresh(webhook)
    return webhook


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update a webhook",
    description="Update a webhook destination URL, secret, or active state.",
)
def update_webhook(
    webhook_id: UUID,
    payload: WebhookUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> Webhook:
    webhook = session.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(webhook, field, value)

    session.commit()
    session.refresh(webhook)
    return webhook


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
    description="Delete a webhook destination.",
)
def delete_webhook(
    webhook_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    webhook = session.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    session.delete(webhook)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _ping_webhook_url(url: str) -> None:
    try:
        response = httpx.get(url, timeout=3.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook URL test failed: {exc}",
        ) from exc
