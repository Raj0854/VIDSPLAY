import re
from flask import Blueprint, request, jsonify
from flask_login import current_user
from models import db, Page, PageSection, NavigationItem, ActivityLog
from utils.auth_helpers import admin_required

pages_bp = Blueprint("api_pages", __name__, url_prefix="/api/pages")


def generate_unique_page_slug(title: str, existing_id: int = None) -> str:
    base_slug = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    base_slug = re.sub(r"[\s_-]+", "-", base_slug)
    if not base_slug:
        base_slug = "page"

    slug = base_slug
    counter = 1
    query = Page.query.filter_by(slug=slug)
    if existing_id:
        query = query.filter(Page.id != existing_id)

    while query.first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
        query = Page.query.filter_by(slug=slug)
        if existing_id:
            query = query.filter(Page.id != existing_id)

    return slug


@pages_bp.route("", methods=["GET"])
def get_pages():
    """List pages. Public requests get is_published=True."""
    include_all = request.args.get("all", "0") == "1" and current_user.is_authenticated

    query = Page.query
    if not include_all:
        query = query.filter(Page.is_published == True)

    pages = query.order_by(Page.id.desc()).all()
    return jsonify({
        "success": True,
        "pages": [p.to_dict(include_sections=False) for p in pages]
    })


@pages_bp.route("/<identifier>", methods=["GET"])
def get_page(identifier):
    """Get page details with all sections by ID or slug."""
    if identifier.isdigit():
        page = Page.query.get(int(identifier))
    else:
        page = Page.query.filter_by(slug=identifier).first()

    if not page:
        return jsonify({"success": False, "error": "Page not found"}), 404

    # If draft and not admin
    if not page.is_published and not current_user.is_authenticated:
        return jsonify({"success": False, "error": "Page not found"}), 404

    return jsonify({"success": True, "page": page.to_dict(include_sections=True)})


@pages_bp.route("", methods=["POST"])
@admin_required
def create_page():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "Page title is required"}), 400

    slug = (data.get("slug") or "").strip()
    if not slug:
        slug = generate_unique_page_slug(title)
    else:
        slug = generate_unique_page_slug(slug)

    meta_description = data.get("meta_description", "")
    template = data.get("template", "default")
    is_published = bool(data.get("is_published", True))
    add_to_navbar = bool(data.get("add_to_navbar", False))

    page = Page(
        title=title,
        slug=slug,
        meta_description=meta_description,
        template=template,
        is_published=is_published,
    )
    db.session.add(page)
    db.session.flush()  # to get page.id

    # Optional default hero section
    default_section = PageSection(
        page_id=page.id,
        section_type="hero",
        title=f"Welcome to {title}",
        subtitle=meta_description or "Explore our curated video collection.",
        config={"bg_color": "dark", "align": "center"},
        display_order=0,
        is_visible=True,
    )
    db.session.add(default_section)

    # Optional auto-add to navbar
    if add_to_navbar:
        max_order = db.session.query(db.func.max(NavigationItem.display_order)).scalar() or 0
        nav_item = NavigationItem(
            label=title,
            target_type="page",
            page_id=page.id,
            display_order=max_order + 1,
            visibility="all",
            is_active=True,
        )
        db.session.add(nav_item)

    db.session.commit()

    ActivityLog.log(
        action="page_created",
        details=f"Created page '{page.title}' (/pages/{page.slug})",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": "Page created successfully",
        "page": page.to_dict()
    }), 201


