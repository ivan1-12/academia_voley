import sys, os, re
sys.path.insert(0, os.getcwd())
from app import app
from models import get_db

with app.app_context():
    db = get_db()
    cur = db.cursor()
    # tomar un jugador y un entrenamiento
    cur.execute("SELECT id FROM usuarios LIMIT 1")
    jugador = cur.fetchone()
    cur.execute("SELECT id FROM entrenamientos LIMIT 1")
    ent = cur.fetchone()
    cur.close()
    if not jugador or not ent:
        print('No hay jugador o entrenamiento en la BD')
        sys.exit(1)
    jugador_id = jugador['id']
    ent_id = ent['id']

with app.test_client() as client:
    get = client.get('/login')
    m = re.search(rb'name="csrf_token" value="([^\"]+)"', get.data)
    token = m.group(1).decode('utf-8') if m else None
    client.post('/login', data={'email': app.config.get('ADMIN_EMAIL'), 'password': app.config.get('ADMIN_PASSWORD'), 'csrf_token': token}, follow_redirects=True)
    dash = client.get('/dashboard_entrenador')
    m2 = re.search(rb'name="csrf_token" value="([^\"]+)"', dash.data)
    token2 = m2.group(1).decode('utf-8') if m2 else None

    resp = client.post('/asignar_entrenamiento', data={'jugador_id': jugador_id, 'entrenamiento_id': ent_id, 'csrf_token': token2}, headers={'X-Requested-With': 'XMLHttpRequest'})
    print('STATUS', resp.status_code)
    print('DATA', resp.get_data(as_text=True))
    
    # verificar en DB
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM asignacion_entrenamientos WHERE jugador_id = %s AND entrenamiento_id = %s", (jugador_id, ent_id))
        print('ASIGN:', cur.fetchone())
        cur.close()
