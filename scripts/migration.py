"""
Script de migración de base de datos para Academia Voley.
Agrega las columnas y tablas necesarias para el módulo de reportes y crea el Súper Usuario Único.
Ejecutar mediante:
python scripts/migration.py
"""

import os
import sys

# Agregar el directorio padre al path para importar config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pymysql
from config import Config
from flask import Flask
from flask_bcrypt import Bcrypt

# Inicializar Flask y Bcrypt para generar el hash de la contraseña de forma idéntica
_app = Flask(__name__)
_bcrypt = Bcrypt(_app)

cfg = Config()

print(
    f"Conectando a la base de datos '{cfg.MYSQL_DB}' en {cfg.MYSQL_HOST}:{cfg.MYSQL_PORT}..."
)
try:
    conn = pymysql.connect(
        host=cfg.MYSQL_HOST,
        port=cfg.MYSQL_PORT,
        user=cfg.MYSQL_USER,
        password=cfg.MYSQL_PASSWORD,
        db=cfg.MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    print("Conexión establecida con éxito.")
except Exception as e:
    print(f"Error al conectar a la base de datos: {e}")
    sys.exit(1)


def run(sql, params=None):
    with conn.cursor() as cur:
        try:
            cur.execute(sql, params or ())
            return cur.fetchall()
        except Exception as e:
            print(f"SQL Error al ejecutar [{sql[:100]}...]: {e}")
            return None


print("Aplicando cambios de esquema para el módulo de reportes...")

# 1. Agregar columna last_activity a usuarios si no existe
try:
    # Comprobar si ya existe
    res = run("SHOW COLUMNS FROM usuarios LIKE 'last_activity'")
    if not res:
        run("ALTER TABLE usuarios ADD COLUMN last_activity DATETIME DEFAULT NULL")
        print("-> Columna 'last_activity' agregada a la tabla 'usuarios'.")
    else:
        print("-> La columna 'last_activity' ya existe en 'usuarios'.")
except Exception as e:
    print(f"Error al agregar columna last_activity: {e}")

# 1b. Agregar columna activo a usuarios si no existe
try:
    res = run("SHOW COLUMNS FROM usuarios LIKE 'activo'")
    if not res:
        run("ALTER TABLE usuarios ADD COLUMN activo TINYINT(1) NOT NULL DEFAULT 1")
        print("-> Columna 'activo' agregada a la tabla 'usuarios'.")
    else:
        print("-> La columna 'activo' ya existe en 'usuarios'.")
except Exception as e:
    print(f"Error al agregar columna activo: {e}")

# 2. Asegurar columnas de usuarios usadas por el flujo de solicitudes y login
for column_name, definition in [
    ("activo", "TINYINT(1) NOT NULL DEFAULT 1"),
    ("telefono", "VARCHAR(100) DEFAULT NULL"),
    ("idioma", "VARCHAR(5) NOT NULL DEFAULT 'es'"),
    ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
]:
    try:
        res = run(f"SHOW COLUMNS FROM usuarios LIKE '{column_name}'")
        if not res:
            run(f"ALTER TABLE usuarios ADD COLUMN {column_name} {definition}")
            print(f"-> Columna '{column_name}' agregada a la tabla 'usuarios'.")
        else:
            print(f"-> La columna '{column_name}' ya existe en 'usuarios'.")
    except Exception as e:
        print(f"Error al verificar la columna {column_name}: {e}")

# 3. Asegurar columnas de entrenamientos usadas por la gestión de rutinas
for column_name, definition in [
    ("imagen_url", "VARCHAR(512) DEFAULT NULL"),
    ("fecha_creacion", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
]:
    try:
        res = run(f"SHOW COLUMNS FROM entrenamientos LIKE '{column_name}'")
        if not res:
            run(f"ALTER TABLE entrenamientos ADD COLUMN {column_name} {definition}")
            print(f"-> Columna '{column_name}' agregada a la tabla 'entrenamientos'.")
        else:
            print(f"-> La columna '{column_name}' ya existe en 'entrenamientos'.")
    except Exception as e:
        print(f"Error al verificar la columna {column_name} en entrenamientos: {e}")

# 4. Asegurar columna usuario_id en galeria si no existe
try:
    res = run("SHOW COLUMNS FROM galeria LIKE 'usuario_id'")
    if not res:
        run("ALTER TABLE galeria ADD COLUMN usuario_id INT DEFAULT NULL")
        print("-> Columna 'usuario_id' agregada a la tabla 'galeria'.")
    else:
        print("-> La columna 'usuario_id' ya existe en 'galeria'.")
except Exception as e:
    print(f"Error al verificar la columna usuario_id en galeria: {e}")

# 5. Asegurar columnas de solicitudes si no existen
for column_name, definition in [
    ("tipo", "VARCHAR(20) NOT NULL DEFAULT 'nuevo'"),
    ("estado", "VARCHAR(50) NOT NULL DEFAULT 'pendiente'"),
]:
    try:
        res = run(f"SHOW COLUMNS FROM solicitudes_equipo LIKE '{column_name}'")
        if not res:
            run(f"ALTER TABLE solicitudes_equipo ADD COLUMN {column_name} {definition}")
            print(f"-> Columna '{column_name}' agregada a la tabla 'solicitudes_equipo'.")
        else:
            print(f"-> La columna '{column_name}' ya existe en 'solicitudes_equipo'.")
    except Exception as e:
        print(f"Error al verificar la columna {column_name} en solicitudes_equipo: {e}")

# 6. Crear tabla descargas_log
run(
    """
CREATE TABLE IF NOT EXISTS descargas_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    fecha_descarga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""
)
print("-> Tabla 'descargas_log' verificada/creada.")

# 3. Asegurar los roles del sistema
run(
    "INSERT IGNORE INTO roles (nombre, descripcion) VALUES ('super_usuario', 'Administrador Total')"
)
run(
    "INSERT IGNORE INTO roles (nombre, descripcion) VALUES ('entrenador', 'Entrenador Deportivo')"
)
run(
    "INSERT IGNORE INTO roles (nombre, descripcion) VALUES ('jugador', 'Jugador de Voleybol')"
)

# Obtener los IDs de los roles
roles = run("SELECT id, nombre FROM roles")
roles_map = {r["nombre"]: r["id"] for r in roles}
print(f"Roles en el sistema: {roles_map}")

# 4. Crear o actualizar el Súper Usuario Único
admin_email = cfg.ADMIN_EMAIL
admin_password = cfg.ADMIN_PASSWORD
hashed_password = _bcrypt.generate_password_hash(admin_password).decode("utf-8")
super_usuario_rol_id = roles_map.get("super_usuario")

if not super_usuario_rol_id:
    print("Error: No se encontró el rol 'super_usuario' en la base de datos.")
    sys.exit(1)

# Verificar si ya existe algún usuario con el rol 'super_usuario'
existing_admins = run(
    "SELECT id, email FROM usuarios WHERE rol = 'super_usuario' OR rol_id = %s",
    (super_usuario_rol_id,),
)

if existing_admins:
    print(f"Ya existe un Súper Usuario en el sistema: {existing_admins[0]['email']}.")
    # Por seguridad, actualizamos su contraseña y nos aseguramos de que su email sea el único
    admin_id = existing_admins[0]["id"]
    run(
        "UPDATE usuarios SET nombre = 'Administrador', apellido = 'Academia', email = %s, password = %s, rol = 'super_usuario', rol_id = %s WHERE id = %s",
        (admin_email, hashed_password, super_usuario_rol_id, admin_id),
    )
    print(
        f"-> Súper Usuario existente (ID: {admin_id}) actualizado con correo {admin_email} y contraseña segura."
    )
else:
    # Si no existe, lo creamos
    run(
        "INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id) VALUES ('Administrador', 'Academia', %s, %s, 'super_usuario', %s)",
        (admin_email, hashed_password, super_usuario_rol_id),
    )
    print(f"-> Súper Usuario Único creado con éxito. Correo: '{admin_email}'.")

# 5. Asegurar que los permisos del súper usuario estén completos en rol_permiso
permisos = run("SELECT id, nombre FROM permisos")
if permisos:
    run("DELETE FROM rol_permiso WHERE rol_id = %s", (super_usuario_rol_id,))
    for perm in permisos:
        run(
            "INSERT IGNORE INTO rol_permiso (rol_id, permiso_id) VALUES (%s, %s)",
            (super_usuario_rol_id, perm["id"]),
        )
    print("-> Permisos del Súper Usuario actualizados en la tabla rol_permiso.")

print("Migración completada con éxito.")
conn.close()
