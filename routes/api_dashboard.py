from flask import Blueprint, request, jsonify
from models import db, Video, Category, NavigationItem, MediaAsset, ActivityLog, SiteSetting
from utils.auth_helpers import admin_required

dashboard_bp = Blueprint("api_dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    """Real statistics derived directly from database records."""
    total_videos = Video.query.count()
    published_videos = Video.query.filter_by(is_published=True).count()
    draft_videos = total_videos - published_videos

    total_categories = Category.query.count()
    active_nav_tabs = NavigationItem.query.filter_by(is_active=True).count()
    total_media_assets = MediaAsset.query.count()

    total_views = db.session.query(db.func.sum(Video.views_count)).scalar() or 0

    recent_videos = (
        Video.query.order_by(Video.id.desc()).limit(5).all()
    )

    recent_activity = (
        ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    )

    return jsonify({
        "success": True,
        "stats": {
            "total_videos": total_videos,
            "published_videos": published_videos,
            "draft_videos": draft_videos,
            "total_categories": total_categories,
            "active_nav_tabs": active_nav_tabs,
            "total_media_assets": total_media_assets,
            "total_views": total_views,
        },
        "recent_videos": [v.to_dict() for v in recent_videos],
        "recent_activity": [a.to_dict() for a in recent_activity],
    })


@dashboard_bp.route("/activity", methods=["GET"])
@admin_required
def get_activity():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    paginated = (
        ActivityLog.query.order_by(ActivityLog.timestamp.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "success": True,
        "logs": [log.to_dict() for log in paginated.items],
        "total": paginated.total,
        "pages": paginated.pages,
        "page": page,
    })


@dashboard_bp.route("/settings", methods=["GET"])
def get_settings():
    """Get site settings. Publicly readable."""
    settings = SiteSetting.query.all()
    data = {s.key: s.value for s in settings}
    # Provide defaults if not yet set
    defaults = {
        "site_title": "VIDSPLAY",
        "site_tagline": "Your Ultimate Destination for Entertainment",
        "marquee_text": "Welcome to VIDSPLAY - Your Ultimate Destination for Movies, TV Shows, Web Series, Anime, Documentaries, Kids' Content, Music, Sports, and Dance Entertainment!",
        "contact_email": "admin@vidsplay.com",
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    return jsonify({"success": True, "settings": data})


@dashboard_bp.route("/settings", methods=["POST"])
@admin_required
def update_settings():
    data = request.get_json() or {}
    for key, value in data.items():
        SiteSetting.set(key, str(value))

    return jsonify({"success": True, "message": "Settings updated successfully"})
