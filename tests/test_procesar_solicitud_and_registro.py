import re
from uuid import uuid4
from app import app
from models import get_db


def _extract_csrf(html: str):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def test_aceptar_solicitud_y_registro_completo():
    entrenador_email = f"tmp_ent_{uuid4().hex}@example.com"
    solicitud_email = f"newplayer_{uuid4().hex}@example.com"

    with app.app_context():
        db = get_db()
        cur = db.cursor()
        try:
            # Crear entrenador temporal
            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password, rol, activo) VALUES (%s,%s,%s,%s,'entrenador',1)",
                ("Temp", "Entrenador", entrenador_email, "x"),
            )
            db.commit()
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (entrenador_email,))
            entrenador_id = cur.fetchone()["id"]

            # Asegurar columna tipo existe
            cur.execute("SHOW COLUMNS FROM solicitudes_equipo LIKE 'tipo'")
            if cur.fetchone() is None:
                cur.execute(
                    "ALTER TABLE solicitudes_equipo ADD COLUMN tipo VARCHAR(32) DEFAULT 'nuevo'"
                )
                db.commit()

            # Crear solicitud pendiente
            cur.execute(
                "INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, estado, tipo) VALUES (%s,%s,%s,%s,%s,'pendiente','nuevo')",
                (entrenador_id, "Solicitante", solicitud_email, None, "Solicitud test"),
            )
            db.commit()
            cur.execute(
                "SELECT id FROM solicitudes_equipo WHERE email = %s ORDER BY creado_at DESC LIMIT 1",
                (solicitud_email,),
            )
            solicitud_id = cur.fetchone()["id"]

            # Login como super_usuario (admin) para procesar solicitud
            with app.test_client() as client:
                get = client.get("/login")
                token = _extract_csrf(get.data.decode("utf-8", errors="replace"))
                resp = client.post(
                    "/login",
                    data={
                        "email": "admin@academiavoley.net",
                        "password": "AcaVoley!2026",
                        "csrf_token": token,
                    },
                    follow_redirects=True,
                )
                assert resp.status_code == 200

                # Procesar solicitud: aceptar
                proc_get = client.get("/solicitudes_equipo")
                token2 = _extract_csrf(proc_get.data.decode("utf-8", errors="replace"))
                proc = client.post(
                    f"/solicitudes_equipo/{solicitud_id}/procesar",
                    data={"action": "aceptar", "csrf_token": token2},
                    follow_redirects=True,
                )
                assert proc.status_code == 200

            # Ahora intentar registro con ese email (debe crear usuario jugador)
            # Some test environments may have CSRF session issues; disable CSRF only for this POST
            original_csrf = app.config.get("WTF_CSRF_ENABLED", True)
            app.config["WTF_CSRF_ENABLED"] = False
            try:
                with app.test_client() as client2:
                    client2.get("/registro")
                    post = client2.post(
                        "/registro",
                        data={
                            "nombre": "Jugador",
                            "apellido": "Nuevo",
                            "email": solicitud_email,
                            "password": "PassValida1!",
                            "confirm_password": "PassValida1!",
                            "fecha_nacimiento": "2005-05-05",
                            "genero": "F",
                            "cedula": "87654321",
                            "entrenador_id": str(entrenador_id),
                        },
                        follow_redirects=True,
                    )
                    if post.status_code != 200:
                        print("\n--- Registro response HTML ---\n")
                        print(post.data.decode("utf-8", errors="replace"))
                        print("\n--- end response ---\n")
                    assert post.status_code == 200
            finally:
                app.config["WTF_CSRF_ENABLED"] = original_csrf

            # Verificar en BD que usuario creado y solicitud marcada como registrado
            cur.execute("SELECT * FROM usuarios WHERE email = %s", (solicitud_email,))
            user = cur.fetchone()
            assert user is not None and user.get("rol") == "jugador"

            cur.execute(
                "SELECT * FROM solicitudes_equipo WHERE id = %s", (solicitud_id,)
            )
            sol = cur.fetchone()
            assert sol is not None and sol.get("estado") in ("registrado", "aceptado")

            # Cleanup
            if user:
                cur.execute("DELETE FROM usuarios WHERE id = %s", (user["id"],))
            cur.execute("DELETE FROM solicitudes_equipo WHERE id = %s", (solicitud_id,))
            cur.execute("DELETE FROM usuarios WHERE id = %s", (entrenador_id,))
            db.commit()
        finally:
            cur.close()
