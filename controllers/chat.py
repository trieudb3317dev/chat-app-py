from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from sqlalchemy.orm import Session
from utils.auth import auth_required, get_current_user_id

from database import get_db
from entities import schemas as s
from services import chat_service
from utils.limit import rate_limit

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.get(
    "/chats/with/{other_user_id}",
    response_model=s.ChatListOut,
    dependencies=[
        Depends(auth_required),
        Depends(rate_limit(max_requests=1000, window_seconds=60)),
    ],
)
def get_conversation_with(
    other_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    per_page: int = 20,
    q: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "asc",
):
    """Return the conversation messages between the authenticated user (sender)
    and another user identified by `other_user_id`.

    The authenticated user id is obtained from the cookie via `auth_required`.
    """
    sender_id = get_current_user_id(request)
    return chat_service.get_conversation_between_users(
        sender_id,
        other_user_id,
        page=page,
        per_page=per_page,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/chats/unread/count",
    dependencies=[
        Depends(auth_required),
        Depends(rate_limit(max_requests=1000, window_seconds=60)),
    ],
)
def count_unread_chats_for_user(request: Request):
    """Return the count of unread chat messages for the authenticated user."""
    user_id = get_current_user_id(request)
    return chat_service.count_unread_chats_for_user_and_group_by_sender(user_id)
