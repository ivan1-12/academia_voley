from flask import Blueprint, render_template
from flask_babel import gettext as _
from flask_login import login_required
from models import get_db, rol_requerido

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reportes")
@login_required
@rol_requerido("super_usuario")
def reportes():
    db = get_db()
    cur = db.cursor()

    # 1. Usuarios Activos (en los últimos 5 minutos)
    try:
        cur.execute(
            """
            SELECT COUNT(*) as total
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE COALESCE(r.nombre, u.rol) = 'jugador' AND u.last_activity >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        """
        )
        jugadores_activos = cur.fetchone()["total"]
    except Exception:
        jugadores_activos = 0

    try:
        cur.execute(
            """
            SELECT COUNT(*) as total
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE COALESCE(r.nombre, u.rol) = 'entrenador' AND u.last_activity >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        """
        )
        entrenadores_activos = cur.fetchone()["total"]
    except Exception:
        entrenadores_activos = 0

    try:
        cur.execute(
            """
            SELECT u.nombre, u.apellido, u.email, COALESCE(r.nombre, u.rol) AS rol, u.last_activity
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE u.last_activity >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            ORDER BY u.last_activity DESC
        """
        )
        lista_activos = cur.fetchall()
    except Exception:
        lista_activos = []

    # 2. Recomendaciones (entrenamientos y nutrición recomendados a jugadores)
    try:
        cur.execute(
            """
            SELECT 
                u.id, 
                u.nombre, 
                u.apellido, 
                u.email,
                (SELECT COUNT(*) FROM asignacion_entrenamientos ae WHERE ae.jugador_id = u.id) as rutinas_count,
                (SELECT COUNT(*) FROM asignacion_nutricion an WHERE an.jugador_id = u.id) as nutricion_count
            FROM usuarios u
            WHERE u.rol = 'jugador'
            ORDER BY u.nombre, u.apellido
        """
        )
        jugadores_recomendaciones = cur.fetchall()
    except Exception:
        jugadores_recomendaciones = []

    # 3. Descargas de material / rutinas asignadas
    try:
        # Historial de descargas recientes (posible filtrado por rango)
        range_param = None
        try:
            from flask import request

            range_param = request.args.get("range")
        except Exception:
            range_param = None

        range_clause = ""
        if range_param == "month":
            range_clause = (
                "WHERE dl.fecha_descarga >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
            )
        elif range_param == "week":
            range_clause = "WHERE dl.fecha_descarga >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        elif range_param == "day":
            range_clause = "WHERE dl.fecha_descarga >= DATE_SUB(NOW(), INTERVAL 1 DAY)"
        elif range_param == "hour":
            range_clause = "WHERE dl.fecha_descarga >= DATE_SUB(NOW(), INTERVAL 1 HOUR)"

        sql = f"""
            SELECT 
                dl.id,
                dl.nombre_archivo, 
                dl.fecha_descarga, 
                u.nombre, 
                u.apellido, 
                u.email
            FROM descargas_log dl
            JOIN usuarios u ON dl.usuario_id = u.id
            {range_clause}
            ORDER BY dl.fecha_descarga DESC
            LIMIT 200
        """
        cur.execute(sql)
        historial_descargas = cur.fetchall()

        # Conteo total de descargas
        cur.execute("SELECT COUNT(*) as total FROM descargas_log")
        total_descargas = cur.fetchone()["total"]

        # Descargas agrupadas por jugador
        cur.execute(
            """
            SELECT 
                u.nombre, 
                u.apellido, 
                u.email, 
                COUNT(dl.id) as total_descargas
            FROM usuarios u
            JOIN descargas_log dl ON dl.usuario_id = u.id
            GROUP BY u.id
            ORDER BY total_descargas DESC
        """
        )
        ranking_descargas = cur.fetchall()
    except Exception:
        historial_descargas = []
        total_descargas = 0
        ranking_descargas = []

    cur.close()

    return render_template(
        "reportes.html",
        jugadores_activos=jugadores_activos,
        entrenadores_activos=entrenadores_activos,
        lista_activos=lista_activos,
        jugadores_recomendaciones=jugadores_recomendaciones,
        historial_descargas=historial_descargas,
        total_descargas=total_descargas,
        ranking_descargas=ranking_descargas,
    )
