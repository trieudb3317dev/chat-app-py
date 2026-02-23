import contextlib
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

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
    try:
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
    except Exception:
        pass


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


def _build_action_link(token: str, action: str = "activate") -> str:
    # action: activate | reset
    base = (
        os.getenv("FRONTEND_URL")
        or os.getenv("APP_URL")
        or os.getenv("BASE_URL")
        or "http://localhost:3000"
    )
    if action == "activate":
        return f"{base.rstrip('/')}/activate?token={token}"
    if action == "reset":
        return f"{base.rstrip('/')}/reset-password?token={token}"
    return f"{base.rstrip('/')}/?token={token}"


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
    subject = "Welcome to our service!"
    text = f"Hi {username or ''}\n\nWelcome to our service! We're glad to have you on board.\n\nBest regards,\nThe Team"
    html = (
        f"<p>Hi {username or ''},</p>"
        f"<p>Welcome to our service! We're glad to have you on board.</p>"
        f"<p>Password: ********</p>"
        f"<p>Activate your account by clicking the link below:</p>"
        f'<p><a href="{_build_action_link("dummy-token", action="activate")}">Activate account</a></p>'
        f"<p>Best regards,<br>The Team</p>"
    )
    return send_email(subject, recipient, text, html)

if __name__ == "__main__":
    # Small manual test — will attempt to send using env SMTP settings
    ok = send_email(
        "Test email", os.getenv("TEST_EMAIL", ""), "This is a test from mailer_service"
    )
    print("sent?", ok)

