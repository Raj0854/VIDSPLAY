import re
from flask import Blueprint, request, jsonify
from flask_login import current_user
from models import db, Category, Video, ActivityLog
from utils.auth_helpers import admin_required

categories_bp = Blueprint("api_categories", __name__, url_prefix="/api/categories")


def generate_unique_category_slug(name: str, existing_id: int = None) -> str:
    base_slug = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    base_slug = re.sub(r"[\s_-]+", "-", base_slug)
    if not base_slug:
        base_slug = "category"

    slug = base_slug
    counter = 1
    query = Category.query.filter_by(slug=slug)
    if existing_id:
        query = query.filter(Category.id != existing_id)

    while query.first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
        query = Category.query.filter_by(slug=slug)
        if existing_id:
            query = query.filter(Category.id != existing_id)

    return slug


@categories_bp.route("", methods=["GET"])
def get_categories():
    """List categories. Public requests get is_active=True ordered by display_order."""
    include_all = request.args.get("all", "0") == "1" and current_user.is_authenticated

    query = Category.query
    if not include_all:
        query = query.filter(Category.is_active == True)

    categories = query.order_by(Category.display_order.asc(), Category.name.asc()).all()
    return jsonify({
        "success": True,
        "categories": [c.to_dict(include_video_count=True) for c in categories]
    })


@categories_bp.route("/<identifier>", methods=["GET"])
def get_category(identifier):
    """Get category by ID or slug."""
    if identifier.isdigit():
        category = Category.query.get(int(identifier))
    else:
        category = Category.query.filter_by(slug=identifier).first()

    if not category:
        return jsonify({"success": False, "error": "Category not found"}), 404

    return jsonify({"success": True, "category": category.to_dict(include_video_count=True)})


@categories_bp.route("", methods=["POST"])
@admin_required
def create_category():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Category name is required"}), 400

    slug = (data.get("slug") or "").strip()
    if not slug:
        slug = generate_unique_category_slug(name)
    else:
        # Check collision
        if Category.query.filter_by(slug=slug).first():
            slug = generate_unique_category_slug(slug)

    description = data.get("description", "")
    icon = data.get("icon", "bi-folder")
    display_order = data.get("display_order", 0)
    is_active = bool(data.get("is_active", True))

    category = Category(
        name=name,
        slug=slug,
        description=description,
        icon=icon,
        display_order=display_order,
        is_active=is_active,
    )
    db.session.add(category)
    db.session.commit()

    ActivityLog.log(
        action="category_created",
        details=f"Created category '{category.name}' ({category.slug})",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": "Category created successfully",
        "category": category.to_dict()
    }), 201


@categories_bp.route("/<int:category_id>", methods=["PUT"])
@admin_required
def update_category(category_id):
    category = Category.query.get_or_404(category_id)
    data = request.get_json() or {}

    if "name" in data:
        new_name = (data["name"] or "").strip()
        if new_name and new_name != category.name:
            category.name = new_name
            if "slug" not in data or not data["slug"]:
                category.slug = generate_unique_category_slug(new_name, existing_id=category.id)

    if "slug" in data and data["slug"]:
        new_slug = (data["slug"] or "").strip()
        if new_slug != category.slug:
            category.slug = generate_unique_category_slug(new_slug, existing_id=category.id)

    if "description" in data:
        category.description = data["description"]

    if "icon" in data:
        category.icon = data["icon"]

    if "display_order" in data:
        category.display_order = int(data["display_order"])

    if "is_active" in data:
        category.is_active = bool(data["is_active"])

    db.session.commit()

    ActivityLog.log(
        action="category_updated",
        details=f"Updated category '{category.name}'",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": "Category updated successfully",
        "category": category.to_dict()
    })


@categories_bp.route("/reorder", methods=["POST"])
@admin_required
def reorder_categories():
    """
    Accepts JSON array of category IDs in the new order:
    {"order": [3, 1, 4, 2]}
    """
    data = request.get_json() or {}
    order_ids = data.get("order", [])
    if not isinstance(order_ids, list):
        return jsonify({"success": False, "error": "Invalid order format"}), 400

    for idx, cat_id in enumerate(order_ids):
        Category.query.filter_by(id=cat_id).update({"display_order": idx})

    db.session.commit()
    return jsonify({"success": True, "message": "Categories reordered successfully"})


@categories_bp.route("/<int:category_id>", methods=["DELETE"])
@admin_required
def delete_category(category_id):
    """
    Safe delete category:
    Optional reassign_to_id parameter in JSON body to move existing videos.
    If no reassign_to_id provided, videos become category_id=NULL.
    """
    category = Category.query.get_or_404(category_id)
    data = request.get_json(silent=True) or {}
    reassign_to_id = data.get("reassign_to_id")

    video_count = Video.query.filter_by(category_id=category.id).count()

    if reassign_to_id:
        target_cat = Category.query.get(reassign_to_id)
        if not target_cat:
            return jsonify({"success": False, "error": "Reassignment target category not found"}), 400
        Video.query.filter_by(category_id=category.id).update({"category_id": target_cat.id})
    else:
        Video.query.filter_by(category_id=category.id).update({"category_id": None})

    name = category.name
    db.session.delete(category)
    db.session.commit()

    ActivityLog.log(
        action="category_deleted",
        details=f"Deleted category '{name}' (had {video_count} videos, reassigned={reassign_to_id or 'none'})",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": f"Category '{name}' deleted successfully"
    })
