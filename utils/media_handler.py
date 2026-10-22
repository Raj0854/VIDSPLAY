import os
import uuid
import mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename
from PIL import Image

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "ogg", "mov", "mkv"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "avif", "gif"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_extensions


def save_uploaded_file(file_storage, base_upload_dir: Path, subfolder: str = "general") -> dict:
    """
    Safely saves an uploaded file into base_upload_dir / subfolder.
    Returns metadata dict:
    {
        "filename": str,
        "original_name": str,
        "file_path": str (relative to base),
        "full_path": Path,
        "mime_type": str,
        "file_size": int,
        "asset_type": str
    }
    """
    original_name = file_storage.filename or "unnamed_file"
    raw_name = secure_filename(original_name)
    if not raw_name:
        raw_name = f"file_{uuid.uuid4().hex[:8]}"

    ext = ""
    if "." in raw_name:
        ext = raw_name.rsplit(".", 1)[1].lower()

    # Determine asset type
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        asset_type = "video"
        subfolder = "videos"
    elif ext in ALLOWED_IMAGE_EXTENSIONS:
        asset_type = "thumbnail" if subfolder == "thumbnails" else ("banner" if subfolder == "banners" else "general")
        if subfolder not in ["thumbnails", "banners"]:
            subfolder = "thumbnails"
    else:
        asset_type = "general"

    # Unique filename
    unique_filename = f"{uuid.uuid4().hex}_{raw_name}"

    target_dir = base_upload_dir / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    destination = target_dir / unique_filename
    file_storage.save(str(destination))

    file_size = destination.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(destination))
    if not mime_type:
        mime_type = "application/octet-stream"

    # Relative path from project static folder or uploads
    rel_path = f"static/uploads/{subfolder}/{unique_filename}"

    return {
        "filename": unique_filename,
        "original_name": original_name,
        "file_path": rel_path,
        "full_path": destination,
        "mime_type": mime_type,
        "file_size": file_size,
        "asset_type": asset_type,
    }


def generate_image_thumbnail(image_path: Path, max_size=(640, 360)) -> str:
    """Optionally creates an optimized thumbnail image."""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size)
            thumb_name = f"thumb_{image_path.name}"
            thumb_path = image_path.parent / thumb_name
            img.save(str(thumb_path))
            return thumb_name
    except Exception:
        return image_path.name
