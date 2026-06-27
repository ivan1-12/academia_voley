import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import get_db
from pprint import pprint

with app.app_context():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM usuarios WHERE rol='jugador'")
    print('jugadores', cur.fetchone())
    cur.execute("SELECT COUNT(*) AS total FROM usuarios")
    print('usuarios', cur.fetchone())
    cur.execute("SHOW COLUMNS FROM usuarios LIKE 'telefono'")
    print('telefono column exists:', bool(cur.fetchall()))
    cur.execute("SELECT id, nombre, apellido, email, rol, activo FROM usuarios WHERE email LIKE %s", ('%@example.com',))
    print('example.com users:')
    pprint(cur.fetchall())
    cur.execute("SELECT id, nombre, apellido, email, rol, activo FROM usuarios WHERE nombre LIKE %s OR apellido LIKE %s", ('%Prueba%', '%Prueba%'))
    print('users with Prueba name:')
    pprint(cur.fetchall())
    cur.close()
