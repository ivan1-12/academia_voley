from flask import request
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_babel import Babel, lazy_gettext as _
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hashlib


def get_client_rate_limit_key():
    address = get_remote_address()
    user_agent = request.headers.get("User-Agent", "")
    if not user_agent:
        return address
    key = f"{address}|{user_agent}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

# Instancias globales de las extensiones
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_client_rate_limit_key,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://",
    enabled=False,
)
babel = Babel()

# Configuración básica de LoginManager
login_manager.login_view = "auth.login"
login_manager.login_message = _("Por favor inicia sesión para acceder a esta página")
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"
