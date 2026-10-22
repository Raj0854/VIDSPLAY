from datetime import datetime
from . import db


class NavigationItem(db.Model):
    __tablename__ = "navigation_items"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(20), nullable=False, default="category")  # 'category', 'page', 'custom'
    target_url = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    page_id = db.Column(db.Integer, db.ForeignKey("pages.id", ondelete="SET NULL"), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("navigation_items.id", ondelete="CASCADE"), nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    visibility = db.Column(db.String(20), default="all", nullable=False)  # 'all', 'desktop', 'mobile'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Self-referential relationship for nested dropdowns
    children = db.relationship(
        "NavigationItem",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        order_by="NavigationItem.display_order",
    )

    def get_resolved_url(self) -> str:
        """Resolve the final frontend URL based on target type."""
        if self.target_type == "category" and self.category:
            return f"/category/{self.category.slug}"
        elif self.target_type == "page" and self.page:
            return f"/pages/{self.page.slug}"
        return self.target_url or "#"

    def to_dict(self, include_children=True):
        data = {
            "id": self.id,
            "label": self.label,
            "target_type": self.target_type,
            "target_url": self.target_url or "",
            "resolved_url": self.get_resolved_url(),
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "page_id": self.page_id,
            "page_title": self.page.title if self.page else None,
            "parent_id": self.parent_id,
            "icon": self.icon or "",
            "display_order": self.display_order,
            "visibility": self.visibility,
            "is_active": self.is_active,
        }
        if include_children and self.children:
            data["children"] = [child.to_dict() for child in self.children if child.is_active]
        else:
            data["children"] = []
        return data

    def __repr__(self):
        return f"<NavigationItem {self.label} -> {self.get_resolved_url()}>"
