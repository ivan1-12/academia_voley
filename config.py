import os
import secrets
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "academia_voley")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3307))

    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@academiavoley.net")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "AcaVoley!2026")

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join("static", "uploads"))
    ALLOWED_EXTENSIONS = set(
        os.environ.get("ALLOWED_EXTENSIONS", "png,jpg,jpeg,gif,webp,svg").split(",")
    )
    LOGO_EXTENSIONS = set(
        os.environ.get("LOGO_EXTENSIONS", "png,jpg,jpeg,webp,svg").split(",")
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    BABEL_DEFAULT_LOCALE = os.environ.get("BABEL_DEFAULT_LOCALE", "es")
    BABEL_DEFAULT_TIMEZONE = os.environ.get("BABEL_DEFAULT_TIMEZONE", "UTC")
    BABEL_TRANSLATION_DIRECTORIES = os.environ.get(
        "BABEL_TRANSLATION_DIRECTORIES", "translations"
    )
    BABEL_SUPPORTED_LOCALES = os.environ.get(
        "BABEL_SUPPORTED_LOCALES", "es,en,pt,fr"
    ).split(",")

    # Feature flags
    ALLOW_SUPERUSER_CREATE_TRAINERS = os.environ.get(
        "ALLOW_SUPERUSER_CREATE_TRAINERS", "1"
    ).lower() in ("1", "true", "yes")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_TIME_LIMIT = 3600
    PASSWORD_RESET_EXPIRATION = int(os.environ.get("PASSWORD_RESET_EXPIRATION", 3600))

    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    # Por defecto escuchar en todas las interfaces para permitir acceso desde móviles
    FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))

    # Mínimo de segundos entre escrituras de last_activity por usuario
    LAST_ACTIVITY_INTERVAL = int(os.environ.get("LAST_ACTIVITY_INTERVAL", 120))
