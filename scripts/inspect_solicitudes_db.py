from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import get_db

with app.app_context():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, nombre, tipo, estado, email FROM solicitudes_equipo ORDER BY creado_at DESC LIMIT 50")
    rows = cur.fetchall()
    for r in rows:
        print(r.get('id'), r.get('nombre'), r.get('tipo'), r.get('estado'), r.get('email'))
    cur.close()
