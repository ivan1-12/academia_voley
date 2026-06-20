import re
from uuid import uuid4
from app import app
from models import get_db


def _extract_csrf(html: str):
    m = re.search(r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def test_crear_solicitud_registro():
    entrenador_email = f"tmp_ent_{uuid4().hex}@example.com"
    email = f"solicitud_test_{uuid4().hex}@example.com"
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
            row = cur.fetchone()
            entrenador_id = row["id"]
            # Ensure `tipo` column exists before invoking the POST flow (route queries it)
            cur.execute("SHOW COLUMNS FROM solicitudes_equipo LIKE 'tipo'")
            has_tipo = cur.fetchone() is not None
            added_tipo = False
            if not has_tipo:
                cur.execute(
                    "ALTER TABLE solicitudes_equipo ADD COLUMN tipo VARCHAR(32) DEFAULT NULL"
                )
                db.commit()
                added_tipo = True

            with app.test_client() as client:
                r = client.get("/registro")
                assert r.status_code == 200
                csrf = _extract_csrf(r.data.decode("utf-8", errors="replace"))
                assert csrf

                data = {
                    "csrf_token": csrf,
                    "nombre": "Solicitud",
                    "apellido": "Tester",
                    "email": email,
                    "password": "ValidaPass1!",
                    "confirm_password": "ValidaPass1!",
                    "fecha_nacimiento": "2000-01-01",
                    "genero": "M",
                    "cedula": "12345678",
                    "entrenador_id": str(entrenador_id),
                }
                post = client.post("/registro", data=data, follow_redirects=True)
                assert post.status_code == 200

            # Verificar que la solicitud fue creada
            cur.execute(
                "SELECT * FROM solicitudes_equipo WHERE email = %s ORDER BY creado_at DESC LIMIT 1",
                (email,),
            )
            solicitud = cur.fetchone()
            assert solicitud is not None
            # Limpiar: borrar la solicitud y el entrenador temporal
            cur.execute(
                "DELETE FROM solicitudes_equipo WHERE id = %s", (solicitud["id"],)
            )
            cur.execute("DELETE FROM usuarios WHERE id = %s", (entrenador_id,))
            db.commit()
            # Si añadimos la columna `tipo` durante el test, revertir el cambio
            if added_tipo:
                try:
                    cur.execute("ALTER TABLE solicitudes_equipo DROP COLUMN tipo")
                    db.commit()
                except Exception:
                    pass
        finally:
            cur.close()
