import contextlib
import sys, os

from datetime import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # add project root
from sqlalchemy.orm import Session
from fastapi import HTTPException, Response
from fastapi import Request
from typing import Optional

from entities.user import User
from entities import schemas as s
import os, bcrypt
import jwt
from datetime import datetime, timedelta
from services.mailer_service import send_welcome_email


def create_user(db: Session, user: s.UserCreate) -> dict:
    # Create a User instance and let the database assign the primary key
    try:
        return _extracted_from_create_user(db, user)
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e


# TODO Rename this here and in `create_user`
def _extracted_from_create_user(db, user):
    if existing_user := db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password before storing it (for security)
    # Use bcrypt to hash the password (includes salt)
    salt = bcrypt.gensalt()  # generate a random salt
    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), salt)
    # store as utf-8 string so DB String column can hold it
    hashed_password_str = hashed_password.decode("utf-8")

    db_user = User(
        username=user.username, email=user.email, password=hashed_password_str
    )
    print(f"[debug] creating user: {db_user.username}, email: {db_user.email}")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # refresh to get the generated id

    # send welcome email (optional, can be commented out if not set up)
    send_welcome_email(db_user.email, db_user.username)

    return {"message": "User created successfully"}


def login_user(
    db: Session, user: s.UserLogin, response: Response, domain: Optional[str] = None
) -> dict:
    try:
        return _extracted_from_login_user(db, user, response, domain)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e


# TODO Rename this here and in `login_user`
def _extracted_from_login_user(db, user, response, domain):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # ensure stored password is bytes for bcrypt.checkpw
    stored = db_user.password
    stored_bytes = stored.encode("utf-8") if isinstance(stored, str) else stored
    if not bcrypt.checkpw(user.password.encode("utf-8"), stored_bytes):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # use userId key for consistency with /users/me
    token_payload = {"userId": db_user.id, "username": db_user.username}
    access_token = generate_token(token_payload, response, domain=domain)
    refresh_token = generate_refresh_token(token_payload, response, domain=domain)

    return {"message": "Login successful"}


def logout_user(response: Response) -> dict:
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
        if user := db.query(User).filter(User.id == user_id).first():
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "address": user.address,
                "phone_number": user.phone_number,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e


def update_profile(db: Session, user_id: int, profile_data: dict) -> dict:
    try:
        return _extracted_from_update_profile(db, user_id, profile_data)
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e  # re-raise HTTP exceptions as they are
        raise HTTPException(status_code=400, detail=str(e)) from e


# TODO Rename this here and in `update_profile`
def _extracted_from_update_profile(db, user_id, profile_data):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only the fields that are provided in profile_data
    for key, value in profile_data.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return {"message": "Profile updated successfully"}


def refresh_access_token(
    db: Session, refresh_token: str, response: Response, domain: Optional[str] = None
) -> dict:
    user_id = verify_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token_payload = {"userId": user.id, "username": user.username}
    new_access_token = generate_token(token_payload, response, domain=domain)
    new_refresh_token = generate_refresh_token(token_payload, response, domain=domain)

    return {"message": "Access token refreshed successfully"}


def reset_password(db: Session, email: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # In a real application, generate a secure token and send a password reset link
    # For this example, we'll just send a simple notification
    send_simple_notification(
        user.email,
        "Password Reset Request",
        f"Hi {user.username}, we received a request to reset your password. If this was you, please follow the instructions to reset your password.",
    )

    return {"message": "Password reset instructions sent to email"}


def change_password(db: Session, user_id: int, new_password: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hash the new password before storing it
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), salt)
    hashed_password_str = hashed_password.decode("utf-8")

    user.password = hashed_password_str
    db.commit()
    db.refresh(user)

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


# def create_post(db: Session, user_id: int, title: str, content: str = "") -> Post:
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     post = Post(title=title, content=content, author=user)
#     db.add(post)
#     db.commit()
#     db.refresh(post)
#     return post


# def create_item(db: Session, name: str) -> Item:
#     item = Item(name=name)
#     db.add(item)
#     db.commit()
#     db.refresh(item)
#     return item


# def attach_item_to_user(db: Session, user_id: int, item_id: int):
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     item = db.query(Item).filter(Item.id == item_id).first()
#     if not item:
#         raise HTTPException(status_code=404, detail="Item not found")
#     if item not in user.items:
#         user.items.append(item)
#         db.commit()
#     return user


# def get_user_with_relations(db: Session, user_id: int):
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return {
#         "id": user.id,
#         "name": user.name,
#         "posts": [{"id": p.id, "title": p.title} for p in user.posts],
#         "items": [{"id": it.id, "name": it.name} for it in user.items],
#     }
