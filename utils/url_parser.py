import re
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract 11-character YouTube video ID from various YouTube URL formats:
    - https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - https://youtu.be/dQw4w9WgXcQ
    - https://www.youtube.com/embed/dQw4w9WgXcQ
    - https://www.youtube.com/shorts/dQw4w9WgXcQ
    - https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=...
    """
    if not url:
        return None

    url = url.strip()

    # Pattern for youtu.be/<id>
    short_pattern = r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})"
    m = re.search(short_pattern, url)
    if m:
        return m.group(1)

    # Pattern for youtube.com/embed/<id>
    embed_pattern = r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})"
    m = re.search(embed_pattern, url)
    if m:
        return m.group(1)

    # Pattern for youtube.com/shorts/<id>
    shorts_pattern = r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})"
    m = re.search(shorts_pattern, url)
    if m:
        return m.group(1)

    # Standard youtube.com/watch?v=<id>
    try:
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"] and len(qs["v"][0]) == 11:
                return qs["v"][0]
    except Exception:
        pass

    # Generic fallback regex for 11 chars after v= or embed/ or youtu.be/
    generic = re.search(r"(?:v=|\/embed\/|\/11|\/v\/|youtu\.be\/|\/shorts\/)([a-zA-Z0-9_-]{11})", url)
    if generic:
        return generic.group(1)

    return None


def parse_video_url(url: str) -> Dict[str, Any]:
    """
    Validate and parse video URL into structured metadata.
    Returns:
    {
        "valid": bool,
        "source_type": "youtube" | "external" | "invalid",
        "embed_code": str or None,
        "thumbnail_url": str or None,
        "normalized_url": str,
        "error": str or None
    }
    """
    if not url or not isinstance(url, str):
        return {
            "valid": False,
            "source_type": "invalid",
            "embed_code": None,
            "thumbnail_url": None,
            "normalized_url": "",
            "error": "URL cannot be empty."
        }

    url = url.strip()

    # Disallow unsafe URL schemes
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {
            "valid": False,
            "source_type": "invalid",
            "embed_code": None,
            "thumbnail_url": None,
            "normalized_url": url,
            "error": "Invalid scheme. Only http:// and https:// URLs are allowed."
        }

    # Check for YouTube
    yt_id = extract_youtube_id(url)
    if yt_id:
        return {
            "valid": True,
            "source_type": "youtube",
            "embed_code": yt_id,
            "thumbnail_url": f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg",
            "normalized_url": f"https://www.youtube.com/watch?v={yt_id}",
            "error": None
        }

    # Check for direct video file (MP4, WebM, Ogg)
    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in [".mp4", ".webm", ".ogg"]):
        return {
            "valid": True,
            "source_type": "external",
            "embed_code": None,
            "thumbnail_url": None,
            "normalized_url": url,
            "error": None
        }

    # Unrecognized or unsupported video format
    return {
        "valid": False,
        "source_type": "invalid",
        "embed_code": None,
        "thumbnail_url": None,
        "normalized_url": url,
        "error": "Unsupported video URL. Please provide a valid YouTube link or a direct .mp4/.webm video link."
    }
