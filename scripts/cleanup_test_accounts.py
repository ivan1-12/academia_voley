import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import get_db

with app.app_context():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM usuarios WHERE email LIKE %s", ("%@example.com",))
    total = cur.fetchone()
    print('Cuentas @example.com encontradas:', total)
    cur.execute("DELETE FROM usuarios WHERE email LIKE %s", ("%@example.com",))
    db.commit()
    cur.execute("SELECT COUNT(*) AS total FROM usuarios WHERE email LIKE %s", ("%@example.com",))
    print('Cuentas @example.com restantes:', cur.fetchone())
    cur.close()
