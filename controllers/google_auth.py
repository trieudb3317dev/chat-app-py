# backend example (FastAPI)
import os, secrets, base64, hashlib
from fastapi import FastAPI, Request, Response, APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, PlainTextResponse
import httpx
import logging
import json
from entities.user import User
from entities import schemas as s
import os, bcrypt
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import get_db, init_db
from services.mailer_service import send_welcome_email_with_google, send_reset_password_email

router = APIRouter(prefix="/api/v1", tags=["google_auth"])


@router.on_event("startup")
def on_startup():
    # create tables if they don't exist (convenience)
    init_db()


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI"
)  # e.g. http://localhost:8000/api/v1/auth/google/callback
FRONTEND_CALLBACK = os.getenv(
    "FRONTEND_OAUTH_CALLBACK", "http://localhost:3000/auth-callback"
)

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
    raise Exception(
        "Missing Google OAuth config in environment variables. Please set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI."
    )

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"


# simple in-memory store for code_verifier keyed by state (use Redis or DB in prod)
_pkce_store: dict[str, str] = {}


def make_pkce_pair():
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    )
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return code_verifier, code_challenge


@router.get("/login/google")
async def login_google():
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = make_pkce_pair()
    _pkce_store[state] = code_verifier  # store; set expiry in production

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    from urllib.parse import urlencode

    auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"

    # Log values to help debug redirect_uri_mismatch issues
    logging.info("Generating Google auth URL; redirect_uri=%s", GOOGLE_REDIRECT_URI)
    logging.info("Auth URL: %s", auth_url)

    return {"url": auth_url}


# NOTE: The previous simple /auth/callback exchanged tokens without PKCE and caused
# "Missing code verifier" errors when the auth request included a code_challenge.
# Keep only the PKCE-aware callback below (`/auth/google/callback`) which uses the
# server-side stored code_verifier matched by `state`.


@router.get("/auth/callback")
async def google_callback(
    request: Request, response: Response, db: Session = Depends(get_db)
):  # sourcery skip: low-code-quality
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        return PlainTextResponse("Missing code or state", status_code=400)
    # retrieve code_verifier
    code_verifier = _pkce_store.pop(state, None)
    print(
        "Retrieved code_verifier:", code_verifier
    )  # log retrieved code_verifier for debug
    if not code_verifier:
        # state not found → invalid or expired
        return PlainTextResponse("Invalid state", status_code=400)

    # exchange code -> tokens
    token_url = "https://oauth2.googleapis.com/token"
    async with httpx.AsyncClient() as client:
        try:
            token_resp = await client.post(
                token_url,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            token_data = token_resp.json()
            print("Token response:", token_data)  # log full token response for debug

            id_token = token_data.get("id_token")
            access_token = token_data.get("access_token")

            email = None
            name = None
            picture = None

            if id_token:
                try:
                    payload_b64 = id_token.split(".")[1]
                    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
                    decoded = base64.urlsafe_b64decode(padded).decode()
                    try:
                        payload_json = json.loads(decoded)
                    except Exception:
                        payload_json = {"raw": decoded}

                    print("Decoded ID token payload:", payload_json)
                    email = payload_json.get("email")
                    name = payload_json.get("name")
                    picture = payload_json.get("picture")

                    username = email.split("@")[0] if email else None
                    if not username:
                        raise HTTPException(
                            status_code=400, detail="Email is required to create user"
                        )
                        
                    password = username

                    # TODO: find or create user in your DB using email
                    if (
                        existing_user := db.query(User)
                        .filter(User.username == username)
                        .first()
                    ):
                        raise HTTPException(
                            status_code=400, detail="Username already exists"
                        )

                    # Hash the password before storing it (for security)
                    # Use bcrypt to hash the password (includes salt)
                    salt = bcrypt.gensalt()  # generate a random salt
                    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
                    # store as utf-8 string so DB String column can hold it
                    hashed_password_str = hashed_password.decode("utf-8")

                    db_user = User(
                        username=username,
                        email=email,
                        password=hashed_password_str,
                        avatar_url=picture,
                    )
                    print(
                        f"[debug] creating user: {db_user.username}, email: {db_user.email}"
                    )
                    db.add(db_user)
                    db.commit()
                    db.refresh(db_user)
                    
                    send_welcome_email_with_google(db_user.email, db_user.username)

                except Exception as e:
                    print("Failed to decode id_token:", e)

            # Fallback to userinfo endpoint if needed
            if not email and access_token:
                profile_resp = await client.get(
                    GOOGLE_USERINFO_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                profile = profile_resp.json()
                print("Userinfo response:", profile)
                email = email or profile.get("email")
                name = name or profile.get("name")
                picture = picture or profile.get("picture")

            return RedirectResponse(
                f"{FRONTEND_CALLBACK}?status=ok"
            )
        except Exception as e:
            # log full exception for debug
            print("token exchange failed", e)
            return PlainTextResponse("Token exchange failed", status_code=500)

    if token_json.get("error"):
        # log token_json details
        print("token error:", token_json)
        return PlainTextResponse(
            "Token error: "
            + str(token_json.get("error_description") or token_json.get("error")),
            status_code=400,
        )

    access_token = token_json.get("access_token")
    id_token = token_json.get("id_token")

    # fetch userinfo
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile = profile_resp.json()

    # TODO: find or create user in your DB using profile["email"]
    # session_token = create_session_for_user(user)
    # response.set_cookie("session", session_token, httponly=True, secure=False)  # secure=True in prod

    # redirect to frontend callback page (it will postMessage to opener and close popup)
    redirect_to = f"{FRONTEND_CALLBACK}?status=ok"
    return RedirectResponse(redirect_to)


@router.get("/profile", response_class=PlainTextResponse)
def profile(request: Request):
    email = request.query_params.get("email")
    name = request.query_params.get("name")
    if not email:
        return PlainTextResponse("Missing email in profile", status_code=400)
    return {"email": email, "name": name}
