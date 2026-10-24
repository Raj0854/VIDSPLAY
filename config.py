import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration settings."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-vidsplay-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 500 * 1024 * 1024))  # 500 MB
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "static/uploads")
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "ogg", "mov", "mkv"}
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "avif", "gif"}

    # Security headers & session settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    ENV = "development"
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'vidsplay_v2.db'}")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = True
    # In PostgreSQL, handle URI prefix if provider supplies postgres://
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url or f"sqlite:///{BASE_DIR / 'instance' / 'vidsplay_v2.db'}"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
