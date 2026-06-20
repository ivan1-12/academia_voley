import re
from app import app


def test_admin_login():
    with app.test_client() as client:
        # GET login to extract CSRF
        get = client.get("/login")
        m = re.search(rb'name="csrf_token" value="([^"]+)"', get.data)
        token = m.group(1).decode("utf-8") if m else None
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
        assert b"Panel" in resp.data or b"Dashboard" in resp.data
