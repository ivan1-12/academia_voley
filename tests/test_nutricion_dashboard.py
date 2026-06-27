import re
import unittest

from app import app
from models import get_db
from extensions import bcrypt


class NutritionDashboardTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def _login_as_admin(self):
        response = self.client.get("/login")
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        token = match.group(1).decode("utf-8") if match else None
        return self.client.post(
            "/login",
            data={
                "email": "admin@academiavoley.net",
                "password": "AcaVoley!2026",
                "csrf_token": token,
            },
            follow_redirects=True,
        )

    def test_dashboard_counts_only_non_finished_solicitudes(self):
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "SELECT id FROM usuarios WHERE email = %s",
                ("admin@academiavoley.net",),
            )
            admin = cur.fetchone()
            trainer_id = admin["id"] if admin else 1

            cur.execute(
                "SELECT COUNT(*) AS count FROM solicitudes_equipo WHERE entrenador_id = %s AND estado IN (%s, %s, %s, %s, %s, %s)",
                (trainer_id, "pendiente", "registrado", "en proceso", "en espera", "en revisión", "procesando"),
            )
            initial_count = cur.fetchone()["count"]

            test_suffix = "_count_test"
            cur.execute(
                "INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, tipo, estado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (trainer_id, "Pendiente", f"pendiente{test_suffix}@example.com", "123", "msg", "nuevo", "pendiente"),
            )
            cur.execute(
                "INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, tipo, estado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (trainer_id, "Registrado", f"registrado{test_suffix}@example.com", "123", "msg", "academia", "registrado"),
            )
            cur.execute(
                "INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, tipo, estado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (trainer_id, "Rechazada", f"rechazada{test_suffix}@example.com", "123", "msg", "nuevo", "rechazada"),
            )
            db.commit()
            cur.close()

        self._login_as_admin()
        response = self.client.get("/dashboard_entrenador")
        match = re.search(rb"Solicitudes en tr\xc3\xa1mite.*?<h2 class=\"display-4\">(\d+)</h2>", response.data, re.S)
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1).decode("utf-8")), initial_count + 2)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "DELETE FROM solicitudes_equipo WHERE email LIKE %s",
                (f"%{test_suffix}@example.com",),
            )
            db.commit()
            cur.close()

    def test_nutricion_page_lists_players_grouped_by_gender(self):
        unique_email = "jugador_nutricion_" + str(abs(hash("test"))) + "@example.com"
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("DELETE FROM usuarios WHERE email = %s", (unique_email,))
            cur.execute("SELECT id FROM roles WHERE nombre = %s", ("jugador",))
            role = cur.fetchone()
            role_id = role["id"] if role else None
            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, genero, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                ("Jugador", "Prueba", unique_email, "hash", "jugador", role_id, "Femenino", 1),
            )
            db.commit()
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (unique_email,))
            jugador = cur.fetchone()
            if jugador:
                cur.execute(
                    "INSERT INTO perfiles_jugadores (usuario_id, altura_cm, peso_kg, posicion) VALUES (%s, %s, %s, %s)",
                    (jugador["id"], 180, 70, "Armador"),
                )
            db.commit()
            cur.close()

        self._login_as_admin()
        response = self.client.get("/gestion_nutricion", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Jugadores por g\xc3\xa9nero", response.data)
        self.assertIn(b"Jugador Prueba", response.data)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("DELETE FROM usuarios WHERE email = %s", (unique_email,))
            db.commit()
            cur.close()

    def test_assign_nutrition_rejects_nonexistent_plan(self):
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM roles WHERE nombre = %s", ("jugador",))
            role = cur.fetchone()
            role_id = role["id"] if role else None
            unique_email = "jugador_nutricion_error_" + str(abs(hash("test"))) + "@example.com"
            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, genero, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                ("Jugador", "Prueba", unique_email, "hash", "jugador", role_id, "Masculino", 1),
            )
            db.commit()
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (unique_email,))
            jugador = cur.fetchone()
            jugador_id = jugador["id"] if jugador else None
            cur.close()

        self._login_as_admin()
        response = self.client.post(
            "/asignar_nutricion",
            data={"jugador_id": jugador_id, "nutricion_id": 999999},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"nutricional", response.data.lower())

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) AS count FROM asignacion_nutricion WHERE jugador_id = %s", (jugador_id,))
            self.assertEqual(cur.fetchone()["count"], 0)
            cur.execute("DELETE FROM usuarios WHERE email = %s", (unique_email,))
            db.commit()
            cur.close()

    def test_dashboard_shows_training_list_for_assignment(self):
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO entrenamientos (titulo, descripcion, ejercicios) VALUES (%s, %s, %s)",
                ("Rutina de prueba", "Descripción de prueba", "Ejercicio 1"),
            )
            db.commit()
            cur.close()

        self._login_as_admin()
        response = self.client.get("/dashboard_entrenador")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nutrici\xc3\xb3n y rutinas", response.data)
        self.assertIn(b"Rutina de prueba", response.data)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("DELETE FROM entrenamientos WHERE titulo = %s", ("Rutina de prueba",))
            db.commit()
            cur.close()

    def test_dashboard_shows_volleyball_player_profile_data(self):
        unique_email = "jugador_voley_" + str(abs(hash("test"))) + "@example.com"
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM roles WHERE nombre = %s", ("jugador",))
            role = cur.fetchone()
            role_id = role["id"] if role else None
            cur.execute("DELETE FROM usuarios WHERE email = %s", (unique_email,))
            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, genero, activo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                ("Jugador", "Voleibol", unique_email, "hash", "jugador", role_id, "Masculino", 1),
            )
            db.commit()
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (unique_email,))
            jugador = cur.fetchone()
            cur.execute(
                "INSERT INTO perfiles_jugadores (usuario_id, altura_cm, peso_kg, posicion) VALUES (%s, %s, %s, %s)",
                (jugador["id"], 190, 82, "Armador"),
            )
            db.commit()
            cur.close()

        self._login_as_admin()
        response = self.client.get("/dashboard_entrenador")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Armador", response.data)
        self.assertIn(b"190", response.data)
        self.assertIn(b"82", response.data)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("DELETE FROM perfiles_jugadores WHERE usuario_id IN (SELECT id FROM usuarios WHERE email = %s)", (unique_email,))
            cur.execute("DELETE FROM usuarios WHERE email = %s", (unique_email,))
            db.commit()
            cur.close()

    def test_update_nutrition_plan_from_management_page(self):
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute(
                "INSERT INTO nutricion (titulo, desayuno, almuerzo, cena, merienda, hidratacion) VALUES (%s, %s, %s, %s, %s, %s)",
                ("Plan original", "Desayuno", "Almuerzo", "Cena", "Merienda", "Hidratación"),
            )
            db.commit()
            cur.execute("SELECT id FROM nutricion WHERE titulo = %s ORDER BY id DESC LIMIT 1", ("Plan original",))
            plan = cur.fetchone()
            plan_id = plan["id"] if plan else None
            cur.close()

        self._login_as_admin()
        form_response = self.client.get("/gestion_nutricion")
        match = re.search(rb'name="csrf_token" value="([^"]+)"', form_response.data)
        token = match.group(1).decode("utf-8") if match else None
        response = self.client.post(
            "/gestion_nutricion",
            data={
                "nutricion_id": plan_id,
                "titulo": "Plan actualizado",
                "desayuno": "Desayuno editado",
                "almuerzo": "Almuerzo editado",
                "cena": "Cena editada",
                "merienda": "Merienda editada",
                "hidratacion": "Hidratación editada",
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT titulo FROM nutricion WHERE id = %s", (plan_id,))
            updated = cur.fetchone()
            self.assertEqual(updated["titulo"], "Plan actualizado")
            cur.execute("DELETE FROM nutricion WHERE id = %s", (plan_id,))
            db.commit()
            cur.close()

    def test_player_dashboard_shows_progress_summary(self):
        unique_email = "jugador_progreso_" + str(abs(hash("test"))) + "@example.com"
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM roles WHERE nombre = %s", ("jugador",))
            role = cur.fetchone()
            role_id = role["id"] if role else None
            cur.execute("DELETE FROM usuarios WHERE email = %s", (unique_email,))
            password_hash = bcrypt.generate_password_hash("hash").decode("utf-8")
            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, activo) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ("Jugador", "Progreso", unique_email, password_hash, "jugador", role_id, 1),
            )
            db.commit()
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (unique_email,))
            jugador = cur.fetchone()
            jugador_id = jugador["id"] if jugador else None
            cur.execute(
                "INSERT INTO perfiles_jugadores (usuario_id, altura_cm, peso_kg, posicion) VALUES (%s, %s, %s, %s)",
                (jugador_id, 185, 78, "Central"),
            )
            cur.execute(
                "INSERT INTO nutricion (titulo, desayuno, almuerzo, cena, merienda, hidratacion) VALUES (%s, %s, %s, %s, %s, %s)",
                ("Plan prueba", "Desayuno", "Almuerzo", "Cena", "Merienda", "Hidratación"),
            )
            db.commit()
            cur.execute("SELECT id FROM nutricion WHERE titulo = %s ORDER BY id DESC LIMIT 1", ("Plan prueba",))
            plan = cur.fetchone()
            plan_id = plan["id"] if plan else None
            cur.execute("INSERT INTO asignacion_nutricion (jugador_id, nutricion_id) VALUES (%s, %s)", (jugador_id, plan_id))
            cur.execute(
                "INSERT INTO entrenamientos (titulo, descripcion, ejercicios, duracion_minutos, dificultad) VALUES (%s, %s, %s, %s, %s)",
                ("Rutina prueba", "Descripción", "Ejercicio", 45, "Media"),
            )
            db.commit()
            cur.execute("SELECT id FROM entrenamientos WHERE titulo = %s ORDER BY id DESC LIMIT 1", ("Rutina prueba",))
            entrenamiento = cur.fetchone()
            entrenamiento_id = entrenamiento["id"] if entrenamiento else None
            cur.execute(
                "INSERT INTO asignacion_entrenamientos (jugador_id, entrenamiento_id, completado) VALUES (%s, %s, %s)",
                (jugador_id, entrenamiento_id, 1),
            )
            db.commit()
            cur.close()

        response = self.client.get("/login")
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        token = match.group(1).decode("utf-8") if match else None
        login_response = self.client.post(
            "/login",
            data={
                "email": unique_email,
                "password": "hash",
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        self.assertEqual(login_response.status_code, 200)
        dashboard_response = self.client.get("/dashboard_jugador")
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn(b"Progreso general", dashboard_response.data)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("DELETE FROM asignacion_entrenamientos WHERE jugador_id = %s", (jugador_id,))
            cur.execute("DELETE FROM asignacion_nutricion WHERE jugador_id = %s", (jugador_id,))
            cur.execute("DELETE FROM perfiles_jugadores WHERE usuario_id = %s", (jugador_id,))
            cur.execute("DELETE FROM entrenamientos WHERE titulo = %s", ("Rutina prueba",))
            cur.execute("DELETE FROM nutricion WHERE id = %s", (plan_id,))
            cur.execute("DELETE FROM usuarios WHERE email = %s", (unique_email,))
            db.commit()
            cur.close()


if __name__ == "__main__":
    unittest.main()
