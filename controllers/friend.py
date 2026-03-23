from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from entities import schemas as s
from services import friend_service
from utils.auth import auth_required, get_current_user_id
from utils.limit import rate_limit

router = APIRouter(prefix="/api/v1", tags=["friends"])


@router.post(
    "/friends/add",
    response_model=s.MessageOut,
    dependencies=[
        Depends(auth_required),
        Depends(rate_limit(max_requests=1000, window_seconds=60)),
    ],
)
def add_friend(
    friend_request: s.FriendRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Send a friend request from the current user to the specified friend_id."""
    try:
        friend_service.add_friend(db, user_id, friend_request.friend_id)
        return {"message": "Friend request sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/friends/remove",
    response_model=s.MessageOut,
    dependencies=[
        Depends(auth_required),
        Depends(rate_limit(max_requests=1000, window_seconds=60)),
    ],
)
def remove_friend(
    friend_request: s.FriendRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Remove a friend relationship with the specified friend_id."""
    try:
        friend_service.remove_friend(db, user_id, friend_request.friend_id)
        return {"message": "Friend removed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/friends/requests",
    dependencies=[
        Depends(auth_required),
        Depends(rate_limit(max_requests=1000, window_seconds=60)),
    ],
)
def list_friend_requests(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=200),
    q: str = None,
):
    """List pending friend requests for the current user."""
    result = friend_service.list_unaccepted_friend_requests(
        db, user_id, page=page, per_page=per_page, q=q
    )
    return {
        "friends": result.get("friends", []),
        "total": int(result.get("total", 0)),
        "page": int(result.get("page", page)),
        "per_page": int(result.get("per_page", per_page)),
        "next_page": result.get("next_page"),
        "prev_page": result.get("prev_page"),
    }


@router.post(
    "/friends/accept",
    response_model=s.MessageOut,
    dependencies=[
        Depends(auth_required),
        Depends(rate_limit(max_requests=1000, window_seconds=60)),
    ],
)
def accept_friend(
    friend_request: s.FriendRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Accept a friend request from the specified friend_id."""
    try:
        friend_service.accept_friend(db, user_id, friend_request.friend_id)
        return {"message": "Friend request accepted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/friends/list",
    dependencies=[
        Depends(auth_required),
        Depends(rate_limit(max_requests=1000, window_seconds=60)),
    ],
)
def list_friends(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    q: str = None,
):
    """List all friends for the current user."""
    result = friend_service.list_friends(db, user_id, page=page, per_page=per_page, q=q)
    # ensure we always return the expected structure
    return {
        "friends": result.get("friends", []),
        "total": int(result.get("total", 0)),
        "page": int(result.get("page", page)),
        "per_page": int(result.get("per_page", per_page)),
        "next_page": result.get("next_page"),
        "prev_page": result.get("prev_page"),
    }


@router.get(
    "/friends/suggestions",
    response_model=s.FriendListOut,
    dependencies=[Depends(auth_required)],
)
def list_friend_suggestions(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=200),
):
    """List friend suggestions for the current user."""
    result = friend_service.list_friend_suggestions(
        db, user_id, page=page, per_page=per_page
    )
    return {
        "friends": result.get("friends", []),
        "total": int(result.get("total", 0)),
        "page": int(result.get("page", page)),
        "per_page": int(result.get("per_page", per_page)),
        "next_page": result.get("next_page"),
        "prev_page": result.get("prev_page"),
    }


@router.get(
    "/friends/unfriended",
    response_model=s.FriendListOut,
    dependencies=[Depends(auth_required)],
)
def list_unfriended_users(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=200),
):
    """List users who are not friends with the current user."""
    result = friend_service.list_unfriended_users(
        db, user_id, page=page, per_page=per_page
    )
    return {
        "friends": result.get("friends", []),
        "total": int(result.get("total", 0)),
        "page": int(result.get("page", page)),
        "per_page": int(result.get("per_page", per_page)),
        "next_page": result.get("next_page"),
        "prev_page": result.get("prev_page"),
    }
