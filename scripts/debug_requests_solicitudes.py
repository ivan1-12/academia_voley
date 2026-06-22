import requests
import re

BASE = 'http://127.0.0.1:5000'

def main():
    s = requests.Session()
    # get login page
    r = s.get(f'{BASE}/login')
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    token = m.group(1) if m else None
    print('csrf token:', bool(token))
    # post login
    resp = s.post(f'{BASE}/login', data={'email': 'admin@academiavoley.net', 'password': 'AcaVoley!2026', 'csrf_token': token}, allow_redirects=True)
    print('login status', resp.status_code)
    # get solicitudes
    r2 = s.get(f'{BASE}/solicitudes_equipo')
    print('/solicitudes_equipo status', r2.status_code)
    open('scripts/solicitudes_requests_debug.html','w',encoding='utf-8').write(r2.text)
    print('wrote scripts/solicitudes_requests_debug.html length', len(r2.text))

if __name__ == '__main__':
    main()
