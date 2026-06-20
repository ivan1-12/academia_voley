import re
from app import app
from models import get_db


def test_add_trainer_blocked_flag():
    # Temporarily set flag to False and ensure POST is redirected with warning
    app.config["ALLOW_SUPERUSER_CREATE_TRAINERS"] = False
    with app.test_client() as client:
        get = client.get("/login")
        m = re.search(rb'name="csrf_token" value="([^"]+)"', get.data)
        token = m.group(1).decode("utf-8") if m else None
        client.post(
            "/login",
            data={
                "email": "admin@academiavoley.net",
                "password": "AcaVoley!2026",
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        form = client.get("/agregar_staff")
        m2 = re.search(rb'name="csrf_token" value="([^"]+)"', form.data)
        token2 = m2.group(1).decode("utf-8") if m2 else None
        resp = client.post(
            "/agregar_staff",
            data={
                "nombre": "Test",
                "apellido": "User",
                "email": "x@example.com",
                "password": "Testpass1!",
                "confirm_password": "Testpass1!",
                "csrf_token": token2,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Creaci" in resp.data or b"deshabilitada" in resp.data


def test_add_trainer_success_and_cleanup():
    app.config["ALLOW_SUPERUSER_CREATE_TRAINERS"] = True
    email = "auto.test.trainer@example.com"
    # Asegurar estado limpio: eliminar cualquier usuario con ese email antes del test
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM usuarios WHERE email = %s", (email,))
        db.commit()
        cur.close()
    with app.test_client() as client:
        get = client.get("/login")
        m = re.search(rb'name="csrf_token" value="([^"]+)"', get.data)
        token = m.group(1).decode("utf-8") if m else None
        client.post(
            "/login",
            data={
                "email": "admin@academiavoley.net",
                "password": "AcaVoley!2026",
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        form = client.get("/agregar_staff")
        m2 = re.search(rb'name="csrf_token" value="([^"]+)"', form.data)
        token2 = m2.group(1).decode("utf-8") if m2 else None
        resp = client.post(
            "/agregar_staff",
            data={
                "nombre": "Auto",
                "apellido": "Tester",
                "email": email,
                "password": "Testpass1!",
                "confirm_password": "Testpass1!",
                "csrf_token": token2,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Entrenador agregado correctamente" in resp.data
    # cleanup
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM usuarios WHERE email = %s", (email,))
        db.commit()
        cur.close()
