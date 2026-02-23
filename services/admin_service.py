import contextlib
import sys, os

from datetime import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # add project root
from sqlalchemy.orm import Session
from fastapi import HTTPException, Response
from fastapi import Request
from typing import Optional

from entities.user import UserAdmin
from entities import schemas as s
import os, bcrypt
import jwt
from datetime import datetime, timedelta
from entities.user import UserRole
from typing import Any


def create_user_admin(db: Session, user: s.UserCreate) -> dict:
    # Create a User instance and let the database assign the primary key
    try:
        return _extracted_from_create_user_admin(db, user)
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e


# TODO Rename this here and in `create_user_admin`
def _extracted_from_create_user_admin(db, user):
    if (
        existing_user := db.query(UserAdmin)
        .filter(UserAdmin.username == user.username)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password before storing it (for security)
    # Use bcrypt to hash the password (includes salt)
    salt = bcrypt.gensalt()  # generate a random salt
    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), salt)
    # store as utf-8 string so DB String column can hold it
    hashed_password_str = hashed_password.decode("utf-8")

    db_user = UserAdmin(
        username=user.username,
        email=user.email,
        password=hashed_password_str,
        role=str(user.role) or str(UserRole.ADMIN.value),  # use default role if not provided
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # refresh to get the generated id
    return {"message": "User created successfully"}


def login_user_admin(
    db: Session, user: s.UserLogin, response: Response, domain: Optional[str] = None
) -> dict:
    try:
        return _extracted_from_login_user_admin(db, user, response, domain)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e


# TODO Rename this here and in `login_user_admin`
def _extracted_from_login_user_admin(db, user, response, domain):
    db_user = db.query(UserAdmin).filter(UserAdmin.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # ensure stored password is bytes for bcrypt.checkpw
    stored = db_user.password
    stored_bytes = stored.encode("utf-8") if isinstance(stored, str) else stored
    if not bcrypt.checkpw(user.password.encode("utf-8"), stored_bytes):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # use userId key for consistency with /users/me
    token_payload = {"userId": db_user.id, "username": db_user.username}
    generate_token(token_payload, response, domain=domain)
    generate_refresh_token(token_payload, response, domain=domain)

    return {"message": "Login successful"}


def logout_user_admin(response: Response) -> dict:
    # Clear the cookies by setting them with an expired date
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Logout successful"}


def verify_token(token: str) -> Optional[int]:
    jwt_secret = os.getenv("SECRET_KEY", "dev-secret")
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        user_id = payload.get("userId")  # use userId key as set in login_user
        return None if user_id is None else user_id
    except jwt.ExpiredSignatureError:
        return None  # token expired
    except Exception:
        return None  # invalid token


def get_profile(db: Session, user_id: int) -> dict:
    try:
        if user := db.query(UserAdmin).filter(UserAdmin.id == user_id).first():
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "address": user.address,
                "phone_number": user.phone_number,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                "role": user.role if hasattr(user, "role") else None,
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e

def update_profile_admin(db: Session, user_id: int, profile_data: dict) -> dict:
    try:
        user = db.query(UserAdmin).filter(UserAdmin.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update only the fields that are provided in profile_data
        for key, value in profile_data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        db.commit()
        return {"message": "Profile updated successfully"}
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e

def refresh_access_token(
    db: Session, refresh_token: Optional[str], response: Response, domain: Optional[str] = None
) -> dict:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    user_id = verify_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(UserAdmin).filter(UserAdmin.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found") 

    # Generate new access token
    token_payload = {"userId": user.id, "username": user.username}
    generate_token(token_payload, response, domain=domain)
    return {"message": "Access token refreshed successfully"}

def reset_password(db: Session, user_id: int) -> dict:
    # Placeholder implementation for password reset
    # In a real application, this would generate a reset token and send an email to the user
    return {"message": f"Password reset requested for user ID {user_id}"}

def change_password(db: Session, user_id: int, new_password: str) -> dict:
    user = db.query(UserAdmin).filter(UserAdmin.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hash the new password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), salt)
    user.password = hashed_password.decode("utf-8")  # store as string

    db.commit()
    return {"message": "Password changed successfully"}


def generate_token(
    payload: dict, response: Response, domain: Optional[str] = None
) -> str:
    jwt_secret = os.getenv("SECRET_KEY", "dev-secret")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)
    token = jwt.encode(
        {**payload, "exp": exp, "iat": now}, jwt_secret, algorithm="HS256"
    )
    # use secure cookies only in production (HTTPS). For local testing over HTTP set secure=False
    secure_flag = os.getenv("ENV", "development") == "production"
    # set cookie with path and max_age so browsers accept it predictably
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=secure_flag,
        samesite="None",  # allow cross-site cookies for testing; set to "Lax" or "Strict" in production
        path="/",
        domain=domain,
        max_age=3600,  # 1 hour in seconds
    )
    # debug: print Set-Cookie header that was added to the response
    with contextlib.suppress(Exception):
        print("[debug] set-cookie header:", response.headers.get("set-cookie"))
    return token


def generate_refresh_token(
    payload: dict, response: Response, domain: Optional[str] = None
) -> str:
    jwt_secret = os.getenv("SECRET_KEY", "dev-secret")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=7)  # refresh token valid for 7 days
    token = jwt.encode(
        {**payload, "exp": exp, "iat": now}, jwt_secret, algorithm="HS256"
    )
    # use secure cookies only in production (HTTPS). For local testing over HTTP set secure=False
    secure_flag = os.getenv("ENV", "development") == "production"
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=secure_flag,
        samesite="None",  # allow cross-site cookies for testing; set to "Lax" or "Strict" in production
        path="/",
        domain=domain,
        max_age=7 * 24 * 3600,
    )
    with contextlib.suppress(Exception):
        print("[debug] set-refresh-cookie header:", response.headers.get("set-cookie"))
    return token


def delete_user_account(db: Session, target_user_id: int) -> dict:
    """Delete a regular user account by id. This is intended to be called
    by an admin after role checks via dependency have passed.
    """
    # import local User model to avoid circular imports at module load time
    from entities.user import User

    try:
        user = db.query(User).filter(User.id == target_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = True  # soft delete by deactivating the account
        # db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e)) from e

def get_all_users(db: Session, page: int = 1, per_page: int = 20) -> any:
    """Get a list of all regular users. This is intended to be called
    by an admin after role checks via dependency have passed.
    """
    from entities.user import User
    from utils.pagination import paginate

    try:
        
        users = db.query(User).filter(User.is_active == False).all()
        if not users:
            raise HTTPException(status_code=404, detail="No active users found")
        print(f"[debug] Retrieved {len(users)} active users from the database")
        return paginate(users, page, per_page)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e)) from e