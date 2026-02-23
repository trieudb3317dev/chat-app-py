from fastapi import APIRouter, Depends, Response, Request, HTTPException
from sqlalchemy.orm import Session
import os, jwt

from database import get_db, init_db
from entities import schemas as s
from services import user_service
from utils.auth import get_current_user_id, auth_required
from utils.limit import rate_limit

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.on_event("startup")
def on_startup():
    # create tables if they don't exist (convenience)
    init_db()


def get_user_or_404(db: Session, user_id: int):
    # helper still available if needed by other endpoints
    return user_service.get_profile(db, user_id)


@router.post("/users/register", response_model=s.MessageOut)
def create_user(
    user: s.UserCreate,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit(max_requests=5, window_seconds=60)),
):
    """Create a new user and return a simple message on success or an HTTP error on failure."""
    return user_service.create_user(db, user)


@router.post(
    "/users/login",
    response_model=s.MessageOut,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
def login_user(
    user: s.UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate a user and return a simple message on success or an HTTP error on failure.

    Note: `response` must be a FastAPI Response object (not a dependency) so `set_cookie` works.
    """
    # pass request host so the service can set cookie domain explicitly (helps clients like Postman)
    host = request.url.hostname
    # apply rate limit (per-IP per-endpoint)
    # we call the dependency inline to keep response signature unchanged
    # However the dependency has already been injected via decorator below
    return user_service.login_user(db, user, response, domain=host)


@router.post("/users/logout", response_model=s.MessageOut)
def logout_user(response: Response):
    """Logout a user by clearing the authentication cookies."""
    return user_service.logout_user(response)


@router.get(
    "/users/me", response_model=s.UserOut, dependencies=[Depends(auth_required)]
)
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Return the profile of the currently authenticated user.

    The user id is retrieved from the `access_token` cookie set at login.
    """
    userId = get_current_user_id(request)
    return user_service.get_profile(db, user_id=userId)


@router.get("/users/{user_id}", response_model=s.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a user by ID. Returns 404 if not found."""
    return get_user_or_404(db, user_id)


@router.put(
    "/users/profile", response_model=s.MessageOut, dependencies=[Depends(auth_required)]
)
def update_current_user(
    profile_data: s.UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit(max_requests=10, window_seconds=60)),
):
    """Update the profile of the currently authenticated user.

    The user id is retrieved from the `access_token` cookie set at login.
    """
    userId = get_current_user_id(request)
    return user_service.update_profile(
        db, user_id=userId, profile_data=profile_data.dict(exclude_unset=True)
    )


@router.post("/users/refresh-token", response_model=s.MessageOut)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Refresh the access token using the refresh token cookie.

    The user id is retrieved from the `refresh_token` cookie. If valid, a new access token is generated and set in the cookies.
    """
    # pass request host so the service can set cookie domain explicitly (helps clients like Postman)
    host = request.url.hostname
    return user_service.refresh_access_token(
        db, request.cookies.get("refresh_token"), response, domain=host
    )


@router.post("/users/{user_id}/reset-password", response_model=s.MessageOut)
def reset_password(user_id: int, db: Session = Depends(get_db)):
    """Trigger a password reset for the user with the given ID.

    This is a placeholder implementation. In a real application, this would generate a password reset token and send an email to the user.
    """
    return user_service.reset_password(db, user_id)


@router.post("/users/{user_id}/change-password", response_model=s.MessageOut)
def change_password(user_id: int, new_password: str, db: Session = Depends(get_db)):
    """Change the password for the user with the given ID.

    This is a placeholder implementation. In a real application, this would require authentication and verification of the old password or a reset token.
    """
    return user_service.change_password(db, user_id, new_password)


# @router.post("/posts")
# def create_post(user_id: int, title: str, content: str = "", db: Session = Depends(get_db)):
#     return db_service.create_post(db, user_id, title, content)


# @router.post("/items")
# def create_item(name: str, db: Session = Depends(get_db)):
#     return db_service.create_item(db, name)


# @router.post("/users/{user_id}/items/{item_id}")
# def attach_item_to_user(user_id: int, item_id: int, db: Session = Depends(get_db)):
#     user = db_service.attach_item_to_user(db, user_id, item_id)
#     return {"user_id": user.id, "item_ids": [i.id for i in user.items]}


# @router.get("/users/{user_id}/full", response_model=s.UserOut)
# def get_user_with_relations(user_id: int, db: Session = Depends(get_db)):
#     return db_service.get_user_with_relations(db, user_id)
