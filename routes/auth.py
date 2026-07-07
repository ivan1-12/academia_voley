from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_babel import gettext as _
from flask_login import login_user, logout_user, login_required, current_user
from extensions import bcrypt, limiter
from models import get_db, User, FALLBACK_PERMISOS
from validators import (
    validar_nombre_texto,
    validar_campo_numerico,
    validar_numero_jugador,
    validar_password_estricta,
    validar_formato_email,
    verificar_email_registro,
)
from datetime import datetime, date

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    db = get_db()
    cur = db.cursor()
    trainers = []
    try:
        cur.execute(
            "SELECT id, nombre, apellido FROM usuarios WHERE rol = 'entrenador' ORDER BY nombre, apellido"
        )
        trainers = cur.fetchall()
    except Exception:
        trainers = []

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        fecha_nacimiento = request.form.get("fecha_nacimiento")
        genero = request.form.get("genero")
        cedula = request.form.get("cedula", "").strip()
        numero = request.form.get("numero", "").strip()
        entrenador_id = request.form.get("entrenador_id")

        # Validaciones estrictas del lado del servidor
        errors = []

        if not validar_nombre_texto(nombre) or not validar_nombre_texto(apellido):
            errors.append(
                _("El nombre y el apellido deben contener letras, espacios, guiones o apóstrofes.")
            )
        if not validar_campo_numerico(cedula):
            errors.append(
                _("El campo Cédula debe contener única y estrictamente números.")
            )
        if numero and not validar_numero_jugador(numero):
            errors.append(_("El campo Número debe contener únicamente dígitos y hasta 3 caracteres."))
        p_valido, p_msg = validar_password_estricta(password)
        if not p_valido:
            errors.append(_(p_msg))
        if password != confirm_password:
            errors.append(_("Las contraseñas no coinciden."))
        if not fecha_nacimiento:
            errors.append(_("La fecha de nacimiento es obligatoria."))
        if not genero:
            errors.append(_("Seleccione un género."))
        email_msg = ""
        if not email:
            errors.append(_("El correo electrónico es obligatorio."))
        elif not validar_formato_email(email):
            errors.append(_("El formato del correo electrónico no es válido."))

        if errors:
            # Build field-specific errors for inline display
            form_errors = {}
            for err in errors:
                if "nombre" in err.lower() or "apellido" in err.lower():
                    form_errors.setdefault("nombre", []).append(err)
                    form_errors.setdefault("apellido", []).append(err)
                elif "cédula" in err.lower() or "cedula" in err.lower():
                    form_errors.setdefault("cedula", []).append(err)
                elif "número" in err.lower() or "numero" in err.lower():
                    form_errors.setdefault("numero", []).append(err)
                elif "contrase" in err.lower() or "contraseñas" in err.lower():
                    form_errors.setdefault("password", []).append(err)
                    form_errors.setdefault("confirm_password", []).append(err)
                elif "fecha de nacimiento" in err.lower() or "fecha" in err.lower():
                    form_errors.setdefault("fecha_nacimiento", []).append(err)
                elif "género" in err.lower() or "genero" in err.lower():
                    form_errors.setdefault("genero", []).append(err)
                elif "correo" in err.lower() or "email" in err.lower():
                    form_errors.setdefault("email", []).append(err)
                elif "entrenador" in err.lower():
                    form_errors.setdefault("entrenador_id", []).append(err)
                else:
                    form_errors.setdefault("general", []).append(err)

            cur.close()
            return render_template(
                "registro.html",
                trainers=trainers,
                selected_trainer_id=entrenador_id,
                form_errors=form_errors,
                nombre=nombre,
                apellido=apellido,
                email=email,
                numero=numero,
            )

        try:
            cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            usuario_existente = cur.fetchone()
            if usuario_existente and usuario_existente.get("rol") != "jugador":
                flash(_("El correo electrónico ya está registrado. Por favor inicia sesión."),
                    "danger",
                )
                cur.close()
                return render_template(
                    "registro.html",
                    trainers=trainers,
                    selected_trainer_id=entrenador_id,
                )

            if not usuario_existente:
                email_valido, email_msg = verificar_email_registro(email, get_db())
                if not email_valido:
                    flash(_(email_msg), "danger")
                    cur.close()
                    return render_template(
                        "registro.html",
                        trainers=trainers,
                        selected_trainer_id=entrenador_id,
                    )
                if email_msg and "Nota:" in email_msg:
                    flash(_(email_msg), "info")

            cur.execute(
                "SELECT id, estado, tipo FROM solicitudes_equipo WHERE email = %s ORDER BY creado_at DESC LIMIT 1",
                (email,),
            )
            solicitud_existente = cur.fetchone()

            if solicitud_existente and solicitud_existente.get("estado") == "pendiente":
                flash(
                    _("Tu solicitud aún está pendiente. Espera a que el entrenador la revise y acepte."),
                    "warning",
                )
                cur.close()
                return render_template(
                    "registro.html",
                    trainers=trainers,
                    selected_trainer_id=entrenador_id,
                )

            if usuario_existente and usuario_existente.get("rol") == "jugador":
                if (
                    solicitud_existente
                    and solicitud_existente.get("estado") == "aceptado"
                ):
                    flash(_("Tu solicitud ya fue aceptada. Inicia sesión con tu correo para completar tu perfil."),
                        "success",
                    )
                    cur.close()
                    return redirect(url_for("auth.login"))
                if not entrenador_id:
                    flash(_("Selecciona un entrenador para solicitar la creación de tu perfil."),
                        "danger",
                    )
                    cur.close()
                    return render_template(
                        "registro.html",
                        trainers=trainers,
                        selected_trainer_id=entrenador_id,
                    )

                cur.execute(
                    "INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, tipo) VALUES (%s, %s, %s, %s, %s, 'academia')",
                    (
                        entrenador_id,
                        nombre,
                        email,
                        None,
                        "Solicitud de perfil para jugador de la academia.",
                    ),
                )
                db.commit()
                flash(_("Solicitud enviada. Fue colocada en el apartado Jugadores de la academia."),
                    "success",
                )
                cur.close()
                return redirect(url_for("public.index"))

            if (
                solicitud_existente
                and solicitud_existente.get("estado") == "aceptado"
                and solicitud_existente.get("tipo") in ("nuevo", "academia")
            ):
                fn = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
                today = date.today()
                edad = (
                    today.year
                    - fn.year
                    - ((today.month, today.day) < (fn.month, fn.day))
                )
                password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
                cur.execute("SELECT id FROM roles WHERE nombre = 'jugador'")
                rol_row = cur.fetchone()
                rol_id = rol_row["id"] if rol_row else None
                idioma = session.get("lang", "es")
                cur.execute(
                    "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, fecha_nacimiento, edad, genero, cedula, numero, idioma) VALUES (%s, %s, %s, %s, 'jugador', %s, %s, %s, %s, %s, %s, %s)",
                    (
                        nombre,
                        apellido,
                        email,
                        password_hash,
                        rol_id,
                        fecha_nacimiento,
                        edad,
                        genero,
                        cedula,
                        numero or None,
                        idioma,
                    ),
                )
                cur.execute(
                    "UPDATE solicitudes_equipo SET estado = 'registrado' WHERE id = %s",
                    (solicitud_existente["id"],),
                )
                db.commit()
                flash(_("Perfil creado correctamente. Ahora puedes iniciar sesión con el mismo correo."),
                    "success",
                )
                cur.close()
                return redirect(url_for("auth.login"))

            if not entrenador_id:
                flash(_("Selecciona un entrenador para tu solicitud."), "danger")
                cur.close()
                return render_template(
                    "registro.html",
                    trainers=trainers,
                    selected_trainer_id=entrenador_id,
                )

            # Crear cuenta de jugador en estado inactivo con los datos enviados para evitar doble formulario
            try:
                cur.execute("SELECT id FROM roles WHERE nombre = 'jugador'")
                rol_row = cur.fetchone()
                rol_id = rol_row["id"] if rol_row else None
                password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
                idioma = session.get("lang", "es")
                fn = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date() if fecha_nacimiento else None
                today = date.today()
                edad = (
                    today.year - fn.year - ((today.month, today.day) < (fn.month, fn.day))
                ) if fn else None

                cur.execute(
                    "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, fecha_nacimiento, edad, genero, cedula, numero, idioma, activo) VALUES (%s, %s, %s, %s, 'jugador', %s, %s, %s, %s, %s, %s, %s, 0)",
                    (
                        nombre,
                        apellido,
                        email,
                        password_hash,
                        rol_id,
                        fecha_nacimiento,
                        edad,
                        genero,
                        cedula,
                        numero or None,
                        idioma,
                    ),
                )
            except Exception:
                db.rollback()

            cur.execute(
                "INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, tipo) VALUES (%s, %s, %s, %s, %s, 'nuevo')",
                (
                    entrenador_id,
                    nombre,
                    email,
                    None,
                    "Solicitud generada desde registro de jugador.",
                ),
            )
            db.commit()
            flash(_("Tu solicitud fue enviada correctamente. Cuando el entrenador la acepte recibirás un correo y podrás iniciar sesión."),
                "success",
            )
            cur.close()
            return redirect(url_for("public.index"))
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error en registro: %s", e)
            flash(_("Error al registrarse. Verifica los datos o contacta al administrador."),
                "danger",
            )
        finally:
            cur.close()

    return render_template("registro.html", trainers=trainers)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            user = cur.fetchone()

            if not user:
                flash(_("Email o contraseña incorrectos"), "danger")
                return render_template("login.html")

            if user.get("activo") == 0:
                flash(_("La cuenta está inactiva. Contacta al administrador."), "warning")
                return render_template("login.html")

            if not bcrypt.check_password_hash(user["password"], password):
                flash(_("Email o contraseña incorrectos"), "danger")
                return render_template("login.html")

            # Obtener el nombre del rol real
            cur.execute("SELECT nombre FROM roles WHERE id = %s", (user.get("rol_id"),))
            rol_row = cur.fetchone()
            rol_actual = rol_row["nombre"] if rol_row else user.get("rol", "jugador")

            # Cargar permisos asociados al rol del usuario
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
                current_app.logger.warning(f"Error cargando permisos: {e}")

            if not permisos:
                permisos = FALLBACK_PERMISOS.get(rol_actual, set())

            # Crear objeto de usuario
            user_obj = User(
                user["id"],
                user["nombre"],
                user["apellido"],
                user["email"],
                rol_actual,
                permisos,
            )
            login_user(user_obj)
            # Aplicar idioma guardado en perfil al iniciar sesión
            try:
                session["lang"] = user.get("idioma", session.get("lang", "es"))
            except Exception:
                pass

            if rol_actual in ["entrenador", "super_usuario"]:
                return redirect(url_for("trainer.dashboard_entrenador"))
            else:
                return redirect(url_for("player.dashboard_jugador"))
        except Exception as e:
            current_app.logger.exception("Error en el login: %s", e)
            flash(_("Ocurrió un error al iniciar sesión. Intenta nuevamente."), "danger")
        finally:
            cur.close()

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash(_("Has cerrado sesión exitosamente"), "success")
    return redirect(url_for("public.index"))


