"""
Script de administración: crea columnas necesarias, tablas de categorías/género,
elimina jugadores existentes y crea un usuario entrenador desde variables de entorno.
Ejecutar desde el virtualenv activado:
python scripts/manage_db.py
"""

import os
import sys

# Agregar el directorio padre al path para importar config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pymysql
from config import Config
from flask_bcrypt import Bcrypt
from flask import Flask

# Crear una app Flask temporal solo para bcrypt
_app = Flask(__name__)
_app.config["SECRET_KEY"] = "temp"
_bcrypt = Bcrypt(_app)

cfg = Config()

conn = pymysql.connect(
    host=cfg.MYSQL_HOST,
    user=cfg.MYSQL_USER,
    password=cfg.MYSQL_PASSWORD,
    db=cfg.MYSQL_DB,
    port=cfg.MYSQL_PORT,
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)


def run(sql, params=None):
    with conn.cursor() as cur:
        try:
            cur.execute(sql, params or ())
            return cur.fetchall()
        except Exception as e:
            print("SQL error:", e)
            return None


print("Aplicando cambios de esquema...")
# Agregar columnas a usuarios
cols = [
    ("fecha_nacimiento", "DATE"),
    ("edad", "INT"),
    ("genero", "VARCHAR(20)"),
    ("cedula", "VARCHAR(50)"),
    ("numero", "VARCHAR(50)"),
    ("descripcion", "TEXT"),
    ("link_facebook", "VARCHAR(255)"),
    ("link_instagram", "VARCHAR(255)"),
    ("rol_id", "INT"),
]
for col, typ in cols:
    try:
        run(f"ALTER TABLE usuarios ADD COLUMN {col} {typ}")
        print(f"Añadida columna {col}")
    except Exception as e:
        print(
            f"No se pudo añadir columna {col} (probablemente ya existe o hay un error):",
            e,
        )

# Crear tablas de roles y permisos (RBAC)
run(
    """
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
)

run(
    """
CREATE TABLE IF NOT EXISTS permisos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
)

run(
    """
CREATE TABLE IF NOT EXISTS rol_permiso (
    rol_id INT NOT NULL,
    permiso_id INT NOT NULL,
    PRIMARY KEY (rol_id, permiso_id),
    FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
)

# Intentar añadir la llave foránea de rol_id en usuarios
try:
    run(
        "ALTER TABLE usuarios ADD FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE SET NULL"
    )
    print("Añadida llave foránea rol_id en usuarios")
except Exception as e:
    print("La llave foránea de rol_id ya existía o no se pudo crear:", e)

print("Esquema RBAC aplicado.")

# Seed de Roles por defecto
run(
    "INSERT IGNORE INTO roles (nombre, descripcion) VALUES ('super_usuario', 'Administrador Total')"
)
run(
    "INSERT IGNORE INTO roles (nombre, descripcion) VALUES ('entrenador', 'Entrenador Deportivo')"
)
run(
    "INSERT IGNORE INTO roles (nombre, descripcion) VALUES ('jugador', 'Jugador de Voleybol')"
)

# Seed de Permisos por defecto
permisos_data = [
    ("modificar_entrenadores", "Modificar entrenadores"),
    ("modificar_jugadores", "Modificar jugadores"),
    ("gestionar_branding", "Gestionar branding y logos"),
    ("gestionar_staff", "Gestionar miembros del staff"),
    ("editar_contenido_inicio", "Editar contenido de inicio"),
    ("recomendar_rutinas", "Recomendar rutinas"),
    ("gestionar_perfil_deportivo", "Gestionar perfil deportivo"),
    ("recomendar_nutricion", "Recomendar nutrición"),
    ("editar_staff_propio", "Editar perfil propio de staff"),
]
for perm_nombre, perm_desc in permisos_data:
    run(
        "INSERT IGNORE INTO permisos (nombre, descripcion) VALUES (%s, %s)",
        (perm_nombre, perm_desc),
    )

# Asociar permisos a roles en la DB
# Limpiar y re-asociar para asegurar consistencia
run("DELETE FROM rol_permiso")
run(
    """
INSERT INTO rol_permiso (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permisos p
WHERE r.nombre = 'super_usuario'
"""
)
run(
    """
INSERT INTO rol_permiso (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permisos p
WHERE r.nombre = 'entrenador' AND p.nombre IN (
  'recomendar_rutinas',
  'gestionar_perfil_deportivo',
  'recomendar_nutricion',
  'editar_staff_propio'
)
"""
)

# Eliminar jugadores existentes
confirm = (
    input("¿Eliminar todos los usuarios con rol='jugador'? (y/N): ").strip().lower()
)
if confirm == "y":
    run("DELETE FROM usuarios WHERE rol = 'jugador'")
    print("Usuarios jugadores eliminados.")
else:
    print("Saltando eliminación de jugadores.")

# Crear usuario entrenador usando bcrypt
trainer_name = os.environ.get("TRAINER_NOMBRE")
trainer_last = os.environ.get("TRAINER_APELLIDO")
trainer_email = os.environ.get("TRAINER_EMAIL")
trainer_password = os.environ.get("TRAINER_PASSWORD")

if not all([trainer_name, trainer_last, trainer_email, trainer_password]):
    print("Faltan variables de entorno necesarias para crear el entrenador.")
    print(
        "Define TRAINER_NOMBRE, TRAINER_APELLIDO, TRAINER_EMAIL y TRAINER_PASSWORD antes de ejecutar este script."
    )
    sys.exit(1)

hashed = _bcrypt.generate_password_hash(trainer_password).decode("utf-8")

# Eliminar entrenador con mismo email para recrearlo
run("DELETE FROM usuarios WHERE email = %s", (trainer_email,))

# Obtener ID del rol entrenador
roles_res = run("SELECT id FROM roles WHERE nombre = 'entrenador'")
entrenador_rol_id = roles_res[0]["id"] if roles_res else None

run(
    "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id) VALUES (%s, %s, %s, %s, 'entrenador', %s)",
    (trainer_name, trainer_last, trainer_email, hashed, entrenador_rol_id),
)
print(f"Usuario entrenador creado: {trainer_email} (rol_id: {entrenador_rol_id})")

# Re-mapear usuarios existentes sin rol_id para compatibilidad
run(
    """
UPDATE usuarios u 
INNER JOIN roles r ON u.rol = r.nombre 
SET u.rol_id = r.id 
WHERE u.rol_id IS NULL
"""
)

print("Creación de carpeta de uploads si es necesario...")
os.makedirs(cfg.UPLOAD_FOLDER, exist_ok=True)
print("Listo.")
