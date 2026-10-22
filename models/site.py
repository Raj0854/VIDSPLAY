from datetime import datetime
from . import db


class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @classmethod
    def get(cls, key: str, default=None):
        setting = db.session.get(cls, key)
        return setting.value if setting else default

    @classmethod
    def set(cls, key: str, value: str, description: str = None):
        setting = db.session.get(cls, key)
        if not setting:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        else:
            setting.value = value
            if description:
                setting.description = description
        db.session.commit()
        return setting

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @classmethod
    def log(cls, action: str, details: str = "", user_id: int = None, ip_address: str = None):
        entry = cls(
            action=action,
            details=details,
            user_id=user_id,
            ip_address=ip_address,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "System",
            "action": self.action,
            "details": self.details or "",
            "ip_address": self.ip_address or "",
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<ActivityLog {self.action} at {self.timestamp}>"
