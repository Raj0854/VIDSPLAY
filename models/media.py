from datetime import datetime
from . import db


class MediaAsset(db.Model):
    __tablename__ = "media_assets"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # Relative to app root or static
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)  # in bytes
    asset_type = db.Column(db.String(50), nullable=False, default="general")  # 'video', 'thumbnail', 'banner', 'general'
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_name": self.original_name,
            "file_path": f"/{self.file_path}" if not self.file_path.startswith("/") else self.file_path,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "asset_type": self.asset_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

    def __repr__(self):
        return f"<MediaAsset {self.filename} ({self.asset_type})>"
