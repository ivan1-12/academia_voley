import sys, os, re
sys.path.insert(0, os.getcwd())
from app import app
from models import get_db

with app.app_context():
    db = get_db()
    cur = db.cursor()
    # Crear un jugador de prueba si no existe
    cur.execute("SELECT id FROM usuarios WHERE email = %s", ("player.test@example.com",))
    row = cur.fetchone()
    if not row:
        # Insertar con rol jugador
        cur.execute("SELECT id FROM roles WHERE nombre = 'jugador'")
        rol = cur.fetchone()
        rol_id = rol['id'] if rol else None
        cur.execute("INSERT INTO usuarios (nombre, apellido, email, password, rol, rol_id) VALUES (%s,%s,%s,%s,%s,%s)",
                    ("Player","Test","player.test@example.com","testpass","jugador",rol_id))
        db.commit()
        cur.execute("SELECT id FROM usuarios WHERE email = %s", ("player.test@example.com",))
        row = cur.fetchone()
    jugador_id = row['id']

    # Crear un entrenamiento de prueba
    cur.execute("INSERT INTO entrenamientos (titulo, descripcion, ejercicios, duracion_minutos, dificultad) VALUES (%s,%s,%s,%s,%s)",
                ("Rutina Auto","Descripción","Ej1,Ej2",30,'Media'))
    db.commit()
    cur.execute("SELECT id FROM entrenamientos WHERE titulo = %s ORDER BY id DESC LIMIT 1", ("Rutina Auto",))
    ent = cur.fetchone()
    entrenamiento_id = ent['id']
    cur.close()

# Usar test_client para llamar a la ruta
with app.test_client() as client:
    # Loggear como admin
    get = client.get('/login')
    m = re.search(rb'name="csrf_token" value="([^\"]+)"', get.data)
    token = m.group(1).decode('utf-8') if m else None
    client.post('/login', data={'email': app.config.get('ADMIN_EMAIL','admin@academiavoley.net'), 'password': app.config.get('ADMIN_PASSWORD','AcaVoley!2026'), 'csrf_token': token}, follow_redirects=True)
    # Obtener token desde el dashboard donde están los formularios de asignación
    dash = client.get('/dashboard_entrenador')
    m2 = re.search(rb'name="csrf_token" value="([^\"]+)"', dash.data)
    token2 = m2.group(1).decode('utf-8') if m2 else None
    # Hacer POST a asignar incluyendo csrf_token
    resp = client.post('/asignar_entrenamiento', data={'jugador_id': str(jugador_id), 'entrenamiento_id': str(entrenamiento_id), 'csrf_token': token2}, follow_redirects=True)
    print('STATUS', resp.status_code)
    print(resp.data.decode('utf-8')[:2000])
    
    # Mostrar cualquier entrada en asignacion_entrenamientos
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM asignacion_entrenamientos WHERE jugador_id = %s AND entrenamiento_id = %s", (jugador_id, entrenamiento_id))
        print('ASIGN:', cur.fetchone())
        cur.close()
