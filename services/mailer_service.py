import contextlib
import os
import smtplib
import ssl
import socket
from email.message import EmailMessage
from typing import Optional
import jwt
from datetime import datetime, timedelta, timezone

# Try to auto-load a .env file for convenience during local dev if python-dotenv
# is available. This avoids situations where you run the script directly but the
# environment variables in .env are not loaded into the process.
try:
    from dotenv import load_dotenv

    # load .env from project root if present; allow overriding by system env
    _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(_env_path)
except Exception:
    # dotenv is optional; if not present the caller must set env vars manually
    pass


# Fallback: if dotenv wasn't installed or didn't load variables, try a simple
# parser to load key=value pairs from .env into os.environ for common use.
def _load_env_fallback():
    with contextlib.suppress(Exception):
        _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if not os.path.exists(_env_path):
            return
        # only load if SMTP_HOST not already present
        if os.getenv("SMTP_HOST"):
            return
        with open(_env_path, "r", encoding="utf8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and not os.getenv(key):
                    os.environ[key] = val

# run fallback loader now
_load_env_fallback()


def _get_smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes"),
        "starttls": os.getenv("SMTP_STARTTLS", "true").lower() in ("1", "true", "yes"),
        "from": os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", "no-reply@example.com")),
    }


def send_email(
    subject: str, recipient: str, body: str, html: Optional[str] = None
) -> bool:
    """Send an email using SMTP settings from environment variables.

    Returns True on success, False on failure.
    """
    cfg = _get_smtp_config()
    # when debugging, print resolved SMTP config (mask sensitive fields)
    debug = os.getenv("MAILER_DEBUG", "0").lower() in ("1", "true", "yes")
    if debug:
        masked = dict(cfg)
        if masked.get("password"):
            masked["password"] = "****"
        print("[mailer debug] SMTP config:", masked)

    # Basic validation: ensure recipient looks like an email address
    if not recipient or not isinstance(recipient, str) or "@" not in recipient:
        print(f"[mailer] invalid recipient address: {recipient!r}")
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = recipient
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    # quick network-level connect test to detect platform-level SMTP blocks
    try:
        sock_timeout = float(os.getenv("MAILER_CONNECT_TIMEOUT", "5"))
        socket.create_connection((cfg["host"], cfg["port"]), timeout=sock_timeout).close()
    except Exception as conn_err:
        # likely outbound SMTP blocked or DNS issue in the hosting environment
        with contextlib.suppress(Exception):
            if os.getenv("MAILER_DEBUG", "0").lower() in ("1", "true", "yes"):
                print(f"[mailer] network connect to {cfg['host']}:{cfg['port']} failed: {conn_err}")

        if sendgrid_key := os.getenv("SENDGRID_API_KEY"):
            try:
                return _send_via_sendgrid(sendgrid_key, cfg.get("from"), recipient, subject, body, html)
            except Exception:
                with contextlib.suppress(Exception):
                    if os.getenv("MAILER_DEBUG", "0").lower() in ("1", "true", "yes"):
                        import traceback

                        print("[mailer] sendgrid fallback failed")
                        traceback.print_exc()
        return False

    try:
        if cfg["use_ssl"]:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context) as server:
                if cfg["user"]:
                    server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                if cfg["starttls"]:
                    server.starttls()
                if cfg["user"]:
                    server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        return True
    except Exception as e:
        # Avoid failing the whole request; log and return False
        with contextlib.suppress(Exception):
            debug = os.getenv("MAILER_DEBUG", "0").lower() in ("1", "true", "yes")
            print(f"[mailer] failed to send email to {recipient}: {e}")
            if debug:
                import traceback

                traceback.print_exc()
        return False


def _send_via_sendgrid(api_key: str, from_email: str, to_email: str, subject: str, text: str, html: Optional[str] = None) -> bool:
    """Send email via SendGrid HTTP API as a fallback when SMTP is blocked.

    Requires SENDGRID_API_KEY env var. Uses requests; raises on unexpected errors.
    """
    try:
        import requests

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": text}],
        }
        if html:
            payload["content"] = [
                {"type": "text/plain", "value": text},
                {"type": "text/html", "value": html},
            ]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post("https://api.sendgrid.com/v3/mail/send", headers=headers, json=payload, timeout=10)
        return resp.status_code in {200, 202}
    except Exception:
        # bubble up to caller for logging
        raise


