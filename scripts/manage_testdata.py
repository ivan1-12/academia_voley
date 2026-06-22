import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app
from models import get_db
from extensions import bcrypt
from datetime import datetime

MARK = "[AUTOTEST]"


def create():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        created = {}
        ts = int(time.time())
        try:
            # Crear entrenador de prueba
            trainer_email = f"test_trainer_{ts}@example.com"
            trainer_name = f"{MARK} Trainer {ts}"
            trainer_pass = "TestPass!23"
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (trainer_email,))
            if not cur.fetchone():
                pw = bcrypt.generate_password_hash(trainer_pass).decode("utf-8")
                cur.execute("SELECT id FROM roles WHERE nombre = 'entrenador'")
                rol_row = cur.fetchone()
                rol_id = rol_row["id"] if rol_row else None
                cur.execute(
                    "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, activo) VALUES (%s,%s,%s,%s,'entrenador',%s,1)",
                    (trainer_name, "Test", trainer_email, pw, rol_id),
                )
                created["trainer_email"] = trainer_email

            # Crear jugador de prueba
            player_email = f"test_player_{ts}@example.com"
            player_name = f"{MARK} Player {ts}"
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (player_email,))
            if not cur.fetchone():
                pw = bcrypt.generate_password_hash("PlayerPass!23").decode("utf-8")
                cur.execute("SELECT id FROM roles WHERE nombre = 'jugador'")
                rol_row = cur.fetchone()
                rol_id = rol_row["id"] if rol_row else None
                cur.execute(
                    "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id, activo) VALUES (%s,%s,%s,%s,'jugador',%s,1)",
                    (player_name, "Test", player_email, pw, rol_id),
                )
                created["player_email"] = player_email

            # Recuperar ids
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (trainer_email,))
            trow = cur.fetchone()
            trainer_id = trow["id"] if trow else None
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (player_email,))
            prow = cur.fetchone()
            player_id = prow["id"] if prow else None

            # Crear horario de prueba
            if trainer_id:
                cur.execute(
                    "INSERT INTO horarios_entrenador (entrenador_id, dias, horario, precio, descripcion, creado_at) VALUES (%s,%s,%s,%s,%s,NOW())",
                    (trainer_id, "Lunes,Miércoles", "18:00 - 20:00", "$10", f"Horario prueba {MARK}"),
                )
                created["horario"] = True

            # Crear logro (usar campos compatibes con esquemas antiguos si hace falta)
            if player_id:
                try:
                    cur.execute(
                        "INSERT INTO logros (titulo, descripcion, fecha_logro, usuario_id, imagen_url) VALUES (%s,%s,%s,%s,%s)",
                        (f"{MARK} Logro {ts}", "Logro de prueba creado por script", datetime.utcnow().date(), player_id, None),
                    )
                except Exception:
                    # Fallback a inserción sin columnas adicionales
                    cur.execute(
                        "INSERT INTO logros (titulo, descripcion, fecha_logro) VALUES (%s,%s,%s)",
                        (f"{MARK} Logro {ts}", "Logro de prueba creado por script", datetime.utcnow().date()),
                    )
                created["logro"] = True

            db.commit()
            print("Creación completada. Elementos marcados:")
            for k, v in created.items():
                print(f" - {k}: {v}")
            print("Cuando quieras, ejecuta este script con 'cleanup' para eliminar solo los elementos marcados.")
        except Exception as e:
            db.rollback()
            print("Error creando test data:", e)
        finally:
            cur.close()


def cleanup():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        try:
            # Eliminar logros con MARK
            cur.execute("DELETE FROM logros WHERE titulo LIKE %s", (f"%{MARK}%",))
            # Eliminar horarios con descripcion MARK
            cur.execute("DELETE FROM horarios_entrenador WHERE descripcion LIKE %s", (f"%{MARK}%",))
            # Eliminar usuarios creados con MARK en nombre o email
            cur.execute("DELETE FROM usuarios WHERE nombre LIKE %s OR email LIKE %s", (f"%{MARK}%", f"%test_%@example.com%"))
            # Eliminar galeria asociada por titulo
            cur.execute("DELETE FROM galeria WHERE titulo LIKE %s", (f"%{MARK}%",))
            db.commit()
            print("Limpieza completada. Se eliminaron los elementos marcados con", MARK)
        except Exception as e:
            db.rollback()
            print("Error en cleanup:", e)
        finally:
            cur.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: manage_testdata.py [create|cleanup]")
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "create":
        create()
    elif cmd == "cleanup":
        cleanup()
    else:
        print("Comando desconocido", cmd)
