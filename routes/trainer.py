from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, abort
from flask_babel import gettext as _
from flask_login import login_required, current_user
from models import get_db, rol_requerido, permiso_requerido
from validators import (
    validar_nombre_texto,
    validar_descripcion_entrenador,
    validar_formato_email,
    validar_password_estricta,
)
from werkzeug.utils import secure_filename
from datetime import datetime
from utils.branding import LOGO_CANDIDATES
from extensions import bcrypt
import os
import random
import string


def generar_contraseña_aleatoria(length=12):
    caracteres = string.ascii_letters + string.digits + "@#$%&*!"
    return "".join(random.choice(caracteres) for _ in range(length))


trainer_bp = Blueprint("trainer", __name__)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


def allowed_logo(filename):
    return "." in filename and filename.rsplit(".", 1)[
        1
    ].lower() in current_app.config.get(
        "LOGO_EXTENSIONS", {"png", "jpg", "jpeg", "webp", "svg"}
    )


def _remove_existing_logos(images_dir):
    for name in LOGO_CANDIDATES:
        path = os.path.join(images_dir, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                current_app.logger.exception(
                    "No se pudo eliminar logo anterior: %s", path
                )


@trainer_bp.route("/dashboard_entrenador")
@login_required
@rol_requerido("entrenador", "super_usuario")
def dashboard_entrenador():
    db = get_db()
    cur = db.cursor()

    try:
        cur.execute("SELECT COUNT(*) as total FROM usuarios WHERE rol = 'jugador'")
        total_jugadores = cur.fetchone()
        total_jugadores = total_jugadores["total"] if total_jugadores else 0
    except Exception:
        total_jugadores = 0

    try:
        cur.execute("SELECT COUNT(*) as total FROM galeria")
        total_media = cur.fetchone()
        total_media = total_media["total"] if total_media else 0
    except Exception:
        total_media = 0

    try:
        cur.execute("SELECT * FROM usuarios WHERE rol = 'jugador'")
        jugadores = cur.fetchall()
    except Exception:
        jugadores = []

    try:
        cur.execute("SELECT * FROM galeria ORDER BY fecha_subida DESC")
        media = cur.fetchall()
    except Exception:
        media = []

    try:
        cur.execute("SELECT * FROM entrenamientos ORDER BY fecha_creacion DESC")
        entrenamientos = cur.fetchall()
    except Exception:
        entrenamientos = []

    try:
        cur.execute("SELECT * FROM nutricion")
        planes_nutricion = cur.fetchall()
    except Exception:
        planes_nutricion = []

    cur.close()

    # Nota: Hemos depurado la estadística de Asistencia que estaba hardcodeada en el HTML.
    return render_template(
        "dashboard_entrenador.html",
        total_jugadores=total_jugadores,
        total_media=total_media,
        jugadores=jugadores,
        media=media,
        entrenamientos=entrenamientos,
        planes_nutricion=planes_nutricion,
    )


@trainer_bp.route("/eliminar_jugador/<int:usuario_id>", methods=["POST"])
@login_required
@permiso_requerido("modificar_jugadores")
def eliminar_jugador(usuario_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "DELETE FROM asignacion_entrenamientos WHERE jugador_id = %s", (usuario_id,)
        )
        cur.execute(
            "DELETE FROM asignacion_nutricion WHERE jugador_id = %s", (usuario_id,)
        )
        cur.execute(
            "DELETE FROM perfiles_jugadores WHERE usuario_id = %s", (usuario_id,)
        )
        cur.execute(
            "DELETE FROM usuarios WHERE id = %s AND rol = 'jugador'", (usuario_id,)
        )
        db.commit()
        flash(_("Jugador eliminado correctamente"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando jugador: %s", e)
        flash(_("Error al eliminar jugador"), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.dashboard_entrenador"))


@trainer_bp.route("/eliminar_imagen/<int:imagen_id>", methods=["POST"])
@login_required
@rol_requerido("entrenador", "super_usuario")
def eliminar_imagen(imagen_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT imagen_url FROM galeria WHERE id = %s", (imagen_id,))
        fila = cur.fetchone()
        if fila:
            imagen_url = fila.get("imagen_url")
            if imagen_url:
                path = imagen_url.lstrip("/")
                full_path = os.path.join(os.getcwd(), path)
                try:
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception:
                    current_app.logger.exception(
                        "No se pudo eliminar archivo: %s", full_path
                    )
        cur.execute("DELETE FROM galeria WHERE id = %s", (imagen_id,))
        db.commit()
        flash(_("Imagen eliminada correctamente"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando imagen: %s", e)
        flash(_("Error al eliminar imagen"), "danger")
    finally:
        cur.close()

    ref = request.referrer
    if ref:
        return redirect(ref)
    return redirect(url_for("trainer.dashboard_entrenador"))


@trainer_bp.route("/editar_staff/<int:staff_id>", methods=["GET", "POST"])
@login_required
def editar_staff(staff_id):
    if current_user.rol == "entrenador":
        if current_user.id != staff_id:
            flash(_("No estás autorizado a editar el perfil de otro entrenador."), "danger"
            )
            return redirect(url_for("public.perfil_academico"))
    elif current_user.rol != "super_usuario":
        abort(403)

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        email = request.form.get("email", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        link_facebook = request.form.get("link_facebook", "").strip()
        link_instagram = request.form.get("link_instagram", "").strip()

        # Validaciones del lado del servidor
        errors = []
        if not nombre or not apellido:
            errors.append(_("Nombre y apellido son obligatorios."))

        if not validar_nombre_texto(nombre) or not validar_nombre_texto(apellido):
            errors.append(
                _("El nombre y el apellido deben contener únicamente letras y espacios.")
            )

        if not validar_descripcion_entrenador(descripcion):
            errors.append(
                _("La descripción o biografía profesional no debe superar los 150 caracteres.")
            )

        if email and not validar_formato_email(email):
            errors.append(_("El formato del correo electrónico no es válido."))

        if errors:
            for err in errors:
                flash(_(err), "danger")
            cur.execute(
                "SELECT * FROM usuarios WHERE id = %s AND rol = 'entrenador'",
                (staff_id,),
            )
            staff = cur.fetchone()
            cur.close()
            return render_template("editar_staff.html", staff=staff)

        try:
            cur.execute(
                "UPDATE usuarios SET nombre = %s, apellido = %s, email = %s, descripcion = %s, link_facebook = %s, link_instagram = %s WHERE id = %s AND rol = 'entrenador'",
                (
                    nombre,
                    apellido,
                    email,
                    descripcion,
                    link_facebook,
                    link_instagram,
                    staff_id,
                ),
            )
            db.commit()
            flash(_("Información del staff actualizada"), "success")
            return redirect(url_for("public.perfil_academico"))
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error actualizando staff: %s", e)
            flash(_("Error al actualizar información"), "danger")
        finally:
            cur.close()

    # GET
    try:
        cur.execute(
            "SELECT * FROM usuarios WHERE id = %s AND rol = 'entrenador'", (staff_id,)
        )
        staff = cur.fetchone()
    finally:
        cur.close()

    if not staff:
        flash(_("Staff no encontrado"), "warning")
        return redirect(url_for("public.perfil_academico"))

    return render_template("editar_staff.html", staff=staff)


@trainer_bp.route("/agregar_staff", methods=["GET", "POST"])
@login_required
@permiso_requerido("gestionar_staff")
def agregar_staff():
    if request.method == "POST":
        # Bloquear creación si la flag está deshabilitada en configuración
        try:
            if not current_app.config.get("ALLOW_SUPERUSER_CREATE_TRAINERS", True):
                flash(_("La creación de entrenadores está deshabilitada en la configuración."),
                    "warning",
                )
                return redirect(url_for("trainer.dashboard_entrenador"))
        except Exception:
            pass
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        descripcion = request.form.get("descripcion", "").strip()
        link_facebook = request.form.get("link_facebook", "").strip()
        link_instagram = request.form.get("link_instagram", "").strip()

        errors = []
        if not validar_nombre_texto(nombre) or not validar_nombre_texto(apellido):
            errors.append(
                _("Nombre y apellido deben contener letras, espacios, guiones o apóstrofes.")
            )
        if not validar_formato_email(email):
            errors.append(_("El correo electrónico no tiene un formato válido."))
        if password != confirm_password:
            errors.append(_("Las contraseñas no coinciden."))
        passwd_valido, passwd_msg = validar_password_estricta(password)
        if not passwd_valido:
            errors.append(_(passwd_msg))
        if not validar_descripcion_entrenador(descripcion):
            errors.append(_("La descripción no debe superar los 150 caracteres."))

        if errors:
            form_errors = {}
            for err in errors:
                if "nombre" in err.lower() or "apellido" in err.lower():
                    form_errors.setdefault("nombre", []).append(err)
                    form_errors.setdefault("apellido", []).append(err)
                elif "correo" in err.lower() or "email" in err.lower():
                    form_errors.setdefault("email", []).append(err)
                elif "contrase" in err.lower():
                    form_errors.setdefault("password", []).append(err)
                    form_errors.setdefault("confirm_password", []).append(err)
                elif "descripción" in err.lower() or "descripcion" in err.lower():
                    form_errors.setdefault("descripcion", []).append(err)
                else:
                    form_errors.setdefault("general", []).append(err)

            return render_template(
                "agregar_staff.html",
                nombre=nombre,
                apellido=apellido,
                email=email,
                descripcion=descripcion,
                link_facebook=link_facebook,
                link_instagram=link_instagram,
                form_errors=form_errors,
            )

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cur.fetchone():
                flash(_("Ese correo ya está registrado."), "danger")
                cur.close()
                return render_template(
                    "agregar_staff.html",
                    nombre=nombre,
                    apellido=apellido,
                    email=email,
                    descripcion=descripcion,
                    link_facebook=link_facebook,
                    link_instagram=link_instagram,
                )

            cur.execute("SELECT id FROM roles WHERE nombre = 'entrenador'")
            rol_row = cur.fetchone()
            if not rol_row:
                raise RuntimeError("No existe el rol entrenador en la base de datos.")
            rol_id = rol_row["id"]

            password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, descripcion, link_facebook, link_instagram) VALUES (%s, %s, %s, %s, 'entrenador', %s, %s, %s, %s)",
                (
                    nombre,
                    apellido,
                    email,
                    password_hash,
                    rol_id,
                    descripcion,
                    link_facebook,
                    link_instagram,
                ),
            )
            db.commit()
            flash(_("Entrenador agregado correctamente"), "success")
            return redirect(url_for("public.perfil_academico"))
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error creando entrenador: %s", e)
            if "No existe el rol entrenador" in str(e):
                flash(_("No se pudo crear el entrenador porque falta el rol entrenador en la base de datos. Contacta al administrador."),
                    "danger",
                )
            else:
                flash(_("Error al agregar el entrenador. Intenta nuevamente."), "danger")
        finally:
            try:
                cur.close()
            except Exception:
                pass

    return render_template("agregar_staff.html")


@trainer_bp.route("/gestion_usuarios")
@login_required
@rol_requerido("super_usuario")
def gestion_usuarios():
    search = request.args.get("search", "").strip()
    rol_filter = request.args.get("rol", "").strip()
    estado_filter = request.args.get("estado", "").strip()

    db = get_db()
    cur = db.cursor()
    usuarios = []
    try:
        query = "SELECT id, nombre, apellido, email, rol, activo FROM usuarios WHERE rol IN ('entrenador', 'jugador')"
        params = []

        if rol_filter in ("entrenador", "jugador"):
            query += " AND rol = %s"
            params.append(rol_filter)

        if estado_filter == "activo":
            query += " AND activo = 1"
        elif estado_filter == "inactivo":
            query += " AND activo = 0"

        if search:
            query += " AND (nombre LIKE %s OR apellido LIKE %s OR email LIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])

        query += " ORDER BY rol, nombre"
        cur.execute(query, params)
        usuarios = cur.fetchall()
    except Exception as e:
        current_app.logger.exception(
            "Error cargando usuarios en gestion_usuarios: %s", e
        )
        flash(_("Ocurrió un error al cargar los usuarios. Intenta nuevamente o revisa los logs."),
            "danger",
        )
    finally:
        cur.close()

    return render_template(
        "gestion_cuentas.html",
        usuarios=usuarios,
        search=search,
        rol_filter=rol_filter,
        estado_filter=estado_filter,
    )


@trainer_bp.route("/toggle_cuenta/<int:usuario_id>", methods=["POST"])
@login_required
@rol_requerido("super_usuario")
def toggle_cuenta(usuario_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT activo FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
        if not usuario:
            flash(_("Usuario no encontrado."), "warning")
            return redirect(url_for("trainer.gestion_usuarios"))

        nuevo_estado = 0 if usuario.get("activo") == 1 else 1
        cur.execute(
            "UPDATE usuarios SET activo = %s WHERE id = %s", (nuevo_estado, usuario_id)
        )
        db.commit()
        flash(_("Estado de la cuenta actualizado."), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error cambiando estado de cuenta: %s", e)
        flash(_("No se pudo actualizar el estado de la cuenta."), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.gestion_usuarios"))


@trainer_bp.route("/eliminar_descarga/<int:descarga_id>", methods=["POST"])
@login_required
@rol_requerido("super_usuario")
def eliminar_descarga(descarga_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM descargas_log WHERE id = %s", (descarga_id,))
        db.commit()
        flash(_("Entrada de descarga eliminada."), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando descarga: %s", e)
        flash(_("No se pudo eliminar la entrada de descarga."), "danger")
    finally:
        cur.close()

    ref = request.referrer
    if ref:
        return redirect(ref)
    return redirect(url_for("reports.reportes"))


@trainer_bp.route("/eliminar_descargas_rango", methods=["POST"])
@login_required
@rol_requerido("super_usuario")
def eliminar_descargas_rango():
    db = get_db()
    cur = db.cursor()
    rango = request.form.get("range", "all")
    try:
        if rango == "month":
            cur.execute(
                "DELETE FROM descargas_log WHERE fecha_descarga >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
            )
        elif rango == "week":
            cur.execute(
                "DELETE FROM descargas_log WHERE fecha_descarga >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
            )
        elif rango == "day":
            cur.execute(
                "DELETE FROM descargas_log WHERE fecha_descarga >= DATE_SUB(NOW(), INTERVAL 1 DAY)"
            )
        elif rango == "hour":
            cur.execute(
                "DELETE FROM descargas_log WHERE fecha_descarga >= DATE_SUB(NOW(), INTERVAL 1 HOUR)"
            )
        else:
            cur.execute("DELETE FROM descargas_log")

        db.commit()
        flash(_("Historial de descargas eliminado para el rango seleccionado."), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando descargas por rango: %s", e)
        flash(_("No se pudo eliminar el historial de descargas."), "danger")
    finally:
        cur.close()

    ref = request.referrer
    if ref:
        return redirect(ref)
    return redirect(url_for("reports.reportes"))


@trainer_bp.route("/editar_usuario/<int:usuario_id>", methods=["GET", "POST"])
@login_required
@rol_requerido("super_usuario")
def editar_usuario(usuario_id):
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        email = request.form.get("email", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        link_facebook = request.form.get("link_facebook", "").strip()
        link_instagram = request.form.get("link_instagram", "").strip()
        fecha_nacimiento = request.form.get("fecha_nacimiento")
        genero = request.form.get("genero", "").strip()
        cedula = request.form.get("cedula", "").strip()

        errors = []
        if not nombre or not apellido:
            errors.append(_("Nombre y apellido son obligatorios."))
        if email and not validar_formato_email(email):
            errors.append(_("El correo electrónico no tiene un formato válido."))

        if errors:
            for err in errors:
                flash(_(err), "danger")
            cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
            usuario = cur.fetchone()
            cur.close()
            return render_template("editar_usuario.html", usuario=usuario)

        try:
            # Validar duplicado de email
            cur.execute(
                "SELECT id FROM usuarios WHERE email = %s AND id != %s",
                (email, usuario_id),
            )
            if cur.fetchone():
                flash(_("El correo electrónico ya está en uso por otro usuario."), "danger"
                )
                cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
                usuario = cur.fetchone()
                cur.close()
                return render_template("editar_usuario.html", usuario=usuario)

            cur.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
            rol_row = cur.fetchone()
            if not rol_row:
                flash(_("Usuario no encontrado."), "warning")
                return redirect(url_for("trainer.gestion_usuarios"))

            if rol_row.get("rol") == "entrenador":
                cur.execute(
                    "UPDATE usuarios SET nombre = %s, apellido = %s, email = %s, descripcion = %s, link_facebook = %s, link_instagram = %s WHERE id = %s",
                    (
                        nombre,
                        apellido,
                        email,
                        descripcion,
                        link_facebook,
                        link_instagram,
                        usuario_id,
                    ),
                )
            else:
                cur.execute(
                    "UPDATE usuarios SET nombre = %s, apellido = %s, email = %s, fecha_nacimiento = %s, genero = %s, cedula = %s WHERE id = %s",
                    (
                        nombre,
                        apellido,
                        email,
                        fecha_nacimiento or None,
                        genero,
                        cedula,
                        usuario_id,
                    ),
                )

            db.commit()
            flash(_("Perfil actualizado correctamente."), "success")
            return redirect(url_for("trainer.gestion_usuarios"))
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error actualizando usuario: %s", e)
            flash(_("No se pudo actualizar el usuario. Intenta nuevamente."), "danger")
        finally:
            cur.close()

    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    usuario = cur.fetchone()
    cur.close()

    if not usuario:
        flash(_("Usuario no encontrado."), "warning")
        return redirect(url_for("trainer.gestion_usuarios"))

    return render_template("editar_usuario.html", usuario=usuario)


@trainer_bp.route("/cambiar_password_usuario/<int:usuario_id>", methods=["POST"])
@login_required
@rol_requerido("super_usuario")
def cambiar_password_usuario(usuario_id):
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if password != confirm_password:
        flash(_("Las contraseñas no coinciden."), "danger")
        return redirect(url_for("trainer.gestion_usuarios"))

    passwd_valido, passwd_msg = validar_password_estricta(password)
    if not passwd_valido:
        flash(passwd_msg, "danger")
        return redirect(url_for("trainer.gestion_usuarios"))

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT id FROM usuarios WHERE id = %s", (usuario_id,))
        if not cur.fetchone():
            flash(_("Usuario no encontrado."), "warning")
            return redirect(url_for("trainer.gestion_usuarios"))

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        cur.execute(
            "UPDATE usuarios SET password = %s WHERE id = %s",
            (password_hash, usuario_id),
        )
        db.commit()
        flash(_("Contraseña actualizada correctamente."), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error cambiando contraseña: %s", e)
        flash(_("Error al actualizar la contraseña. Intenta nuevamente."), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.gestion_usuarios"))


@trainer_bp.route("/gestion_entrenamientos", methods=["GET", "POST"])
@login_required
@permiso_requerido("recomendar_rutinas")
def gestion_entrenamientos():
    db = get_db()
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        ejercicios = request.form.get("ejercicios", "").strip()
        duracion = request.form.get("duracion")
        dificultad = request.form.get("dificultad", "").strip()
        imagen = request.files.get("imagen")
        imagen_url = None

        if (
            not titulo
            or not descripcion
            or not ejercicios
            or not duracion
            or not dificultad
        ):
            flash(_("Todos los campos son obligatorios"), "danger")
            return redirect(url_for("trainer.gestion_entrenamientos"))

        if imagen and imagen.filename:
            if allowed_file(imagen.filename):
                filename = secure_filename(imagen.filename)
                filename = (
                    f"entrenamiento_{int(datetime.utcnow().timestamp())}_{filename}"
                )
                upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"])
                os.makedirs(upload_path, exist_ok=True)
                imagen.save(os.path.join(upload_path, filename))
                imagen_url = f"/static/uploads/{filename}"
            else:
                flash(_("El archivo de imagen no tiene un formato compatible."), "danger")
                return redirect(url_for("trainer.gestion_entrenamientos"))

        cur = db.cursor()
        try:
            cur.execute(
                """INSERT INTO entrenamientos (titulo, descripcion, ejercicios, duracion_minutos, dificultad, imagen_url) 
                          VALUES (%s, %s, %s, %s, %s, %s)""",
                (titulo, descripcion, ejercicios, duracion, dificultad, imagen_url),
            )
            db.commit()
            flash(_("Entrenamiento creado exitosamente"), "success")
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error creando entrenamiento: %s", e)
            flash(_("Error al crear entrenamiento"), "danger")
        finally:
            cur.close()
        return redirect(url_for("trainer.gestion_entrenamientos"))

    cur = db.cursor()
    cur.execute("SELECT * FROM entrenamientos ORDER BY fecha_creacion DESC")
    entrenamientos = cur.fetchall()
    cur.close()

    return render_template("entrenamientos.html", entrenamientos=entrenamientos)


@trainer_bp.route("/asignar_entrenamiento", methods=["POST"])
@login_required
@permiso_requerido("recomendar_rutinas")
def asignar_entrenamiento():
    # Usar get para evitar KeyError y validar datos del formulario
    jugador_id = request.form.get("jugador_id")
    entrenamiento_id = request.form.get("entrenamiento_id")

    if not jugador_id or not entrenamiento_id:
        flash(_("Faltan datos para asignar el entrenamiento."), "warning")
        return redirect(url_for("trainer.dashboard_entrenador"))

    try:
        jugador_id = int(jugador_id)
        entrenamiento_id = int(entrenamiento_id)
    except ValueError:
        flash(_("Datos inválidos en el formulario de asignación."), "danger")
        return redirect(url_for("trainer.dashboard_entrenador"))

    db = get_db()
    cur = db.cursor()
    try:
        # Comprobar que el entrenamiento existe
        cur.execute("SELECT id FROM entrenamientos WHERE id = %s", (entrenamiento_id,))
        if not cur.fetchone():
            flash(_("El entrenamiento seleccionado no existe."), "danger")
            return redirect(url_for("trainer.dashboard_entrenador"))

        cur.execute(
            "SELECT 1 FROM asignacion_entrenamientos WHERE jugador_id = %s AND entrenamiento_id = %s",
            (jugador_id, entrenamiento_id),
        )
        if cur.fetchone():
            flash(_("Este entrenamiento ya estaba asignado a ese jugador."), "warning")
            return redirect(url_for("trainer.dashboard_entrenador"))

        cur.execute(
            "INSERT INTO asignacion_entrenamientos (jugador_id, entrenamiento_id, completado) VALUES (%s, %s, FALSE)",
            (jugador_id, entrenamiento_id),
        )
        db.commit()
        flash(_("Entrenamiento asignado exitosamente"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error asignando entrenamiento: %s", e)
        flash(_("Error al asignar entrenamiento"), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.dashboard_entrenador"))


@trainer_bp.route("/gestion_nutricion", methods=["GET", "POST"])
@login_required
@permiso_requerido("recomendar_nutricion")
def gestion_nutricion():
    db = get_db()
    if request.method == "POST":
        titulo = request.form["titulo"]
        desayuno = request.form["desayuno"]
        almuerzo = request.form["almuerzo"]
        cena = request.form["cena"]
        merienda = request.form["merienda"]
        hidratacion = request.form["hidratacion"]

        cur = db.cursor()
        try:
            cur.execute(
                """INSERT INTO nutricion (titulo, desayuno, almuerzo, cena, merienda, hidratacion) 
                          VALUES (%s, %s, %s, %s, %s, %s)""",
                (titulo, desayuno, almuerzo, cena, merienda, hidratacion),
            )
            db.commit()
            flash(_("Plan nutricional creado exitosamente"), "success")
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error creando plan nutricional: %s", e)
            flash(_("Error al crear plan nutricional"), "danger")
        finally:
            cur.close()
        return redirect(url_for("trainer.gestion_nutricion"))

    cur = db.cursor()
    cur.execute("SELECT * FROM nutricion")
    planes = cur.fetchall()
    cur.close()

    return render_template("nutricion.html", planes=planes)


@trainer_bp.route("/horarios_entrenador", methods=["GET", "POST"])
@login_required
@rol_requerido("entrenador", "super_usuario")
def horarios_entrenador():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        if current_user.rol != "entrenador":
            flash(_("Solo los entrenadores pueden agregar horarios."), "danger")
            cur.close()
            return redirect(url_for("trainer.horarios_entrenador"))

        entrenador_id = current_user.id
        dias = request.form.get("dias", "").strip()
        horario = request.form.get("horario", "").strip()
        precio = request.form.get("precio", "").strip()
        descripcion = request.form.get("descripcion", "").strip()

        if not dias or not horario or not precio:
            flash(_("Los campos Días, Horario y Precio son obligatorios."), "danger")
            cur.close()
            return redirect(url_for("trainer.horarios_entrenador"))

        try:
            cur.execute(
                "INSERT INTO horarios_entrenador (entrenador_id, dias, horario, precio, descripcion) VALUES (%s, %s, %s, %s, %s)",
                (entrenador_id, dias, horario, precio, descripcion),
            )
            db.commit()
            flash(_("Horario agregado correctamente."), "success")
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error agregando horario: %s", e)
            flash(_("Error al guardar el horario."), "danger")
        finally:
            cur.close()
        return redirect(url_for("trainer.horarios_entrenador"))

    if current_user.rol == "super_usuario":
        cur.execute(
            "SELECT h.*, u.nombre AS entrenador_nombre, u.apellido AS entrenador_apellido FROM horarios_entrenador h LEFT JOIN usuarios u ON h.entrenador_id = u.id ORDER BY h.creado_at DESC"
        )
    else:
        cur.execute(
            "SELECT * FROM horarios_entrenador WHERE entrenador_id = %s ORDER BY creado_at DESC",
            (current_user.id,),
        )
    horarios = cur.fetchall()
    cur.close()
    return render_template("horarios_entrenador.html", horarios=horarios)


@trainer_bp.route("/eliminar_horario/<int:horario_id>", methods=["POST"])
@login_required
@rol_requerido("entrenador", "super_usuario")
def eliminar_horario(horario_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT entrenador_id FROM horarios_entrenador WHERE id = %s", (horario_id,)
        )
        horario = cur.fetchone()
        if not horario:
            flash(_("Horario no encontrado."), "warning")
            return redirect(url_for("trainer.horarios_entrenador"))
        if (
            current_user.rol != "super_usuario"
            and horario["entrenador_id"] != current_user.id
        ):
            abort(403)
        cur.execute("DELETE FROM horarios_entrenador WHERE id = %s", (horario_id,))
        db.commit()
        flash(_("Horario eliminado correctamente."), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando horario: %s", e)
        flash(_("Error al eliminar el horario."), "danger")
    finally:
        cur.close()
    return redirect(url_for("trainer.horarios_entrenador"))


@trainer_bp.route("/solicitudes_equipo")
@login_required
@rol_requerido("entrenador", "super_usuario")
def solicitudes_equipo():
    tipo_filter = request.args.get("tipo", "").strip()
    db = get_db()
    cur = db.cursor()
    try:
        if current_user.rol == "super_usuario":
            query = "SELECT s.*, u.nombre AS entrenador_nombre, u.apellido AS entrenador_apellido FROM solicitudes_equipo s JOIN usuarios u ON s.entrenador_id = u.id"
            params = []
            if tipo_filter in ("nuevo", "academia"):
                query += " WHERE s.tipo = %s"
                params.append(tipo_filter)
            query += " ORDER BY s.creado_at DESC"
            cur.execute(query, params)
        else:
            query = "SELECT s.*, u.nombre AS entrenador_nombre, u.apellido AS entrenador_apellido FROM solicitudes_equipo s JOIN usuarios u ON s.entrenador_id = u.id WHERE s.entrenador_id = %s"
            params = [current_user.id]
            if tipo_filter in ("nuevo", "academia"):
                query += " AND s.tipo = %s"
                params.append(tipo_filter)
            query += " ORDER BY s.creado_at DESC"
            cur.execute(query, params)
        solicitudes = cur.fetchall()
    except Exception:
        solicitudes = []
    finally:
        cur.close()
    return render_template(
        "solicitudes_equipo.html", solicitudes=solicitudes, tipo_filter=tipo_filter
    )


@trainer_bp.route("/solicitudes_equipo/<int:solicitud_id>/procesar", methods=["POST"])
@login_required
@rol_requerido("entrenador", "super_usuario")
def procesar_solicitud_equipo(solicitud_id):
    accion = request.form.get("action")
    if accion not in ["aceptar", "rechazar"]:
        flash(_("Acción inválida."), "danger")
        return redirect(url_for("trainer.solicitudes_equipo"))

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT * FROM solicitudes_equipo WHERE id = %s", (solicitud_id,))
        solicitud = cur.fetchone()
        if not solicitud:
            flash(_("Solicitud no encontrada."), "warning")
            return redirect(url_for("trainer.solicitudes_equipo"))
        if (
            current_user.rol != "super_usuario"
            and solicitud["entrenador_id"] != current_user.id
        ):
            abort(403)

        if accion == "rechazar":
            cur.execute(
                "UPDATE solicitudes_equipo SET estado = 'rechazada' WHERE id = %s",
                (solicitud_id,),
            )
            db.commit()
            flash(_("Solicitud rechazada correctamente."), "success")
            return redirect(url_for("trainer.solicitudes_equipo"))

        # Aceptar la solicitud sin crear cuenta automáticamente
        cur.execute(
            "UPDATE solicitudes_equipo SET estado = 'aceptado' WHERE id = %s",
            (solicitud_id,),
        )
        db.commit()

        if solicitud.get("tipo") == "nuevo":
            flash(_("Solicitud aceptada. El solicitante podrá crear su perfil usando el mismo correo."),
                "success",
            )
        else:
            flash(_("Solicitud aceptada. El jugador de la academia fue puesto en espera para la creación de perfil."),
                "success",
            )
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error procesando solicitud: %s", e)
        flash(_("Error al procesar la solicitud. Intenta nuevamente."), "danger")
    finally:
        cur.close()
    return redirect(url_for("trainer.solicitudes_equipo"))


@trainer_bp.route("/asignar_nutricion", methods=["POST"])
@login_required
@permiso_requerido("recomendar_nutricion")
def asignar_nutricion():
    jugador_id = request.form["jugador_id"]
    nutricion_id = request.form["nutricion_id"]

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT * FROM asignacion_nutricion WHERE jugador_id = %s", (jugador_id,)
        )
        existente = cur.fetchone()

        if existente:
            cur.execute(
                "UPDATE asignacion_nutricion SET nutricion_id = %s WHERE jugador_id = %s",
                (nutricion_id, jugador_id),
            )
        else:
            cur.execute(
                "INSERT INTO asignacion_nutricion (jugador_id, nutricion_id) VALUES (%s, %s)",
                (jugador_id, nutricion_id),
            )

        db.commit()
        flash(_("Plan nutricional asignado exitosamente"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error asignando nutrición: %s", e)
        flash(_("Error al asignar plan nutricional"), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.dashboard_entrenador"))


@trainer_bp.route("/subir_foto", methods=["POST"])
@login_required
@rol_requerido("entrenador", "super_usuario")
def subir_foto():
    if "foto" not in request.files:
        flash(_("No se seleccionó ninguna foto"), "danger")
        return redirect(url_for("trainer.dashboard_entrenador"))

    foto = request.files["foto"]
    titulo = request.form.get("titulo", "")
    descripcion = request.form.get("descripcion", "")
    tipo = request.form.get("tipo", "equipo")

    if foto.filename == "":
        flash(_("No se seleccionó ninguna foto"), "danger")
        return redirect(url_for("trainer.dashboard_entrenador"))

    if foto and allowed_file(foto.filename):
        filename = secure_filename(foto.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + filename

        upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"])
        os.makedirs(upload_path, exist_ok=True)

        foto.save(os.path.join(upload_path, filename))

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                """INSERT INTO galeria (titulo, descripcion, imagen_url, tipo, fecha_subida) 
                      VALUES (%s, %s, %s, %s, NOW())""",
                (titulo, descripcion, f"/static/uploads/{filename}", tipo),
            )
            db.commit()
            flash(_("Foto subida exitosamente"), "success")
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error guardando imagen en BD: %s", e)
            flash(_("Error al subir foto"), "danger")
        finally:
            cur.close()
    else:
        flash(_("Formato de archivo no permitido"), "danger")

    return redirect(url_for("trainer.dashboard_entrenador"))


@trainer_bp.route("/gestion_logros", methods=["GET", "POST"])
@login_required
@rol_requerido("entrenador", "super_usuario")
def gestion_logros():
    db = get_db()
    if request.method == "POST":
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        fecha_logro = request.form["fecha_logro"]

        cur = db.cursor()
        try:
            cur.execute(
                "INSERT INTO logros (titulo, descripcion, fecha_logro) VALUES (%s, %s, %s)",
                (titulo, descripcion, fecha_logro),
            )
            db.commit()
            flash(_("Logro agregado exitosamente"), "success")
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error agregando logro: %s", e)
            flash(_("Error al agregar logro"), "danger")
        finally:
            cur.close()
        return redirect(url_for("trainer.gestion_logros"))

    cur = db.cursor()
    cur.execute("SELECT * FROM logros ORDER BY fecha_logro DESC")
    logros = cur.fetchall()
    cur.close()

    return render_template("logros.html", logros=logros)


@trainer_bp.route("/eliminar_entrenamiento/<int:entrenamiento_id>", methods=["POST"])
@login_required
@permiso_requerido("recomendar_rutinas")
def eliminar_entrenamiento(entrenamiento_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "DELETE FROM asignacion_entrenamientos WHERE entrenamiento_id = %s",
            (entrenamiento_id,),
        )
        cur.execute("DELETE FROM entrenamientos WHERE id = %s", (entrenamiento_id,))
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando entrenamiento: %s", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cur.close()


@trainer_bp.route("/eliminar_logro/<int:logro_id>", methods=["POST"])
@login_required
@rol_requerido("entrenador", "super_usuario")
def eliminar_logro(logro_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM logros WHERE id = %s", (logro_id,))
        db.commit()
        flash(_("Logro eliminado correctamente"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando logro: %s", e)
        flash(_("Error al eliminar logro"), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.gestion_logros"))


@trainer_bp.route("/eliminar_nutricion/<int:nutricion_id>", methods=["POST"])
@login_required
@permiso_requerido("recomendar_nutricion")
def eliminar_nutricion(nutricion_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "DELETE FROM asignacion_nutricion WHERE nutricion_id = %s", (nutricion_id,)
        )
        cur.execute("DELETE FROM nutricion WHERE id = %s", (nutricion_id,))
        db.commit()
        flash(_("Plan nutricional eliminado correctamente"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando nutrición: %s", e)
        flash(_("Error al eliminar plan nutricional"), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.gestion_nutricion"))


@trainer_bp.route("/branding", methods=["GET", "POST"])
@login_required
@permiso_requerido("gestionar_branding")
def branding():
    images_dir = os.path.join(current_app.static_folder, "images")
    os.makedirs(images_dir, exist_ok=True)

    # Importar PIL bajo demanda para evitar fallos al iniciar la app
    Image = None
    try:
        from PIL import Image as _Image

        Image = _Image
    except Exception:
        # Pillow no está disponible; la funcionalidad de procesado de imágenes se degradará
        current_app.logger.warning(
            "Pillow no disponible; procesamiento de logos deshabilitado."
        )

    if request.method == "POST":
        logo = request.files.get("logo")
        if not logo or logo.filename == "":
            flash(_("Selecciona un archivo de logo."), "danger")
            return redirect(url_for("trainer.branding"))

        if not allowed_logo(logo.filename):
            flash(_("Formato no permitido. Usa PNG, JPG, WEBP o SVG."), "danger")
            return redirect(url_for("trainer.branding"))

        ext = logo.filename.rsplit(".", 1)[1].lower()
        if ext == "jpeg":
            ext = "jpg"
        target_name = f"logo.{ext}"
        # Save to temporary path first
        tmp_name = f"logo_tmp.{ext}"
        tmp_path = os.path.join(images_dir, tmp_name)
        try:
            logo.save(tmp_path)

            # Only raster formats are processed; SVGs are saved as-is
            if ext in ("png", "jpg", "jpeg", "webp"):
                try:
                    im = Image.open(tmp_path).convert("RGBA")
                    # Create square canvas and center the image
                    max_side = max(im.width, im.height)
                    canvas = Image.new("RGBA", (max_side, max_side), (255, 255, 255, 0))
                    paste_x = (max_side - im.width) // 2
                    paste_y = (max_side - im.height) // 2
                    # Use alpha channel as mask when present
                    if "A" in im.getbands():
                        canvas.paste(im, (paste_x, paste_y), im)
                    else:
                        canvas.paste(im, (paste_x, paste_y))

                    # Resize to a reasonable fixed size to ensure consistent appearance
                    target_size = 512
                    canvas = canvas.resize((target_size, target_size), Image.LANCZOS)

                    # Remove existing logos and save
                    _remove_existing_logos(images_dir)
                    save_path = os.path.join(images_dir, target_name)
                    if ext in ("jpg", "jpeg"):
                        # JPEG doesn't support alpha; paste on white background
                        bg = Image.new(
                            "RGB", (target_size, target_size), (255, 255, 255)
                        )
                        bg.paste(canvas, mask=canvas.split()[3])
                        bg.save(save_path, quality=95)
                    else:
                        # PNG/WebP keep alpha
                        canvas.save(save_path)

                    os.remove(tmp_path)
                    flash(_("Logo actualizado correctamente."), "success")
                    return redirect(url_for("trainer.branding"))
                except Exception as e:
                    current_app.logger.exception("Error procesando logo: %s", e)
                    # fallback: move original file
                    _remove_existing_logos(images_dir)
                    os.replace(tmp_path, os.path.join(images_dir, target_name))
                    flash(_("Logo actualizado (sin procesar)."), "warning")
                    return redirect(url_for("trainer.branding"))
            else:
                # For SVG or unsupported raster types, simply replace
                _remove_existing_logos(images_dir)
                os.replace(tmp_path, os.path.join(images_dir, target_name))
                flash(_("Logo actualizado correctamente."), "success")
                return redirect(url_for("trainer.branding"))
        except Exception as e:
            current_app.logger.exception("Error guardando logo: %s", e)
            # Clean tmp file if exists
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            flash(_("Error al guardar el logo. Intenta nuevamente."), "danger")
            return redirect(url_for("trainer.branding"))

    return render_template("branding.html")


@trainer_bp.route("/eliminar_entrenador/<int:usuario_id>", methods=["POST"])
@login_required
@permiso_requerido("modificar_entrenadores")
def eliminar_entrenador(usuario_id):
    if current_user.id == usuario_id:
        flash(_("No puedes eliminar tu propia cuenta desde aquí."), "danger")
        return redirect(url_for("trainer.gestion_usuarios"))

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        row = cur.fetchone()
        if not row or row.get("rol") != "entrenador":
            flash(_("Entrenador no encontrado."), "warning")
            return redirect(url_for("trainer.gestion_usuarios"))

        cur.execute(
            "DELETE FROM horarios_entrenador WHERE entrenador_id = %s", (usuario_id,)
        )
        cur.execute(
            "DELETE FROM solicitudes_equipo WHERE entrenador_id = %s", (usuario_id,)
        )
        cur.execute(
            "DELETE FROM usuarios WHERE id = %s AND rol = 'entrenador'", (usuario_id,)
        )
        db.commit()
        flash(_("Entrenador eliminado correctamente."), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error eliminando entrenador: %s", e)
        flash(_("Error al eliminar entrenador."), "danger")
    finally:
        cur.close()

    return redirect(url_for("trainer.gestion_usuarios"))


@trainer_bp.route("/api/jugadores")
@login_required
@rol_requerido("entrenador", "super_usuario")
def api_jugadores():
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT id, nombre, apellido, email FROM usuarios WHERE rol = 'jugador' ORDER BY nombre"
        )
        jugadores = cur.fetchall()
    except Exception:
        jugadores = []
    finally:
        cur.close()

    return jsonify({"jugadores": jugadores})
