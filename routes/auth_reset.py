from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_babel import gettext as _
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from extensions import bcrypt, limiter
from models import get_db
from validators import validar_password_estricta, validar_formato_email
from utils.notifications import send_email

reset_bp = Blueprint("auth_reset", __name__)


def get_serializer():
    secret = current_app.config.get("SECRET_KEY")
    return URLSafeTimedSerializer(secret, salt="password-reset-salt")


@reset_bp.route("/forgot_password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email or not validar_formato_email(email):
            flash(_("Ingrese un correo válido."), "danger")
            return render_template("forgot_password.html")

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("SELECT id, nombre FROM usuarios WHERE email = %s", (email,))
            user = cur.fetchone()
            if not user:
                flash(_("Si existe una cuenta con ese correo, recibirás un enlace para restablecer la contraseña."), "info")
                return redirect(url_for("auth.login"))

            token = get_serializer().dumps({"user_id": user["id"], "email": email})
            reset_url = url_for("auth_reset.reset_password", token=token, _external=True)
            subject = _("Restablece tu contraseña")
            body = _(
                "Hola %(name)s,\n\nRecibimos una solicitud para restablecer tu contraseña. Si no la solicitaste, ignora este correo.\n\nHaz clic en el siguiente enlace para continuar:\n%(url)s\n\nEste enlace expira en %(expiration)d minutos.",
                name=user["nombre"],
                url=reset_url,
                expiration=int(current_app.config.get("PASSWORD_RESET_EXPIRATION", 3600) / 60),
            )
            send_email(email, subject, body)
            flash(_("Si existe una cuenta con ese correo, recibirás un enlace para restablecer la contraseña."), "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            current_app.logger.exception("Error al generar token de restablecimiento: %s", e)
            flash(_("Ocurrió un error. Intenta nuevamente más tarde."), "danger")
        finally:
            cur.close()
    return render_template("forgot_password.html")


@reset_bp.route("/reset_password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def reset_password(token):
    try:
        data = get_serializer().loads(token, max_age=current_app.config.get("PASSWORD_RESET_EXPIRATION", 3600))
    except SignatureExpired:
        flash(_("El enlace de restablecimiento ha expirado."), "danger")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash(_("El enlace de restablecimiento no es válido."), "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        nueva = request.form.get("password_nueva", "")
        confirmar = request.form.get("confirm_password", "")
        if nueva != confirmar:
            flash(_("Las contraseñas no coinciden."), "danger")
            return render_template("reset_password.html")

        valido, msg = validar_password_estricta(nueva)
        if not valido:
            flash(_(msg), "danger")
            return render_template("reset_password.html")

        db = get_db()
        cur = db.cursor()
        try:
            password_hash = bcrypt.generate_password_hash(nueva).decode("utf-8")
            cur.execute("UPDATE usuarios SET password = %s WHERE id = %s", (password_hash, data["user_id"]))
            db.commit()
            flash(_("Contraseña restablecida correctamente. Ya puedes iniciar sesión."), "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Error restableciendo contraseña: %s", e)
            flash(_("Ocurrió un error al actualizar la contraseña."), "danger")
        finally:
            cur.close()

    return render_template("reset_password.html")
