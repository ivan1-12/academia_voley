from app import app
import re

def run():
    with app.test_client() as client:
        # obtener csrf
        r = client.get('/login')
        m = re.search(rb'name="csrf_token" value="([^"]+)"', r.data)
        token = m.group(1).decode('utf-8') if m else None
        # login como superusuario/admin
        resp = client.post('/login', data={
            'email': 'admin@academiavoley.net',
            'password': 'AcaVoley!2026',
            'csrf_token': token
        }, follow_redirects=True)
        print('Login status:', resp.status_code)
        # acceder a solicitudes_equipo
        resp2 = client.get('/solicitudes_equipo')
        print('GET /solicitudes_equipo status:', resp2.status_code)
        # write output to file for inspection
        open('scripts/solicitudes_debug.html', 'wb').write(resp2.data)
        print('Response saved to scripts/solicitudes_debug.html')

if __name__ == '__main__':
    run()
