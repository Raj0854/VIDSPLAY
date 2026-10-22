from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from models import db, MediaAsset, Video, ActivityLog
from utils.auth_helpers import admin_required
from utils.media_handler import save_uploaded_file

media_bp = Blueprint("api_media", __name__, url_prefix="/api/media")


@media_bp.route("", methods=["GET"])
@admin_required
def get_media():
    """List uploaded media assets with search and type filter."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    asset_type = request.args.get("type", None)
    search = request.args.get("q", "").strip()

    query = MediaAsset.query

    if asset_type and asset_type != "all":
        query = query.filter(MediaAsset.asset_type == asset_type)

    if search:
        query = query.filter(
            (MediaAsset.original_name.ilike(f"%{search}%")) |
            (MediaAsset.filename.ilike(f"%{search}%"))
        )

    paginated = query.order_by(MediaAsset.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "assets": [a.to_dict() for a in paginated.items],
        "total": paginated.total,
        "pages": paginated.pages,
        "page": page,
    })


@media_bp.route("/upload", methods=["POST"])
@admin_required
def upload_media():
    """Direct upload to media library."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400

    subfolder = request.form.get("subfolder", "general")
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])

    meta = save_uploaded_file(file, upload_dir, subfolder=subfolder)

    asset = MediaAsset(
        filename=meta["filename"],
        original_name=meta["original_name"],
        file_path=meta["file_path"],
        mime_type=meta["mime_type"],
        file_size=meta["file_size"],
        asset_type=meta["asset_type"],
    )
    db.session.add(asset)
    db.session.commit()

    ActivityLog.log(
        action="media_uploaded",
        details=f"Uploaded {meta['asset_type']} '{meta['original_name']}' ({meta['file_size']} bytes)",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": "File uploaded successfully", "asset": asset.to_dict()}), 201


@media_bp.route("/<int:asset_id>", methods=["DELETE"])
@admin_required
def delete_media(asset_id):
    """
    Safely delete media:
    Checks if referenced by any Video (storage_key or thumbnail_url).
    """
    asset = MediaAsset.query.get_or_404(asset_id)
    force = request.args.get("force", "0") == "1"

    # Check references
    ref_count = Video.query.filter(
        (Video.storage_key == asset.file_path) |
        (Video.thumbnail_url == f"/{asset.file_path}") |
        (Video.thumbnail_url == asset.file_path)
    ).count()

    if ref_count > 0 and not force:
        return jsonify({
            "success": False,
            "error": f"Asset is currently referenced by {ref_count} video(s). Pass force=1 to delete anyway.",
            "references": ref_count,
        }), 409

    # Remove physical file if exists
    try:
        full_path = Path(current_app.root_path) / asset.file_path
        if full_path.exists():
            full_path.unlink()
    except Exception:
        pass

    filename = asset.original_name
    db.session.delete(asset)
    db.session.commit()

    ActivityLog.log(
        action="media_deleted",
        details=f"Deleted media asset '{filename}' (ID {asset_id})",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": f"Asset '{filename}' deleted successfully"})
