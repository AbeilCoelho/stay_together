from datetime import timedelta
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session/Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"  # Use 'Strict' in production
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # In production, set these to True
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
