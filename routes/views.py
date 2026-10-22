from pathlib import Path
from flask import Blueprint, render_template, abort, redirect, url_for, current_app
from flask_login import current_user
from sqlalchemy import or_
from models import Video, Category, Page, SiteSetting
from utils.auth_helpers import admin_required
from utils.streaming import stream_video

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Main Home page."""
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order.asc()).all()
    featured_video = (
        Video.query.filter(
            Video.is_published.is_(True),
            or_(
                (Video.source_url.isnot(None) & (Video.source_url != "")),
                (Video.storage_key.isnot(None) & (Video.storage_key != "")),
            ),
        )
        .order_by(Video.is_featured.desc(), Video.id.desc())
        .first()
    )
    marquee = SiteSetting.get("marquee_text", "Welcome to VIDSPLAY - Your Ultimate Destination for Entertainment!")
    return render_template(
        "index.html",
        categories=categories,
        featured_video=featured_video,
        marquee_text=marquee,
    )


@views_bp.route("/category/<slug>")
def category_view(slug):
    """Dynamic category page (replaces hardcoded movies.html, music.html, etc.)."""
    category = Category.query.filter_by(slug=slug, is_active=True).first_or_404()
    videos = (
        Video.query.filter_by(category_id=category.id, is_published=True)
        .order_by(Video.id.desc())
        .all()
    )
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order.asc()).all()
    marquee = SiteSetting.get("marquee_text", "Welcome to VIDSPLAY - Your Ultimate Destination for Entertainment!")
    return render_template(
        "category.html",
        category=category,
        videos=videos,
        categories=categories,
        marquee_text=marquee,
    )


@views_bp.route("/pages/<slug>")
def page_view(slug):
    """Dynamic page builder page."""
    page = Page.query.filter_by(slug=slug, is_published=True).first_or_404()
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order.asc()).all()
    marquee = SiteSetting.get("marquee_text", "Welcome to VIDSPLAY - Your Ultimate Destination for Entertainment!")
    return render_template(
        "page_builder.html",
        page=page,
        categories=categories,
        marquee_text=marquee,
    )


@views_bp.route("/stream/<int:video_id>")
def stream_local_video(video_id):
    """Stream a local video with HTTP Range partial content."""
    video = Video.query.get_or_404(video_id)
    if not video.is_published and not current_user.is_authenticated:
        abort(404)

    if video.source_type != "local" or not video.storage_key:
        abort(400, "Not a local video")

    full_path = Path(current_app.root_path) / video.storage_key
    if not full_path.exists():
        abort(404, "Physical video file not found")

    content_type = "video/mp4"
    if str(full_path).endswith(".webm"):
        content_type = "video/webm"
    elif str(full_path).endswith(".ogg"):
        content_type = "video/ogg"

    return stream_video(full_path, content_type=content_type)


@views_bp.route("/admin/login")
def admin_login():
    """Admin Login page."""
    if current_user.is_authenticated:
        return redirect(url_for("views.admin_dashboard"))
    return render_template("admin/login.html")


@views_bp.route("/admin")
@views_bp.route("/admin/<path:subpath>")
@admin_required
def admin_dashboard(subpath=None):
    """Admin Dashboard."""
    return render_template("admin/dashboard.html", user=current_user)
