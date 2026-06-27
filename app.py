from flask import Flask, render_template, request, g, url_for, redirect, flash
from flask_wtf.csrf import CSRFError, generate_csrf
from config import Config
from extensions import bcrypt, login_manager, csrf, babel, limiter
from models import get_db, close_db
from flask_login import current_user
from flask_babel import gettext as _, get_locale as _get_babel_locale
from utils.branding import resolve_brand_logo
import os
import socket
import time
from datetime import datetime, timezone
import logging

from routes.public import public_bp
from routes.auth import auth_bp
from routes.auth_reset import reset_bp
from routes.graphql_api import graphql_bp
from routes.player import player_bp
from routes.trainer import trainer_bp
from routes.reports import reports_bp

app = Flask(__name__)
app.config.from_object(Config)
app.config.setdefault("RATELIMIT_ENABLED", not app.config.get("TESTING", False))
if app.config.get("TESTING", False):
    app.config["RATELIMIT_ENABLED"] = False

logging.basicConfig(level=logging.WARNING)
werkzeug_logger = logging.getLogger("werkzeug")
if app.config.get("FLASK_DEBUG"):
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.propagate = True
    werkzeug_logger.disabled = False
else:
    werkzeug_logger.setLevel(logging.ERROR)
    werkzeug_logger.propagate = False
    werkzeug_logger.disabled = True
app.logger.setLevel(logging.WARNING)

app.config["MYSQL_CURSORCLASS"] = "DictCursor"


def get_locale():
    from flask import session

    supported = app.config.get("BABEL_SUPPORTED_LOCALES", ["es"])
    try:
        lang = session.get("lang")
        if lang in supported:
            return lang
    except Exception:
        pass

    best = request.accept_languages.best_match(supported)
    return best or app.config.get("BABEL_DEFAULT_LOCALE", "es")


bcrypt.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
limiter.init_app(app)
babel.init_app(app, locale_selector=get_locale)


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash(_("Invalid CSRF token. Please try again."), "danger")
    return redirect(request.referrer or url_for("public.index"))


@app.before_request
def _log_resolved_locale():
    try:
        # Loguear el locale resuelto para depuración
        resolved = _get_babel_locale()
        app.logger.debug(f"Resolved locale: {resolved}")
    except Exception:
        pass


@app.before_request
def _sync_rate_limit_state():
    testing = app.config.get("TESTING", False)
    app.config["RATELIMIT_ENABLED"] = not testing
    try:
        limiter.enabled = not testing
    except Exception:
        pass


app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(reset_bp)
app.register_blueprint(graphql_bp)
app.register_blueprint(player_bp)
app.register_blueprint(trainer_bp)
app.register_blueprint(reports_bp)

app.teardown_appcontext(close_db)


@app.before_request
def update_last_activity():
    if not current_user.is_authenticated:
        return
    now_ts = time.time()
    last_ts = session_get_last_activity()
    interval = app.config.get("LAST_ACTIVITY_INTERVAL", 120)
    if last_ts and (now_ts - last_ts) < interval:
        return
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE usuarios SET last_activity = NOW() WHERE id = %s",
            (current_user.id,),
        )
        db.commit()
        g._last_activity_updated = now_ts
    except Exception as e:
        db.rollback()
        app.logger.warning(
            f"Error actualizando last_activity para usuario {current_user.id}: {e}"
        )
    finally:
        cur.close()


def session_get_last_activity():
    from flask import session

    return session.get("_last_activity_ts")


@app.after_request
def persist_last_activity_ts(response):
    if getattr(g, "_last_activity_updated", None):
        from flask import session

        session["_last_activity_ts"] = g._last_activity_updated
    return response


@app.after_request
def set_security_headers(response):
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=()")
    response.headers.setdefault("X-XSS-Protection", "0")
    return response


@app.context_processor
def inject_now():
    return {"now": lambda: datetime.now(timezone.utc)}