def _build_action_link(token: str, action: str = "activate") -> str:
    # action: activate | reset
    base = (
        os.getenv("FRONTEND_URL")
        or os.getenv("APP_URL")
        or os.getenv("BASE_URL")
        or "http://localhost:3000"
    )
    print(f"[mailer] building action link for action={action}, token={token}, base={base}")
    if action == "activate":
        return f"{base}/activate?token={token}"
    if action == "reset":
        return f"{base}/reset-password?token={token}"
    return f"{base}/?token={token}"


def send_activation_email(
    recipient: str, token: str, username: Optional[str] = None
) -> bool:
    link = _build_action_link(token, action="activate")
    subject = "Activate your account"
    text = f"Hi {username or ''}\n\nPlease activate your account by clicking the link below:\n{link}\n\nIf you didn't request this, ignore this email.\n"
    html = (
        f"<p>Hi {username or ''},</p>"
        f"<p>Please activate your account by clicking the link below:</p>"
        f'<p><a href="{link}">Activate account</a></p>'
        f"<p>If you didn't request this, ignore this email.</p>"
    )
    return send_email(subject, recipient, text, html)


def send_reset_password_email(
    recipient: str, token: str, username: Optional[str] = None
) -> bool:
    link = _build_action_link(token, action="reset")
    subject = "Reset your password"
    text = f"Hi {username or ''}\n\nYou can reset your password by clicking the link below:\n{link}\n\nIf you didn't request this, ignore this email.\n"
    html = (
        f"<p>Hi {username or ''},</p>"
        f"<p>You can reset your password by clicking the link below:</p>"
        f'<p><a href="{link}">Reset password</a></p>'
        f"<p>If you didn't request this, ignore this email.</p>"
    )
    return send_email(subject, recipient, text, html)


def send_simple_notification(recipient: str, subject: str, message: str) -> bool:
    return send_email(subject, recipient, message)


def send_welcome_email(recipient: str, username: Optional[str] = None) -> bool:

    # create token to activate account (in real implementation, this should be a real token linked to the user)
    jwt_secret = os.getenv("SECRET_KEY", "dev-secret")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=300)  # token valid for 5 minutes
    payload = {"sub": recipient}
    token = jwt.encode(
        {**payload, "exp": exp, "iat": now}, jwt_secret, algorithm="HS256"
    )

    subject = "Welcome to our service!"
    text = f"Hi {username or ''}\n\nWelcome to our service! We're glad to have you on board.\n\nBest regards,\nThe Team"
    html = (
        f"<p>Hi {username or ''},</p>"
        f"<p>Welcome to our service! We're glad to have you on board.</p>"
        f"<p>Password: ********</p>"
        f"<p>Activate your account by clicking the link below:</p>"
        f'<p><a href="{_build_action_link(token, action="activate")}">Activate account</a></p>'
        f"<p>Best regards,<br>The Team</p>"
    )
    return send_email(subject, recipient, text, html)

def send_welcome_email_with_google(recipient: str, username: Optional[str] = None) -> bool:

    # create token to activate account (in real implementation, this should be a real token linked to the user)
    jwt_secret = os.getenv("SECRET_KEY", "dev-secret")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=300)  # token valid for 5 minutes
    payload = {"sub": recipient}
    token = jwt.encode(
        {**payload, "exp": exp, "iat": now}, jwt_secret, algorithm="HS256"
    )

    subject = "Welcome to our service!"
    text = f"Hi {username or ''}\n\nWelcome to our service! We're glad to have you on board.\n\nBest regards,\nThe Team"
    html = (
        f"<p>Hi {username or ''},</p>"
        f"<p>Welcome to our service! We're glad to have you on board.</p>"
        f"<p>Password: {username or ''} - Please change it after login to something more secure.</p>"
        f"<p>Activate your account by clicking the link below:</p>"
        f'<p><a href="{_build_action_link(token, action="activate")}">Activate account</a></p>'
        f"<p>Best regards,<br>The Team</p>"
    )
    return send_email(subject, recipient, text, html)


if __name__ == "__main__":
    # Small manual test — will attempt to send using env SMTP settings
    ok = send_email(
        "Test email", os.getenv("TEST_EMAIL", ""), "This is a test from mailer_service"
    )
    print("sent?", ok)
