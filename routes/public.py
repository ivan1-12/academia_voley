from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_babel import gettext as _
from flask_login import current_user
from models import get_db
from validators import validar_formato_email

def _tabla_tiene_columna(cur, tabla, columna):
    try:
        cur.execute(f"SHOW COLUMNS FROM {tabla} LIKE %s", (columna,))
        return cur.fetchone() is not None
    except Exception:
        return False

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    galeria = []
    logros = []
    try:
        cur = get_db().cursor()
        cur.execute("SELECT * FROM galeria ORDER BY fecha_subida DESC LIMIT 6")
        galeria = cur.fetchall()
        cur.execute("SELECT * FROM logros ORDER BY fecha_logro DESC LIMIT 6")
        logros = cur.fetchall()
        cur.close()
    except Exception:
        current_app.logger.exception("Error cargando datos del inicio")

    return render_template("index.html", galeria=galeria, logros=logros)


@public_bp.route("/perfil_academico")
def perfil_academico():
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, nombre, apellido, email, descripcion, link_facebook, link_instagram FROM usuarios WHERE rol = 'entrenador'"
    )
    staff_members = cur.fetchall()
    horarios_map = {}
    if staff_members:
        trainer_ids = [member["id"] for member in staff_members]
        format_ids = ",".join(["%s"] * len(trainer_ids))
        cur.execute(
            f"SELECT * FROM horarios_entrenador WHERE entrenador_id IN ({format_ids}) ORDER BY entrenador_id, creado_at DESC",
            tuple(trainer_ids),
        )
        horarios = cur.fetchall()
        for horario in horarios:
            horarios_map.setdefault(horario["entrenador_id"], []).append(horario)
    cur.close()
    return render_template(
        "perfil_academico.html", staff_members=staff_members, horarios_map=horarios_map
    )


@public_bp.route("/solicitar_unirse/<int:trainer_id>", methods=["GET", "POST"])
def solicitar_unirse(trainer_id):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, nombre, apellido, email, descripcion FROM usuarios WHERE id = %s AND rol = 'entrenador'",
        (trainer_id,),
    )
    trainer = cur.fetchone()
    horarios = []
    if not trainer:
        cur.close()
        flash(_("Entrenador no encontrado."), "danger")
        return redirect(url_for("public.perfil_academico"))

    cur.execute(
        "SELECT * FROM horarios_entrenador WHERE entrenador_id = %s ORDER BY creado_at DESC",
        (trainer_id,),
    )
    horarios = cur.fetchall()
    cur.close()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        mensaje = request.form.get("mensaje", "").strip()

        errors = []
        if not nombre:
            errors.append(_("El nombre es obligatorio."))
        if not email:
            errors.append(_("El email es obligatorio."))
        elif not validar_formato_email(email):
            errors.append(_("El correo electrónico no tiene un formato válido."))
        if not mensaje:
            errors.append(_("Describe brevemente por qué quieres unirte al equipo."))

        if errors:
            for err in errors:
                flash(_(err), "danger")
            return render_template(
                "solicitud_unirse.html",
                trainer=trainer,
                horarios=horarios,
                nombre=nombre,
                email=email,
                telefono=telefono,
                mensaje=mensaje,
            )

        db = get_db()
        cur = db.cursor()
        try:
            # Todas las solicitudes enviadas desde la página de un entrenador se consideran
            # solicitudes por staff / equipo, incluso si el email no existe aún.
            tipo = "academia"

            cur.execute(
                "INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, tipo) VALUES (%s, %s, %s, %s, %s, %s)",
                (trainer_id, nombre, email, telefono, mensaje, tipo),
            )
            db.commit()
            flash(_("Solicitud enviada correctamente. El entrenador revisará tu petición pronto."),
                "success",
            )
            return redirect(url_for("public.perfil_academico"))
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error guardando solicitud: %s", e)
            flash(_("Error al enviar la solicitud. Intenta nuevamente."), "danger")
        finally:
            cur.close()

    return render_template("solicitud_unirse.html", trainer=trainer, horarios=horarios)


@public_bp.route("/galeria_publica")
def galeria_publica():
    tipos = []
    try:
        cur = get_db().cursor()
        cur.execute(
            "SELECT g.*, u.nombre AS entrenador_nombre, u.apellido AS entrenador_apellido "
            "FROM galeria g LEFT JOIN usuarios u ON g.usuario_id = u.id "
            "ORDER BY g.fecha_subida DESC"
        )
        galeria = cur.fetchall()
        cur.execute(
            "SELECT DISTINCT tipo FROM galeria WHERE tipo IS NOT NULL AND tipo != '' ORDER BY tipo"
        )
        tipos = [row["tipo"] for row in cur.fetchall()]
        cur.close()
    except Exception:
        current_app.logger.exception("Error cargando galería pública")
        galeria = []

    return render_template("galeria.html", galeria=galeria, galeria_tipos=tipos)


@public_bp.route("/set_language", methods=["GET"])
def set_language():
    lang = request.args.get("lang", "es")
    supported = current_app.config.get("BABEL_SUPPORTED_LOCALES", ["es"])
    if lang not in supported:
        lang = current_app.config.get("BABEL_DEFAULT_LOCALE", "es")
    session["lang"] = lang

    # Si el usuario está autenticado, guardar preferencia en la base de datos
    try:
        if current_user.is_authenticated:
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "UPDATE usuarios SET idioma = %s WHERE id = %s", (lang, current_user.id)
            )
            db.commit()
            cur.close()
    except Exception:
        current_app.logger.exception(
            "No se pudo guardar el idioma en el perfil del usuario"
        )

    ref = request.referrer
    if ref:
        return redirect(ref)
    return redirect(url_for("public.index"))
