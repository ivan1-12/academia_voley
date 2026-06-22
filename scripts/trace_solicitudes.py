import re
import sys
import os
import traceback

# Ensure project root is on sys.path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

def main():
    with app.test_client() as c:
        r = c.get('/login')
        m = re.search(r'name="csrf_token" value="([^"]+)"', r.get_data(as_text=True))
        token = m.group(1) if m else None
        print('csrf token found:', bool(token))
        resp = c.post('/login', data={'email': 'admin@academiavoley.net', 'password': 'AcaVoley!2026', 'csrf_token': token}, follow_redirects=True)
        print('login status', resp.status_code)
        try:
            r2 = c.get('/solicitudes_equipo')
            print('/solicitudes_equipo status', r2.status_code)
            open('scripts/solicitudes_testclient_debug.html', 'w', encoding='utf-8').write(r2.get_data(as_text=True))
            print('wrote scripts/solicitudes_testclient_debug.html length', len(r2.get_data(as_text=True)))
        except Exception:
            traceback.print_exc()

if __name__ == '__main__':
    main()
