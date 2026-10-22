from datetime import datetime
from . import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(80), nullable=True, default="bi-folder")
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    videos = db.relationship("Video", backref="category", lazy=True, cascade="all")
    nav_items = db.relationship("NavigationItem", backref="category", lazy=True)

    def to_dict(self, include_video_count=True):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description or "",
            "icon": self.icon or "bi-folder",
            "display_order": self.display_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_video_count:
            data["video_count"] = len(self.videos) if self.videos else 0
        return data

    def __repr__(self):
        return f"<Category {self.name}>"
