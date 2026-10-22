import re
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from models import db, Video, Category, ActivityLog, MediaAsset
from utils.auth_helpers import admin_required
from utils.url_parser import parse_video_url
from utils.media_handler import save_uploaded_file, ALLOWED_VIDEO_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS

videos_bp = Blueprint("api_videos", __name__, url_prefix="/api/videos")


def generate_unique_slug(title: str, existing_id: int = None) -> str:
    base_slug = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    base_slug = re.sub(r"[\s_-]+", "-", base_slug)
    if not base_slug:
        base_slug = "video"

    slug = base_slug
    counter = 1
    query = Video.query.filter_by(slug=slug)
    if existing_id:
        query = query.filter(Video.id != existing_id)

    while query.first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
        query = Video.query.filter_by(slug=slug)
        if existing_id:
            query = query.filter(Video.id != existing_id)

    return slug


@videos_bp.route("/validate-url", methods=["POST"])
@admin_required
def validate_url():
    """Live validation helper for the admin Add Video form."""
    data = request.get_json() or {}
    url = data.get("url", "")
    result = parse_video_url(url)
    return jsonify(result)


@videos_bp.route("", methods=["GET"])
def get_videos():
    """
    List videos with filtering, search, pagination, and status checks.
    Public requests only see is_published=True.
    Admin requests can pass ?include_drafts=1
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 12, type=int)
    category_slug = request.args.get("category", None)
    search_query = request.args.get("q", "").strip()
    source_type = request.args.get("source_type", None)
    sort_by = request.args.get("sort", "newest")  # 'newest', 'views', 'trending', 'title'

    query = Video.query

    # Restrict to published unless user is admin and specifically asked for all
    include_drafts = request.args.get("include_drafts", "0") == "1"
    if not (current_user.is_authenticated and include_drafts):
        query = query.filter(Video.is_published == True)

    # Category filter
    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            query = query.filter(Video.category_id == cat.id)
        else:
            return jsonify({"videos": [], "total": 0, "pages": 0, "page": page})

    # Search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Video.title.ilike(search_term)) | (Video.description.ilike(search_term))
        )

    # Source type filter
    if source_type:
        query = query.filter(Video.source_type == source_type)

    # Sorting
    if sort_by == "views":
        query = query.order_by(Video.views_count.desc(), Video.id.desc())
    elif sort_by == "trending":
        query = query.order_by(Video.is_featured.desc(), Video.views_count.desc())
    elif sort_by == "title":
        query = query.order_by(Video.title.asc())
    else:  # newest
        query = query.order_by(Video.id.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "videos": [v.to_dict() for v in paginated.items],
        "total": paginated.total,
        "pages": paginated.pages,
        "page": page,
        "per_page": per_page,
    })


@videos_bp.route("/<identifier>", methods=["GET"])
def get_video(identifier):
    """Get single video by ID or slug."""
    if identifier.isdigit():
        video = db.session.get(Video, int(identifier))
    else:
        video = Video.query.filter_by(slug=identifier).first()

    if not video:
        return jsonify({"success": False, "error": "Video not found"}), 404

    # If draft and not admin
    if not video.is_published and not current_user.is_authenticated:
        return jsonify({"success": False, "error": "Video not found"}), 404

    # Increment view count if requested by viewer
    if request.args.get("increment_view", "0") == "1":
        video.views_count += 1
        db.session.commit()

    return jsonify({"success": True, "video": video.to_dict()})


@videos_bp.route("", methods=["POST"])
@admin_required
def create_video():
    """
    Create a new video:
    Supports both Option 1 (multipart form with local video upload)
    and Option 2 (JSON payload or form with video URL).
    """
    is_multipart = request.content_type and "multipart/form-data" in request.content_type

    if is_multipart:
        data = request.form
        video_file = request.files.get("video_file")
        thumb_file = request.files.get("thumbnail_file")
    else:
        data = request.get_json() or {}
        video_file = None
        thumb_file = None

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "Title is required"}), 400

    description = data.get("description", "")
    category_id = data.get("category_id", type=int) if is_multipart else data.get("category_id")
    if category_id:
        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            category_id = None

    is_published = str(data.get("is_published", "true")).lower() in ["true", "1", "on"]
    is_featured = str(data.get("is_featured", "false")).lower() in ["true", "1", "on"]
    source_type = data.get("source_type", "youtube")
    thumbnail_url = data.get("thumbnail_url", "")
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])

    storage_key = None
    embed_code = None
    source_url = None
    file_size = None

    # Handle Option 1: Local Upload
    if source_type == "local" or video_file:
        source_type = "local"
        if not video_file or not video_file.filename:
            return jsonify({"success": False, "error": "No video file provided for local upload"}), 400

        # Save video file
        upload_meta = save_uploaded_file(video_file, upload_dir, subfolder="videos")
        storage_key = upload_meta["file_path"]
        file_size = upload_meta["file_size"]

        # Track in MediaAsset
        media_record = MediaAsset(
            filename=upload_meta["filename"],
            original_name=upload_meta["original_name"],
            file_path=upload_meta["file_path"],
            mime_type=upload_meta["mime_type"],
            file_size=upload_meta["file_size"],
            asset_type="video",
        )
        db.session.add(media_record)

    # Handle Option 2: URL
    elif source_type in ["youtube", "external"]:
        raw_url = (data.get("source_url") or "").strip()
        parsed = parse_video_url(raw_url)
        if not parsed["valid"]:
            return jsonify({"success": False, "error": parsed["error"]}), 400

        source_type = parsed["source_type"]
        source_url = parsed["normalized_url"]
        embed_code = parsed["embed_code"]

        # Fallback to auto-detected YouTube thumbnail if not provided
        if not thumbnail_url and parsed["thumbnail_url"]:
            thumbnail_url = parsed["thumbnail_url"]

    # Handle custom thumbnail upload if provided
    if thumb_file and thumb_file.filename:
        thumb_meta = save_uploaded_file(thumb_file, upload_dir, subfolder="thumbnails")
        thumbnail_url = f"/{thumb_meta['file_path']}"
        thumb_record = MediaAsset(
            filename=thumb_meta["filename"],
            original_name=thumb_meta["original_name"],
            file_path=thumb_meta["file_path"],
            mime_type=thumb_meta["mime_type"],
            file_size=thumb_meta["file_size"],
            asset_type="thumbnail",
        )
        db.session.add(thumb_record)

    # Generate unique slug
    slug = generate_unique_slug(title)

    video = Video(
        title=title,
        slug=slug,
        description=description,
        source_type=source_type,
        source_url=source_url,
        storage_key=storage_key,
        embed_code=embed_code,
        thumbnail_url=thumbnail_url or "/static/img/logo.png",
        is_published=is_published,
        is_featured=is_featured,
        category_id=category_id,
        file_size=file_size,
    )

    db.session.add(video)
    db.session.commit()

    ActivityLog.log(
        action="video_created",
        details=f"Created video '{video.title}' (ID {video.id}, {source_type})",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": "Video created successfully",
        "video": video.to_dict()
    }), 201


@videos_bp.route("/<int:video_id>", methods=["PUT"])
@admin_required
def update_video(video_id):
    """Update video details."""
    video = Video.query.get_or_404(video_id)
    is_multipart = request.content_type and "multipart/form-data" in request.content_type

    if is_multipart:
        data = request.form
        thumb_file = request.files.get("thumbnail_file")
    else:
        data = request.get_json() or {}
        thumb_file = None

    if "title" in data:
        new_title = (data["title"] or "").strip()
        if new_title and new_title != video.title:
            video.title = new_title
            video.slug = generate_unique_slug(new_title, existing_id=video.id)

    if "description" in data:
        video.description = data["description"]

    if "category_id" in data:
        cat_id = data["category_id"]
        try:
            video.category_id = int(cat_id) if cat_id else None
        except (ValueError, TypeError):
            video.category_id = None

    if "is_published" in data:
        video.is_published = str(data["is_published"]).lower() in ["true", "1", "on"]

    if "is_featured" in data:
        video.is_featured = str(data["is_featured"]).lower() in ["true", "1", "on"]

    if "thumbnail_url" in data and data["thumbnail_url"]:
        video.thumbnail_url = data["thumbnail_url"]

    # A blank replacement field keeps the existing source unchanged.
    if "source_url" in data and data["source_url"]:
        replacement_url = data["source_url"]
        if not isinstance(replacement_url, str):
            return jsonify({"success": False, "error": "Video source URL must be text"}), 400

        parsed = parse_video_url(replacement_url.strip())
        if not parsed["valid"]:
            return jsonify({"success": False, "error": parsed["error"]}), 400

        previous_thumbnail = video.thumbnail_url or ""
        video.source_url = parsed["normalized_url"]
        video.source_type = parsed["source_type"]
        video.embed_code = parsed["embed_code"]
        video.storage_key = None
        video.file_size = None
        if parsed["thumbnail_url"] and (
            not previous_thumbnail
            or previous_thumbnail == "/static/img/logo.png"
            or previous_thumbnail.startswith("https://img.youtube.com/")
        ):
            video.thumbnail_url = parsed["thumbnail_url"]

    # Thumbnail upload
    if thumb_file and thumb_file.filename:
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        thumb_meta = save_uploaded_file(thumb_file, upload_dir, subfolder="thumbnails")
        video.thumbnail_url = f"/{thumb_meta['file_path']}"
        thumb_record = MediaAsset(
            filename=thumb_meta["filename"],
            original_name=thumb_meta["original_name"],
            file_path=thumb_meta["file_path"],
            mime_type=thumb_meta["mime_type"],
            file_size=thumb_meta["file_size"],
            asset_type="thumbnail",
        )
        db.session.add(thumb_record)

    db.session.commit()

    ActivityLog.log(
        action="video_updated",
        details=f"Updated video '{video.title}' (ID {video.id})",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": "Video updated successfully", "video": video.to_dict()})


@videos_bp.route("/<int:video_id>", methods=["DELETE"])
@admin_required
def delete_video(video_id):
    """Delete a video with confirmation."""
    video = Video.query.get_or_404(video_id)
    title = video.title

    db.session.delete(video)
    db.session.commit()

    ActivityLog.log(
        action="video_deleted",
        details=f"Deleted video '{title}' (ID {video_id})",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": f"Video '{title}' deleted successfully"})