@app.context_processor
def inject_gettext():
    return dict(_=_)


@app.context_processor
def inject_supported_languages():
    supported = app.config.get("BABEL_SUPPORTED_LOCALES", ["es"])
    label_map = {
        "es": _("Español"),
        "en": _("English"),
        "pt": _("Português"),
        "fr": _("Français"),
    }
    return {
        "supported_languages": [(code, label_map.get(code, code)) for code in supported]
    }


@app.context_processor
def inject_feature_flags():
    try:
        return {
            "allow_create_trainers": app.config.get(
                "ALLOW_SUPERUSER_CREATE_TRAINERS", True
            )
        }
    except Exception:
        return {"allow_create_trainers": True}


@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


@app.context_processor
def inject_social_links():
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT link_facebook, link_instagram FROM usuarios "
            "WHERE rol = 'entrenador' ORDER BY id ASC LIMIT 1"
        )
        social = cur.fetchone()
        cur.close()
        if social:
            return dict(
                academy_fb=social.get("link_facebook"),
                academy_ig=social.get("link_instagram"),
            )
    except Exception:
        app.logger.exception("Error cargando enlaces sociales")
    return dict(academy_fb=None, academy_ig=None)


@app.context_processor
def inject_brand_logo():
    rel = resolve_brand_logo(app.static_folder)
    if rel:
        return dict(brand_logo_url=url_for("static", filename=rel))
    return dict(brand_logo_url=url_for("static", filename="images/logo.svg"))


@app.template_global()
def get_color_dificultad(dificultad):
    colores = {
        "Principiante": "principiante",
        "principiante": "principiante",
        "facil": "principiante",
        "Intermedio": "intermedio",
        "intermedio": "intermedio",
        "medio": "intermedio",
        "Avanzado": "avanzado",
        "avanzado": "avanzado",
        "dificil": "avanzado",
    }
    return colores.get(dificultad, "principiante")


@app.template_global()
def get_badge_dificultad(dificultad):
    badges = {
        "Principiante": "success",
        "principiante": "success",
        "facil": "success",
        "Intermedio": "warning",
        "intermedio": "warning",
        "medio": "warning",
        "Avanzado": "danger",
        "avanzado": "danger",
        "dificil": "danger",
    }
    return badges.get(dificultad, "secondary")


@app.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    app.logger.exception("Error interno del servidor")
    return render_template("errors/500.html"), 500


def get_local_ipv4_addresses():
    addresses = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            addresses.add(s.getsockname()[0])
    except OSError:
        pass

    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip and not ip.startswith("127."):
                addresses.add(ip)
    except socket.gaierror:
        pass

    if not addresses:
        addresses.add("127.0.0.1")
    return sorted(addresses)


def print_access_info(host, port):
    addresses = get_local_ipv4_addresses()
    print(f"Local: http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        for ip in addresses:
            if ip != "127.0.0.1":
                print(f"LAN:   http://{ip}:{port}")
                break
    else:
        print(f"Host:  http://{host}:{port}")
    print("")


if __name__ == "__main__":
    if not os.environ.get("SECRET_KEY"):
        app.logger.warning(
            "SECRET_KEY no está definida en .env; las sesiones se invalidarán al reiniciar."
        )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join("static", "images"), exist_ok=True)
    host = app.config["FLASK_HOST"]
    port = app.config["FLASK_PORT"]

    # Si la configuración indica localhost, automáticamente enlazamos a 0.0.0.0
    # para facilitar el acceso desde teléfonos en la misma red local.
    run_host = host
    if host in ("127.0.0.1", "localhost"):
        run_host = "0.0.0.0"

    print_access_info(run_host, port)
    app.run(
        host=run_host,
        port=port,
        debug=app.config["FLASK_DEBUG"],
        use_debugger=app.config["FLASK_DEBUG"],
        use_reloader=app.config["FLASK_DEBUG"],
    )
