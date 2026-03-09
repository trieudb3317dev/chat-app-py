import contextlib
import os
import sys
from typing import Optional

# Allow insecure OAuth2 transport for local development only. Do NOT enable this in
# production. Controlled by the ENV environment variable (default: development).
ENV = os.environ.get("ENV", "development")
if ENV != "production":
    # Force the flag so oauthlib accepts http:// redirect URIs during development.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import APIRouter, Request
from database import init_db

from google_auth_oauthlib.flow import Flow
from google.oauth2 import credentials
from googleapiclient.discovery import build

sys.path.append(os.path.dirname(__file__))  # Ensure current directory is in path

router = APIRouter(prefix="/api/v1", tags=["google_auth"])


@router.on_event("startup")
def on_startup():
    # create tables if they don't exist (convenience)
    init_db()


# Load credentials from environment variables or a JSON file
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
# Allow overriding redirect URI via environment (useful for deploy vs local).
REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/v1/auth/google/callback",
)

# Valid scopes for basic profile/email info. Do NOT use plain https://www.googleapis.com which is invalid.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _make_flow(state: Optional[str] = None) -> Flow:
    """Create a new Flow instance for each request."""
    # Create a fresh Flow per request (do not reuse a module-level Flow instance).
    # First try to load the client_secret.json file (useful for local dev).
    with contextlib.suppress(Exception):
        # When deploying we often don't commit client_secret.json. In that case
        # construct a client config from environment variables (CLIENT_ID, CLIENT_SECRET)
        # and use Flow.from_client_config.
        if not (CLIENT_ID and CLIENT_SECRET):
            raise Exception("CLIENT_ID and CLIENT_SECRET must be set in environment")

        client_config = {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(
            client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI
        )

    if state:
        # If state is provided, set it so the flow will accept it on fetch
        with contextlib.suppress(Exception):
            flow.state = state
    return flow


@router.get("/login/google")
async def login_google(request: Request):
    """Redirects the user to the Google authentication page."""
    # Build a new Flow and produce an authorization URL. We request offline access so
    # a refresh token can be returned when authorized (optional).
    flow = _make_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
    )
    # Store state server-side in the session (requires SessionMiddleware in app)
    with contextlib.suppress(Exception):
        if hasattr(request, "session"):
            request.session["oauth_state"] = state
    return {"url": authorization_url}


@router.get(
    "/auth/google/callback",
)
async def auth_callback(request: Request, code: str = None, state: str = None):
    """Handles the redirect from Google, exchanges the code for a token, and gets user info.

    Security notes:
    - Validate the `state` value against the one you stored in the user's session/cookie.
    - This example assumes the frontend returns the `state` value and the app validates it.
    """
    # In a production app, validate the state stored in a server-side session.
    # If you used SessionMiddleware you can access request.session and compare/consume it.
    session_state = None
    try:
        session_state = (
            request.session.pop("oauth_state", None)
            if hasattr(request, "session")
            else None
        )
    except Exception:
        session_state = None

    if session_state and state and session_state != state:
        return {"error": "Invalid state parameter"}

    # Create a fresh Flow and exchange the authorization response for tokens
    flow = _make_flow()
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials

    # Use credentials to fetch user info
    service = build("oauth2", "v2", credentials=creds)
    user_info = service.userinfo().get().execute()

    # Process user_info, create a session, JWT token, etc.
    return {"message": "Authentication successful!", "user_info": user_info}