@auth_bp.route("/cambiar_password", methods=["GET", "POST"])
@login_required
def cambiar_password():
    if request.method == "POST":
        actual = request.form.get("password_actual", "")
        nueva = request.form.get("password_nueva", "")
        confirmar = request.form.get("confirm_password", "")

        if nueva != confirmar:
            flash(_("Las contraseñas nuevas no coinciden."), "danger")
            return render_template("cambiar_password.html")

        p_valido, p_msg = validar_password_estricta(nueva)
        if not p_valido:
            flash(_(p_msg), "danger")
            return render_template("cambiar_password.html")

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                "SELECT password FROM usuarios WHERE id = %s", (current_user.id,)
            )
            row = cur.fetchone()
            if not row or not bcrypt.check_password_hash(row["password"], actual):
                flash(_("La contraseña actual no es correcta."), "danger")
                return render_template("cambiar_password.html")

            password_hash = bcrypt.generate_password_hash(nueva).decode("utf-8")
            cur.execute(
                "UPDATE usuarios SET password = %s WHERE id = %s",
                (password_hash, current_user.id),
            )
            db.commit()
            flash(_("Contraseña actualizada correctamente."), "success")
            if current_user.rol in ("entrenador", "super_usuario"):
                return redirect(url_for("trainer.dashboard_entrenador"))
            return redirect(url_for("player.dashboard_jugador"))
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error cambiando contraseña: %s", e)
            flash(_("No se pudo actualizar la contraseña."), "danger")
        finally:
            cur.close()

    return render_template("cambiar_password.html")
