import re
import sys
import os
# Asegurar que la raíz del proyecto esté en sys.path
sys.path.insert(0, os.getcwd())
from app import app

app.config['ALLOW_SUPERUSER_CREATE_TRAINERS'] = True
email = 'auto.test.trainer@example.com'
with app.test_client() as client:
    get = client.get('/login')
    m = re.search(rb'name="csrf_token" value="([^\"]+)"', get.data)
    token = m.group(1).decode('utf-8') if m else None
    client.post('/login', data={'email': 'admin@academiavoley.net', 'password': 'AcaVoley!2026', 'csrf_token': token}, follow_redirects=True)
    form = client.get('/agregar_staff')
    m2 = re.search(rb'name="csrf_token" value="([^\"]+)"', form.data)
    token2 = m2.group(1).decode('utf-8') if m2 else None
    resp = client.post('/agregar_staff', data={'nombre': 'Auto', 'apellido': 'Tester', 'email': email, 'password': 'Testpass1!', 'confirm_password': 'Testpass1!', 'csrf_token': token2}, follow_redirects=True)
    print('STATUS:', resp.status_code)
    data = resp.data.decode('utf-8')
    print('LEN:', len(data))
    # show a slice around possible alerts
    phrase = 'Entrenador agregado correctamente'
    idx = data.find(phrase)
    print('INDEX phrase:', idx)
    if idx != -1:
        print(data[max(0, idx-200): idx+200])
    else:
            print('Phrase not found; mostrando sección de alertas y navbar:')
            start = data.find('<div class="container mt-3">')
            if start != -1:
                print(data[start:start+500])
            else:
                print(data[:1000])
