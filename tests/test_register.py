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
