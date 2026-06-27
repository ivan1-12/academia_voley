from flask import current_app, g, redirect, url_for, flash, abort
from flask_babel import gettext as _
from flask_login import UserMixin, current_user
import pymysql.cursors
from extensions import login_manager
from functools import wraps


class User(UserMixin):
    def __init__(self, id, nombre, apellido, email, rol, permisos=None, telefono=None):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.email = email
        self.rol = rol
        self.telefono = telefono
        self.permisos = permisos or set()

    def has_permission(self, permiso):
        # El rol super_usuario tiene acceso total por defecto
        if self.rol == "super_usuario":
            return True
        return permiso in self.permisos


# Mapeo de permisos fallback por seguridad en caso de fallos de DB
FALLBACK_PERMISOS = {
    "super_usuario": {
        "modificar_entrenadores",
        "modificar_jugadores",
        "gestionar_branding",
        "gestionar_staff",
        "editar_contenido_inicio",
        "recomendar_rutinas",
        "gestionar_perfil_deportivo",
        "recomendar_nutricion",
        "editar_staff_propio",
    },
    "entrenador": {
        "recomendar_rutinas",
        "gestionar_perfil_deportivo",
        "recomendar_nutricion",
        "editar_staff_propio",
    },
    "jugador": set(),
}


def get_db():
    if "db" not in g:
        host = current_app.config.get("MYSQL_HOST", "localhost")
        user = current_app.config.get("MYSQL_USER", "root")
        password = current_app.config.get("MYSQL_PASSWORD", "")
        db_name = current_app.config.get("MYSQL_DB", "")
        configured_port = int(current_app.config.get("MYSQL_PORT", 3307))
        ports = [configured_port]
        for fallback_port in (3306, 3307):
            if fallback_port not in ports:
                ports.append(fallback_port)

        last_error = None
        for port in ports:
            try:
                g.db = pymysql.connect(
                    host=host,
                    user=user,
                    password=password,
                    db=db_name,
                    port=port,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,
                )
                if port != configured_port:
                    current_app.logger.warning(
                        "Conexión a MySQL establecida usando el puerto %s (fallback de %s)",
                        port,
                        configured_port,
                    )
                break
            except Exception as exc:
                last_error = exc
        else:
            raise last_error
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            current_app.logger.exception("Error cerrando conexión DB")


@login_manager.user_loader
def load_user(user_id):
    try:
        cur = get_db().cursor()
        # Intentamos obtener el usuario y el nombre de su rol mediante el ID de rol
        cur.execute(
            """
            SELECT u.*, r.nombre AS rol_nombre 
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE u.id = %s
        """,
            (user_id,),
        )
        user = cur.fetchone()

        if user:
            # Determinamos el rol (priorizando rol_nombre del sistema RBAC)
            rol_actual = user.get("rol_nombre") or user.get("rol") or "jugador"

            # Cargar permisos desde la base de datos (RBAC)
            permisos = set()
            try:
                if user.get("rol_id"):
                    cur.execute(
                        """
                        SELECT p.nombre 
                        FROM rol_permiso rp
                        JOIN permisos p ON rp.permiso_id = p.id
                        WHERE rp.rol_id = %s
                    """,
                        (user["rol_id"],),
                    )
                    permisos_rows = cur.fetchall()
                    permisos = {p["nombre"] for p in permisos_rows}
            except Exception as e:
                current_app.logger.warning(
                    f"No se pudieron cargar permisos de la DB para el usuario {user_id}: {e}"
                )

            # Si no hay permisos cargados de la DB, usar fallback basado en el rol
            if not permisos:
                permisos = FALLBACK_PERMISOS.get(rol_actual, set())

            cur.close()
            return User(
                user["id"],
                user["nombre"],
                user["apellido"],
                user["email"],
                rol_actual,
                permisos,
                telefono=user.get("telefono"),
            )

        cur.close()
    except Exception as e:
        current_app.logger.exception(f"Error en load_user para user_id {user_id}: {e}")
        # Fallback básico si hay algún problema con la base de datos o estructura incompleta
        try:
            cur = get_db().cursor()
            cur.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
            user = cur.fetchone()
            cur.close()
            if user:
                rol_actual = user.get("rol", "jugador")
                permisos = FALLBACK_PERMISOS.get(rol_actual, set())
                return User(
                    user["id"],
                    user["nombre"],
                    user["apellido"],
                    user["email"],
                    rol_actual,
                    permisos,
                )
        except Exception:
            pass
    return None


def permiso_requerido(permiso):
    """Decorador para restringir el acceso a usuarios que tengan el permiso especificado."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash(_("Por favor inicia sesión para acceder a esta sección."), "warning")
                return redirect(url_for("auth.login"))
            if not current_user.has_permission(permiso):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def rol_requerido(*roles):
    """Decorador para restringir el acceso a usuarios con alguno de los roles especificados."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash(_("Por favor inicia sesión para acceder a esta sección."), "warning")
                return redirect(url_for("auth.login"))
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator
