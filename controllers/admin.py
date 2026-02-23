from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from database import get_db, init_db
from entities import schemas as s
from services import admin_service as service
from utils.auth import auth_required, get_current_user_id
from utils.limit import rate_limit
from utils.roles import require_role

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.on_event("startup")
def on_startup():
    # create tables if they don't exist (convenience)
    init_db()


def get_user_or_404(db: Session, user_id: int):
    # helper still available if needed by other endpoints
    # return user_service.get_profile(db, user_id)
    pass  # not needed for admin routes but can be implemented if needed


@router.post(
    "/admin/register",
    response_model=s.MessageOut,
    dependencies=[Depends(rate_limit(max_requests=3, window_seconds=60))],
)
def create_user_admin(user: s.UserCreate, db: Session = Depends(get_db)):
    """Create a new admin user and return a simple message on success or an HTTP error on failure."""
    return service.create_user_admin(db, user)


@router.post(
    "/admin/login",
    response_model=s.MessageOut,
    dependencies=[Depends(rate_limit(max_requests=3, window_seconds=60))],
)
def login_user_admin(
    user: s.UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate an admin user and return a simple message on success or an HTTP error on failure.

    Note: `response` must be a FastAPI Response object (not a dependency) so `set_cookie` works.
    """
    # pass request host so the service can set cookie domain explicitly (helps clients like Postman)
    host = request.url.hostname
    return service.login_user_admin(db, user, response, domain=host)


@router.post("/admin/logout", response_model=s.MessageOut)
def logout_user_admin(response: Response):
    """Logout an admin user by clearing the authentication cookies."""
    return service.logout_user_admin(response)


@router.get(
    "/admin/me",
    response_model=s.UserOut,
    dependencies=[Depends(auth_required)],
)
def get_profile_admin(
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get the profile of the currently authenticated admin user."""
    userId = get_current_user_id(request)
    return service.get_profile(db, userId)


@router.put(
    "/admin/profile",
    response_model=s.MessageOut,
    dependencies=[Depends(auth_required)],
)
def update_profile_admin(
    profile_data: s.UserUpdate,
    db: Session = Depends(get_db),
    request: Request = None,
    _rl: None = Depends(rate_limit(max_requests=10, window_seconds=60)),
):
    """Update the profile of the currently authenticated admin user."""
    userId = get_current_user_id(request)
    return service.update_profile_admin(
        db, userId, profile_data.dict(exclude_unset=True)
    )


@router.post(
    "/admin/refresh-token",
    response_model=s.MessageOut,
    dependencies=[Depends(auth_required)],
)
def refresh_access_token_admin(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Refresh the access token for the currently authenticated admin user."""
    host = request.url.hostname
    return service.refresh_access_token(
        db, request.cookies.get("refresh_token"), response, domain=host
    )


@router.post(
    "/admin/reset-password",
    response_model=s.MessageOut,
    dependencies=[Depends(auth_required)],
)
def reset_password_admin(
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Request a password reset for the currently authenticated admin user."""
    userId = get_current_user_id(request)
    return service.reset_password(db, userId)


@router.post(
    "/admin/change-password",
    response_model=s.MessageOut,
    dependencies=[Depends(auth_required)],
)
def change_password_admin(
    new_password: str,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Change the password for the currently authenticated admin user."""
    userId = get_current_user_id(request)
    return service.change_password(db, userId, new_password)


@router.delete(
    "/admin/users/{user_id}",
    response_model=s.MessageOut,
    dependencies=[
        Depends(auth_required),
        Depends(require_role("admin", "super_admin")),
    ],
)
def delete_user_admin(
    user_id: int, db: Session = Depends(get_db), request: Request = None
):
    """Delete a regular user account. Only admins/super_admins are allowed."""
    # user performing the action is available via request.state.user_id if needed
    return service.delete_user_account(db, user_id)


@router.get(
    "/admin/users",
    # response_model=any,
    dependencies=[
        Depends(auth_required),
        Depends(require_role("admin", "super_admin")),
    ],
    # In the FastAPI framework, the `response_model` parameter in a route decorator specifies the
    # Pydantic model that should be used to serialize the response data returned by that route.
    # query_params={"page": int, "per_page": int},
)
def list_users_admin(db: Session = Depends(get_db), page: int = 1, per_page: int = 20):
    """List all regular users. Only admins/super_admins are allowed."""
    return service.get_all_users(db, page, per_page)