@pages_bp.route("/<int:page_id>", methods=["PUT"])
@admin_required
def update_page(page_id):
    page = Page.query.get_or_404(page_id)
    data = request.get_json() or {}

    if "title" in data:
        new_title = (data["title"] or "").strip()
        if new_title and new_title != page.title:
            page.title = new_title
            if "slug" not in data or not data["slug"]:
                page.slug = generate_unique_page_slug(new_title, existing_id=page.id)

    if "slug" in data and data["slug"]:
        new_slug = (data["slug"] or "").strip()
        if new_slug != page.slug:
            page.slug = generate_unique_page_slug(new_slug, existing_id=page.id)

    if "meta_description" in data:
        page.meta_description = data["meta_description"]

    if "template" in data:
        page.template = data["template"]

    if "is_published" in data:
        page.is_published = bool(data["is_published"])

    db.session.commit()

    ActivityLog.log(
        action="page_updated",
        details=f"Updated page '{page.title}'",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": "Page updated successfully", "page": page.to_dict()})


@pages_bp.route("/<int:page_id>/duplicate", methods=["POST"])
@admin_required
def duplicate_page(page_id):
    source = Page.query.get_or_404(page_id)
    new_title = f"{source.title} (Copy)"
    new_slug = generate_unique_page_slug(new_title)

    new_page = Page(
        title=new_title,
        slug=new_slug,
        meta_description=source.meta_description,
        template=source.template,
        is_published=False,  # Draft by default
    )
    db.session.add(new_page)
    db.session.flush()

    for sec in source.sections:
        new_sec = PageSection(
            page_id=new_page.id,
            section_type=sec.section_type,
            title=sec.title,
            subtitle=sec.subtitle,
            config=dict(sec.config or {}),
            display_order=sec.display_order,
            is_visible=sec.is_visible,
        )
        db.session.add(new_sec)

    db.session.commit()

    ActivityLog.log(
        action="page_duplicated",
        details=f"Duplicated page '{source.title}' to '{new_page.title}'",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": "Page duplicated successfully", "page": new_page.to_dict()}), 201


@pages_bp.route("/<int:page_id>", methods=["DELETE"])
@admin_required
def delete_page(page_id):
    page = Page.query.get_or_404(page_id)
    title = page.title

    db.session.delete(page)
    db.session.commit()

    ActivityLog.log(
        action="page_deleted",
        details=f"Deleted page '{title}'",
        user_id=current_user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": f"Page '{title}' deleted successfully"})


# --- Section Builder Endpoints ---

@pages_bp.route("/<int:page_id>/sections", methods=["POST"])
@admin_required
def add_section(page_id):
    page = Page.query.get_or_404(page_id)
    data = request.get_json() or {}

    section_type = data.get("section_type", "video_grid")
    title = data.get("title", "")
    subtitle = data.get("subtitle", "")
    config = data.get("config", {})
    is_visible = bool(data.get("is_visible", True))

    max_order = (
        db.session.query(db.func.max(PageSection.display_order))
        .filter_by(page_id=page.id)
        .scalar()
        or 0
    )

    section = PageSection(
        page_id=page.id,
        section_type=section_type,
        title=title,
        subtitle=subtitle,
        config=config,
        display_order=max_order + 1,
        is_visible=is_visible,
    )
    db.session.add(section)
    db.session.commit()

    return jsonify({"success": True, "message": "Section added successfully", "section": section.to_dict()}), 201


@pages_bp.route("/sections/<int:section_id>", methods=["PUT"])
@admin_required
def update_section(section_id):
    section = PageSection.query.get_or_404(section_id)
    data = request.get_json() or {}

    if "title" in data:
        section.title = data["title"]
    if "subtitle" in data:
        section.subtitle = data["subtitle"]
    if "config" in data:
        section.config = data["config"]
    if "is_visible" in data:
        section.is_visible = bool(data["is_visible"])
    if "section_type" in data:
        section.section_type = data["section_type"]

    db.session.commit()
    return jsonify({"success": True, "message": "Section updated successfully", "section": section.to_dict()})


@pages_bp.route("/sections/<int:section_id>", methods=["DELETE"])
@admin_required
def delete_section(section_id):
    section = PageSection.query.get_or_404(section_id)
    db.session.delete(section)
    db.session.commit()
    return jsonify({"success": True, "message": "Section deleted successfully"})


@pages_bp.route("/<int:page_id>/sections/reorder", methods=["POST"])
@admin_required
def reorder_sections(page_id):
    data = request.get_json() or {}
    order_ids = data.get("order", [])
    if not isinstance(order_ids, list):
        return jsonify({"success": False, "error": "Invalid order format"}), 400

    for idx, sec_id in enumerate(order_ids):
        PageSection.query.filter_by(id=sec_id, page_id=page_id).update({"display_order": idx})

    db.session.commit()
    return jsonify({"success": True, "message": "Sections reordered successfully"})
