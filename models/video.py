from datetime import datetime
from . import db


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    source_type = db.Column(db.String(20), nullable=False, default="youtube")  # 'local', 'youtube', 'external'
    source_url = db.Column(db.String(500), nullable=True)
    storage_key = db.Column(db.String(500), nullable=True)  # Relative upload path for local files
    embed_code = db.Column(db.Text, nullable=True)  # YouTube ID e.g. 'g2EgLybo1Y4' or validated embed URL
    thumbnail_url = db.Column(db.String(500), nullable=True)
    views_count = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    duration = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def get_playback_url(self) -> str:
        """Return the direct or streaming URL for player."""
        if self.source_type == "local" and self.storage_key:
            return f"/{self.storage_key}" if not self.storage_key.startswith("/") else self.storage_key
        elif self.source_type == "youtube":
            return f"https://www.youtube.com/embed/{self.embed_code}" if self.embed_code else (self.source_url or "")
        return self.source_url or ""

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "description": self.description or "",
            "source_type": self.source_type,
            "source_url": self.source_url or "",
            "storage_key": self.storage_key or "",
            "embed_code": self.embed_code or "",
            "thumbnail_url": self.thumbnail_url or "/static/img/logo.png",
            "playback_url": self.get_playback_url(),
            "views_count": self.views_count,
            "is_published": self.is_published,
            "is_featured": self.is_featured,
            "duration": self.duration or "",
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Uncategorized",
            "category_slug": self.category.slug if self.category else "uncategorized",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Video {self.title}>"
