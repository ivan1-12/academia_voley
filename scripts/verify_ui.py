import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app
from models import get_db
from datetime import datetime


def find_autotest_users():
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT id, nombre, apellido, email FROM usuarios WHERE nombre LIKE %s OR email LIKE %s", ("%[AUTOTEST]%", "%test_%@example.com%"))
        rows = cur.fetchall()
        return rows
    finally:
        cur.close()


def main():
    # Desactivar CSRF para pruebas locales temporales
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        users = find_autotest_users()
        trainer = None
        player = None
        for u in users:
            if 'Trainer' in (u.get('nombre') or '') or u.get('email','').startswith('test_trainer_'):
                trainer = u
            if 'Player' in (u.get('nombre') or '') or u.get('email','').startswith('test_player_'):
                player = u

        if not trainer or not player:
            print('No se encontraron usuarios de prueba [AUTOTEST]. Asegúrate de ejecutar manage_testdata.py create primero.')
            return

        print('Trainer:', trainer)
        print('Player:', player)

    client = app.test_client()

    # Login como trainer
    login_data = {'email': trainer['email'], 'password': 'TestPass!23'}
    r = client.post('/login', data=login_data, follow_redirects=True)
    print('/login ->', r.status_code)

    # Acceder al dashboard
    r = client.get('/dashboard_entrenador')
    print('/dashboard_entrenador ->', r.status_code)

    # Ver perfil del jugador
    r = client.get(f"/perfil_jugador/{player['id']}")
    print(f"/perfil_jugador/{player['id']} ->", r.status_code)

    # Crear logro para el jugador
    logro_data = {
        'titulo': f'[AUTOTEST] Verif logro {int(datetime.now().timestamp())}',
        'descripcion': 'Creado por script de verificación',
        'fecha_logro': datetime.utcnow().strftime('%Y-%m-%d'),
        'usuario_id': player['id']
    }
    r = client.post('/gestion_logros', data=logro_data, follow_redirects=True)
    print('/gestion_logros POST ->', r.status_code)

    # Crear horario para el trainer
    horario_data = {'dias': 'Martes', 'horario': '19:00 - 21:00', 'precio': '$15', 'descripcion': '[AUTOTEST] Horario verif'}
    r = client.post('/horarios_entrenador', data=horario_data, follow_redirects=True)
    print('/horarios_entrenador POST ->', r.status_code)

    # Crear una solicitud de equipo manualmente y procesarla
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        test_email = f"verify_request_{int(datetime.now().timestamp())}@example.com"
        try:
            cur.execute("INSERT INTO solicitudes_equipo (entrenador_id, nombre, email, telefono, mensaje, tipo, estado, creado_at) VALUES (%s,%s,%s,%s,%s,'nuevo','pendiente',NOW())", (trainer['id'], '[AUTOTEST] Verify', test_email, None, 'Solicitud de verificación'))
            db.commit()
            cur.execute("SELECT id FROM solicitudes_equipo WHERE email = %s ORDER BY creado_at DESC LIMIT 1", (test_email,))
            row = cur.fetchone()
            solicitud_id = row['id']
            print('Solicitud creada id=', solicitud_id)
        finally:
            cur.close()

    # Procesar la solicitud (aceptar)
    r = client.post(f'/solicitudes_equipo/{solicitud_id}/procesar', data={'action': 'aceptar'}, follow_redirects=True)
    print(f'/solicitudes_equipo/{solicitud_id}/procesar POST ->', r.status_code)

    print('Verificación completada. Revisa la interfaz en el navegador. Ejecuta manage_testdata.py cleanup y elimina la solicitud manual creada si deseas limpiar.')


if __name__ == '__main__':
    main()
