from fastapi import Request, HTTPException, Depends
from services.user_service import verify_token
from entities.user import User
from database import get_db
from sqlalchemy.orm import Session


def auth_required(request: Request, db: Session = Depends(get_db)):
    """Dependency to require authentication on a route.

    Usage:
      - as a dependency in a route: dependencies=[Depends(auth_required)]
      - or to get the user id: user_id = Depends(auth_required)
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # activated user_id in request.state for access in route handlers
    # `get_db()` is a FastAPI dependency that yields a Session; here we
    # accept `db: Session = Depends(get_db)` so we have a real Session
    # instance (not the generator object returned when calling get_db()).
    is_verified = (
        db.query(User).filter(User.id == user_id, User.is_verified == True).first()
    )
    print(f"auth_required: user_id={user_id}, is_verified={is_verified}")
    if not is_verified:
        raise HTTPException(status_code=403, detail="Account not verified")

    # Attach user_id to request state for access in route handlers
    request.state.user_id = user_id
    return user_id


def get_current_user_id(request: Request) -> int:
    """Helper to retrieve current user's id from request.state (set by auth_required).

    If request.state.user_id is missing, this will raise HTTPException.
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user_id