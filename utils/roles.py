from fastapi import Request, HTTPException, Depends
from typing import Iterable
from database import get_db
from sqlalchemy.orm import Session

from services.user_service import verify_token
from entities.user import UserAdmin


def require_role(*allowed_roles: Iterable[str]):
    """FastAPI dependency factory that ensures the current authenticated admin
    has one of the allowed roles. Usage:

      dependencies=[Depends(require_role('admin','super_admin'))]

    This dependency expects `auth_required` to have run (or it will call
    token verification itself) and relies on `get_db` for DB access.
    """

    def _dependency(request: Request, db: Session = Depends(get_db)):
        # Ensure authentication via access_token cookie
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = verify_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # load admin record
        admin = db.query(UserAdmin).filter(UserAdmin.id == user_id).first()
        if not admin:
            raise HTTPException(status_code=403, detail="Admin account not found")

        role = getattr(admin, "role", None)
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden: insufficient role")

        # attach admin info to request.state for downstream handlers if needed
        request.state.user_id = user_id
        request.state.user_role = role
        return True

    return _dependency
