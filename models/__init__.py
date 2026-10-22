from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models for easy access and Alembic discovery
from .user import AdminUser
from .category import Category
from .video import Video
from .navigation import NavigationItem
from .page import Page, PageSection
from .media import MediaAsset
from .site import SiteSetting, ActivityLog

__all__ = [
    "db",
    "AdminUser",
    "Category",
    "Video",
    "NavigationItem",
    "Page",
    "PageSection",
    "MediaAsset",
    "SiteSetting",
    "ActivityLog",
]
