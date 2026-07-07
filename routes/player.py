from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, abort
from flask_babel import gettext as _
from flask_login import login_required, current_user
from models import get_db, rol_requerido
from validators import validar_telefono, validar_numero_jugador, normalizar_telefono
from datetime import datetime
from fpdf import FPDF
import io

player_bp = Blueprint("player", __name__)


@player_bp.route("/perfil_jugador/<int:usuario_id>")
@login_required
@rol_requerido("entrenador", "super_usuario")
def perfil_jugador(usuario_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT * FROM usuarios WHERE id = %s AND rol = 'jugador'", (usuario_id,))
        usuario = cur.fetchone()
        if not usuario:
            flash(_("Jugador no encontrado."), "warning")
            cur.close()
            return redirect(url_for("trainer.dashboard_entrenador"))

        usuario["telefono"] = normalizar_telefono(usuario.get("telefono"))
        cur.execute("SELECT * FROM perfiles_jugadores WHERE usuario_id = %s", (usuario_id,))
        perfil = cur.fetchone()
    except Exception:
        usuario = None
        perfil = None
    finally:
        cur.close()

    return render_template("perfil_jugador.html", usuario=usuario, perfil=perfil)


@player_bp.route("/dashboard_jugador")
@login_required
def dashboard_jugador():
    if current_user.rol != "jugador":
        return redirect(url_for("trainer.dashboard_entrenador"))

    db = get_db()
    cur = db.cursor()

    try:
        cur.execute(
            """
            SELECT e.*, ae.completado 
            FROM asignacion_entrenamientos ae
            JOIN entrenamientos e ON ae.entrenamiento_id = e.id
            WHERE ae.jugador_id = %s
        """,
            (current_user.id,),
        )
        entrenamientos = cur.fetchall()
    except Exception:
        entrenamientos = []

    try:
        cur.execute(
            """
            SELECT n.* 
            FROM asignacion_nutricion an
            JOIN nutricion n ON an.nutricion_id = n.id
            WHERE an.jugador_id = %s
        """,
            (current_user.id,),
        )
        nutricion = cur.fetchone()
    except Exception:
        nutricion = None

    try:
        cur.execute(
            "SELECT * FROM perfiles_jugadores WHERE usuario_id = %s", (current_user.id,)
        )
        perfil = cur.fetchone()
    except Exception:
        perfil = None

    if hasattr(current_user, 'telefono'):
        current_user.telefono = normalizar_telefono(current_user.telefono)

    total_entrenamientos = len(entrenamientos)
    completados = sum(1 for entrenamiento in entrenamientos if entrenamiento.get("completado"))
    progreso_general = round((completados / total_entrenamientos * 100), 1) if total_entrenamientos else 0.0

    cur.close()

    return render_template(
        "dashboard_jugador.html",
        entrenamientos=entrenamientos,
        nutricion=nutricion,
        perfil=perfil,
        total_entrenamientos=total_entrenamientos,
        completados=completados,
        progreso_general=progreso_general,
    )


@player_bp.route("/completar_entrenamiento/<int:entrenamiento_id>", methods=["POST"])
@login_required
@rol_requerido("jugador")
def completar_entrenamiento(entrenamiento_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE asignacion_entrenamientos SET completado = TRUE WHERE jugador_id = %s AND entrenamiento_id = %s",
            (current_user.id, entrenamiento_id),
        )
        db.commit()
        flash(_("¡Felicidades! Has completado el entrenamiento"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error completando entrenamiento: %s", e)
        flash(_("Error al completar entrenamiento"), "danger")
    finally:
        cur.close()

    return redirect(url_for("player.dashboard_jugador"))


@player_bp.route("/editar_perfil_jugador", methods=["POST"])
@login_required
def editar_perfil_jugador():
    # Permitido si es jugador, o si es entrenador/super con permiso
    if current_user.rol != "jugador" and not current_user.has_permission(
        "gestionar_perfil_deportivo"
    ):
        abort(403)

    # Obtener el ID de usuario del perfil a modificar
    if current_user.rol == "jugador":
        target_usuario_id = current_user.id
    else:
        target_usuario_id = request.form.get("jugador_id")
        if not target_usuario_id:
            flash(_("Debe especificar el jugador a editar."), "danger")
            return redirect(url_for("trainer.dashboard_entrenador"))

    altura_cm = request.form.get("altura_cm")
    peso_kg = request.form.get("peso_kg")
    posicion = request.form.get("posicion", "").strip()
    telefono = request.form.get("telefono", "")
    numero = request.form.get("numero", "").strip()

    if telefono and not validar_telefono(telefono):
        flash(_("El teléfono ingresado no tiene un formato válido."), "danger")
        return redirect(
            url_for("player.dashboard_jugador")
            if current_user.rol == "jugador"
            else url_for("trainer.dashboard_entrenador")
        )

    if numero and not validar_numero_jugador(numero):
        flash(_("El campo Número debe contener únicamente dígitos y hasta 3 caracteres."), "danger")
        return redirect(
            url_for("player.dashboard_jugador")
            if current_user.rol == "jugador"
            else url_for("trainer.dashboard_entrenador")
        )

    telefono = normalizar_telefono(telefono)

    # Convertir a tipos numéricos o None con validación
    try:
        altura_cm = int(altura_cm) if altura_cm and altura_cm.strip() else None
        peso_kg = float(peso_kg) if peso_kg and peso_kg.strip() else None
    except ValueError:
        flash(_("Altura o peso inválidos. Por favor use números."), "danger")
        return redirect(
            url_for("player.dashboard_jugador")
            if current_user.rol == "jugador"
            else url_for("trainer.dashboard_entrenador")
        )

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT id FROM perfiles_jugadores WHERE usuario_id = %s",
            (target_usuario_id,),
        )
        existente = cur.fetchone()

        cur.execute(
            "UPDATE usuarios SET telefono = %s, numero = %s WHERE id = %s",
            (telefono, numero or None, target_usuario_id),
        )

        if existente:
            cur.execute(
                "UPDATE perfiles_jugadores SET altura_cm = %s, peso_kg = %s, posicion = %s WHERE usuario_id = %s",
                (altura_cm, peso_kg, posicion, target_usuario_id),
            )
        else:
            cur.execute(
                "INSERT INTO perfiles_jugadores (usuario_id, altura_cm, peso_kg, posicion) VALUES (%s, %s, %s, %s)",
                (target_usuario_id, altura_cm, peso_kg, posicion),
            )

        db.commit()
        flash(_("Perfil actualizado correctamente"), "success")
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Error actualizando perfil: %s", e)
        flash(_("Error al actualizar perfil"), "danger")
    finally:
        cur.close()

    return redirect(
        url_for("player.dashboard_jugador")
        if current_user.rol == "jugador"
        else url_for("trainer.dashboard_entrenador")
    )


@player_bp.route("/descargar_rutinas_pdf")
@login_required
@rol_requerido("jugador")
def descargar_rutinas_pdf():
    db = get_db()
    cur = db.cursor()

    # Obtener entrenamientos asignados
    try:
        cur.execute(
            """
            SELECT e.*, ae.completado 
            FROM asignacion_entrenamientos ae
            JOIN entrenamientos e ON ae.entrenamiento_id = e.id
            WHERE ae.jugador_id = %s
        """,
            (current_user.id,),
        )
        entrenamientos = cur.fetchall()
    except Exception:
        entrenamientos = []

    # Obtener plan nutricional
    try:
        cur.execute(
            """
            SELECT n.* 
            FROM asignacion_nutricion an
            JOIN nutricion n ON an.nutricion_id = n.id
            WHERE an.jugador_id = %s
        """,
            (current_user.id,),
        )
        nutricion = cur.fetchone()
    except Exception:
        nutricion = None

    cur.close()

    # Generar PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # --- Encabezado ---
    pdf.set_fill_color(102, 126, 234)
    pdf.rect(0, 0, 210, 45, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_y(8)
    pdf.cell(
        0,
        10,
        _("Academia Juventud Global Sports"),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(
        0,
        8,
        _("Plan de Entrenamiento y Nutricion"),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(
        0,
        8,
        f"Jugador: {current_user.nombre} {current_user.apellido}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(55)

    # Fecha de generacion
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(
        0,
        6,
        f'Generado el: {datetime.now().strftime("%d/%m/%Y a las %H:%M")}',
        align="R",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)

    # --- Entrenamientos ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_fill_color(40, 167, 69)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(
        0,
        10,
        _("  Mis Entrenamientos Asignados"),
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    if entrenamientos:
        for i, ent in enumerate(entrenamientos, 1):
            if pdf.get_y() > 240:
                pdf.add_page()

            estado = "COMPLETADO" if ent.get("completado") else "PENDIENTE"
            color_estado = (40, 167, 69) if ent.get("completado") else (255, 193, 7)

            # Titulo del entrenamiento
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, f'{i}. {ent["titulo"]}', new_x="LMARGIN", new_y="NEXT")

            # Estado badge
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(*color_estado)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(30, 6, f" {estado} ", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            # Info
            pdf.set_font("Helvetica", "", 10)
            duracion = ent.get("duracion_minutos", "N/A")
            dificultad = ent.get("dificultad", "N/A")
            pdf.cell(90, 6, _(f"Duracion: {duracion} minutos"), new_x="RIGHT")
            pdf.cell(0, 6, _(f"Dificultad: {dificultad}"), new_x="LMARGIN", new_y="NEXT")

            # Descripcion
            if ent.get("descripcion"):
                pdf.set_font("Helvetica", "I", 10)
                pdf.multi_cell(0, 5, _(f"Descripcion: {ent['descripcion']}"))

            # Ejercicios
            if ent.get("ejercicios"):
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, _("Ejercicios:"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                ejercicios_text = (
                    ent["ejercicios"].replace("\r\n", "\n").replace("\r", "\n")
                )
                pdf.multi_cell(0, 5, ejercicios_text)

            # Separador
            pdf.ln(3)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
    else:
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(
            0,
            8,
            _("No tienes entrenamientos asignados aun."),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(5)

    # --- Plan Nutricional ---
    if pdf.get_y() > 220:
        pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_fill_color(23, 162, 184)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, _("  Mi Plan Nutricional"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    if nutricion:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(
            0,
            8,
            nutricion.get("titulo", _("Plan Nutricional")),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(3)

        comidas = [
            (_("Desayuno"), nutricion.get("desayuno", "")),
            (_("Almuerzo"), nutricion.get("almuerzo", "")),
            (_("Cena"), nutricion.get("cena", "")),
            (_("Merienda"), nutricion.get("merienda", "")),
            (_("Hidratacion"), nutricion.get("hidratacion", "")),
        ]

        for nombre, contenido in comidas:
            if pdf.get_y() > 250:
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 7, f"  {nombre}", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            if contenido:
                pdf.multi_cell(0, 5, f"  {contenido}")
            else:
                pdf.cell(0, 5, _("  No especificado"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
    else:
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(
            0,
            8,
            _("No tienes un plan nutricional asignado aun."),
            new_x="LMARGIN",
            new_y="NEXT",
        )

    # --- Pie de pagina ---
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0,
        5,
        _("Academia Juventud Global Sports - Documento generado automaticamente"),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    # Enviar PDF
    pdf_output = pdf.output()
    buffer = io.BytesIO(pdf_output)
    buffer.seek(0)

    filename = f'rutinas_{current_user.nombre}_{current_user.apellido}_{datetime.now().strftime("%Y%m%d")}.pdf'

    # Registrar la descarga en la base de datos
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO descargas_log (usuario_id, nombre_archivo) VALUES (%s, %s)",
            (current_user.id, filename),
        )
        db.commit()
    except Exception as e:
        db.rollback()
        current_app.logger.warning(f"Error al registrar descarga en descargas_log: {e}")
    finally:
        cur.close()

    return send_file(
        buffer, as_attachment=True, download_name=filename, mimetype="application/pdf"
    )
