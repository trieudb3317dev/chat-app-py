# Configuration for Cloudinary
import cloudinary
try:
    # import uploader module explicitly — avoids issues when cloudinary package layout
    from cloudinary import uploader as cloudinary_uploader
except Exception:
    cloudinary_uploader = None
    logger.warning(
        "cloudinary.uploader not available; ensure the 'cloudinary' package is installed correctly"
    )
import contextlib
import os
import sys
import io
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

with contextlib.suppress(Exception):
    from dotenv import load_dotenv

    # load .env from project root if present; allow overriding by system env
    _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(_env_path)


# Load Cloudinary configuration from environment variables
if hasattr(cloudinary, "config"):
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    )
else:
    logger.warning("cloudinary module does not expose config(); cloudinary may not be installed")

# warn if configuration looks incomplete
if not (
    os.getenv("CLOUDINARY_CLOUD_NAME")
    and os.getenv("CLOUDINARY_API_KEY")
    and os.getenv("CLOUDINARY_API_SECRET")
):
    logger.warning(
        "Cloudinary environment variables are missing or incomplete; uploads may fail."
    )


def _to_filelike(obj: Any):
    """Normalize common upload inputs to a file-like object acceptable by cloudinary.uploader.upload.

    Accepts: path (str), bytes, file-like objects, and Starlette UploadFile-like objects (has .file).
    Returns a tuple (file_obj, filename) where file_obj is a file-like or a path string.
    """
    # Starlette / FastAPI UploadFile
    if hasattr(obj, "file"):
        return obj.file, getattr(obj, "filename", None)

    # raw bytes
    if isinstance(obj, (bytes, bytearray)):
        return io.BytesIO(obj), None

    return obj, None


def upload_image(file: Any) -> Dict[str, Optional[str]]:
    """Upload an image file to Cloudinary and return a dict with url and public_id.

    The `file` parameter may be:
    - a filesystem path (str)
    - bytes
    - a file-like object with .read()
    - a Starlette/FastAPI UploadFile (has .file and .filename)
    """
    try:
        file_obj, filename = _to_filelike(file)
        logger.debug("Uploading file to Cloudinary: filename=%s, type=%s", filename, type(file_obj))
        # ensure uploader is available
        if cloudinary_uploader is None:
            raise RuntimeError("cloudinary.uploader is not available; install 'cloudinary' package")
        # use resource_type='image' explicitly
        result = cloudinary_uploader.upload(file_obj, resource_type="image")
        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }
    except Exception:
        logger.exception("Error uploading image to Cloudinary")
        return {"url": None, "public_id": None}


def delete_image(public_id: Optional[str]) -> bool:
    """Delete an image from Cloudinary by its public ID. Returns True on success."""
    if not public_id:
        logger.debug("delete_image called with empty public_id")
        return False
    try:
        if cloudinary_uploader is None:
            raise RuntimeError("cloudinary.uploader is not available; cannot delete image")
        result = cloudinary_uploader.destroy(public_id)
        return result.get("result") == "ok"
    except Exception:
        logger.exception("Error deleting image from Cloudinary")
        return False
