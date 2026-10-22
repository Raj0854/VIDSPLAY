from datetime import datetime
from . import db


class Page(db.Model):
    __tablename__ = "pages"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    meta_description = db.Column(db.String(300), nullable=True)
    template = db.Column(db.String(50), default="default", nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sections = db.relationship(
        "PageSection",
        backref="page",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="PageSection.display_order",
    )
    nav_items = db.relationship("NavigationItem", backref="page", lazy=True)

    def to_dict(self, include_sections=True):
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "meta_description": self.meta_description or "",
            "template": self.template,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sections and self.sections:
            data["sections"] = [s.to_dict() for s in self.sections]
        else:
            data["sections"] = []
        return data

    def __repr__(self):
        return f"<Page {self.title} (/pages/{self.slug})>"


class PageSection(db.Model):
    __tablename__ = "page_sections"

    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    section_type = db.Column(db.String(50), nullable=False)
    # Types: 'hero', 'featured_video', 'video_grid', 'carousel', 'category_grid', 'banner', 'text'
    title = db.Column(db.String(150), nullable=True)
    subtitle = db.Column(db.String(255), nullable=True)
    config = db.Column(db.JSON, nullable=True, default=dict)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "page_id": self.page_id,
            "section_type": self.section_type,
            "title": self.title or "",
            "subtitle": self.subtitle or "",
            "config": self.config or {},
            "display_order": self.display_order,
            "is_visible": self.is_visible,
        }

    def __repr__(self):
        return f"<PageSection {self.section_type} (Order {self.display_order})>"
