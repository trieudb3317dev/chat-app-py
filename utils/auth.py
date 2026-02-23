from fastapi import Request, HTTPException
from services.user_service import verify_token


def auth_required(request: Request):
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
