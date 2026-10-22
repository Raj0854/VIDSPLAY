from flask import Blueprint, request, jsonify
from flask_login import current_user
from models import db, NavigationItem, Category, Page, ActivityLog
from utils.auth_helpers import admin_required

navigation_bp = Blueprint("api_navigation", __name__, url_prefix="/api/navigation")


@navigation_bp.route("", methods=["GET"])
def get_public_navigation():
    """
    Returns active root navbar items with children, ordered by display_order.
    Used by the frontend to render the dynamic navbar.
    """
    items = (
        NavigationItem.query.filter_by(parent_id=None, is_active=True)
        .order_by(NavigationItem.display_order.asc())
        .all()
    )
    return jsonify({
        "success": True,
        "items": [item.to_dict() for item in items]
    })


@navigation_bp.route("/all", methods=["GET"])
@admin_required
def get_all_navigation():
    """
    Returns all navbar items (including drafts/inactive) for the admin dashboard.
    """
    items = (
        NavigationItem.query.filter_by(parent_id=None)
        .order_by(NavigationItem.display_order.asc())
        .all()
    )
    return jsonify({
        "success": True,
        "items": [item.to_dict(include_children=True) for item in items]
    })


@navigation_bp.route("", methods=["POST"])
@admin_required
def create_navigation_item():
    data = request.get_json() or {}
    label = (data.get("label") or "").strip()
    if not label:
        return jsonify({"success": False, "error": "Label is required"}), 400

    target_type = data.get("target_type", "category")  # 'category', 'page', 'custom'
    target_url = data.get("target_url", "")
    category_id = data.get("category_id")
    page_id = data.get("page_id")
    parent_id = data.get("parent_id")
    icon = data.get("icon", "")
    visibility = data.get("visibility", "all")
    is_active = bool(data.get("is_active", True))

    # Calculate max display order
    max_order = (
        db.session.query(db.func.max(NavigationItem.display_order))
        .filter_by(parent_id=parent_id)
        .scalar()
        or 0
    )

    item = NavigationItem(
        label=label,
        target_type=target_type,
        target_url=target_url,
        category_id=int(category_id) if category_id else None,
        page_id=int(page_id) if page_id else None,
        parent_id=int(parent_id) if parent_id else None,
        icon=icon,
        display_order=max_order + 1,
        visibility=visibility,
        is_active=is_active,
    )
    db.session.add(item)
    db.session.commit()

    ActivityLog.log(
        action="nav_created",
        details=f"Created navbar item '{item.label}' -> '{item.get_resolved_url()}'",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": "Navbar item created successfully",
        "item": item.to_dict()
    }), 201


@navigation_bp.route("/<int:item_id>", methods=["PUT"])
@admin_required
def update_navigation_item(item_id):
    item = NavigationItem.query.get_or_404(item_id)
    data = request.get_json() or {}

    if "label" in data:
        item.label = (data["label"] or "").strip() or item.label

    if "target_type" in data:
        item.target_type = data["target_type"]

    if "target_url" in data:
        item.target_url = data["target_url"]

    if "category_id" in data:
        item.category_id = int(data["category_id"]) if data["category_id"] else None

    if "page_id" in data:
        item.page_id = int(data["page_id"]) if data["page_id"] else None

    if "parent_id" in data:
        new_parent = int(data["parent_id"]) if data["parent_id"] else None
        if new_parent != item.id:  # prevent self-parenting
            item.parent_id = new_parent

    if "icon" in data:
        item.icon = data["icon"]

    if "visibility" in data:
        item.visibility = data["visibility"]

    if "is_active" in data:
        item.is_active = bool(data["is_active"])

    if "display_order" in data:
        item.display_order = int(data["display_order"])

    db.session.commit()

    ActivityLog.log(
        action="nav_updated",
        details=f"Updated navbar item '{item.label}'",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": "Navbar item updated successfully",
        "item": item.to_dict()
    })


@navigation_bp.route("/reorder", methods=["POST"])
@admin_required
def reorder_navigation():
    """
    Accepts JSON array of item IDs in order:
    {"order": [1, 5, 2, 8]}
    """
    data = request.get_json() or {}
    order_ids = data.get("order", [])
    if not isinstance(order_ids, list):
        return jsonify({"success": False, "error": "Invalid order format"}), 400

    for idx, item_id in enumerate(order_ids):
        NavigationItem.query.filter_by(id=item_id).update({"display_order": idx})

    db.session.commit()
    return jsonify({"success": True, "message": "Navbar items reordered successfully"})


@navigation_bp.route("/<int:item_id>", methods=["DELETE"])
@admin_required
def delete_navigation_item(item_id):
    item = NavigationItem.query.get_or_404(item_id)
    label = item.label

    db.session.delete(item)
    db.session.commit()

    ActivityLog.log(
        action="nav_deleted",
        details=f"Deleted navbar item '{label}'",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": f"Navbar item '{label}' deleted successfully"})
