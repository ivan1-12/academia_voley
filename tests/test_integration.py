import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_index_loads(client):
    r = client.get("/")
    assert r.status_code == 200


def test_perfil_academico_loads(client):
    r = client.get("/perfil_academico")
    assert r.status_code == 200


def test_galeria_publica_loads(client):
    r = client.get("/galeria_publica")
    assert r.status_code == 200


def test_solicitar_unirse_get(client):
    # trainer may or may not exist; ensure endpoint responds (200 or redirect)
    r = client.get("/solicitar_unirse/1")
    assert r.status_code in (200, 302)


def test_solicitar_unirse_post_validation(client):
    # Post missing required fields to trigger validation path
    r = client.post("/solicitar_unirse/1", data={"nombre": "", "email": "bad", "mensaje": ""}, follow_redirects=True)
    # Should return 200 and render form with errors (no server error)
    assert r.status_code == 200
