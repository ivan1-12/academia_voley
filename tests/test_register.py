import re
from app import app


def _extract_csrf(html: str):
    m = re.search(r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def test_register_get_and_validation():
    with app.test_client() as client:
        r = client.get("/registro")
        assert r.status_code == 200
        html = r.data.decode("utf-8", errors="replace")
        csrf = _extract_csrf(html)
        assert csrf is not None
        # Try to POST with invalid fields including CSRF
        post = client.post(
            "/registro",
            data={
                "csrf_token": csrf,
                "nombre": "123",
                "apellido": "",
                "email": "bad",
                "password": "short",
                "confirm_password": "short",
            },
            follow_redirects=True,
        )
        assert post.status_code == 200
        text = post.data.decode("utf-8", errors="replace")
        assert "El nombre" in text or "Cédula" in text or "contrase" in text


def test_registration_form_includes_number_field():
    with app.test_client() as client:
        r = client.get("/registro")
        assert r.status_code == 200
        html = r.data.decode("utf-8", errors="replace")
        assert 'name="numero"' in html


def test_registration_rejects_invalid_number_field():
    with app.test_client() as client:
        r = client.get("/registro")
        assert r.status_code == 200
        html = r.data.decode("utf-8", errors="replace")
        csrf = _extract_csrf(html)
        post = client.post(
            "/registro",
            data={
                "csrf_token": csrf,
                "nombre": "Luis",
                "apellido": "Perez",
                "email": "luis.perez@example.com",
                "password": "Testpass1!",
                "confirm_password": "Testpass1!",
                "fecha_nacimiento": "2000-01-01",
                "genero": "M",
                "cedula": "12345678",
                "numero": "abc123",
            },
            follow_redirects=True,
        )
        assert post.status_code == 200
        assert "El campo Número" in post.data.decode("utf-8", errors="replace")


def test_login_rate_limit_per_device_agent():
    with app.test_client() as client:
        get = client.get("/login")
        assert get.status_code == 200
        csrf = _extract_csrf(get.data.decode("utf-8", errors="replace"))

        headers_device_a = {"User-Agent": "DeviceA/1.0"}
        headers_device_b = {"User-Agent": "DeviceB/1.0"}

        for _ in range(10):
            resp = client.post(
                "/login",
                headers=headers_device_a,
                data={"email": "no-one@example.com", "password": "badpass", "csrf_token": csrf},
            )
            assert resp.status_code != 429

        resp = client.post(
            "/login",
            headers=headers_device_b,
            data={"email": "no-one@example.com", "password": "badpass", "csrf_token": csrf},
        )
        assert resp.status_code != 429
