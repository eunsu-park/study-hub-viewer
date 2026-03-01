"""Configuration for the Multi-User Study Viewer application."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
_STUDY_HUB = Path(os.environ.get("STUDY_HUB_PATH", BASE_DIR.parent))
CONTENT_DIR = _STUDY_HUB / "content"
EXAMPLES_DIR = _STUDY_HUB / "examples"
EXERCISES_DIR = _STUDY_HUB / "exercises"


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'data.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CONTENT_DIR = CONTENT_DIR
    EXAMPLES_DIR = EXAMPLES_DIR
    EXERCISES_DIR = EXERCISES_DIR

    # Language settings
    SUPPORTED_LANGUAGES = ["ko", "en"]
    DEFAULT_LANGUAGE = "ko"
    LANGUAGE_NAMES = {
        "ko": "한국어",
        "en": "English",
    }

    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    BCRYPT_LOG_ROUNDS = 12
    REMEMBER_COOKIE_DURATION = 30 * 24 * 60 * 60  # 30 days in seconds


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        if not self.SECRET_KEY:
            raise RuntimeError("SECRET_KEY environment variable must be set in production")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
