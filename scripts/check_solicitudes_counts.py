import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import get_db

with app.app_context():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT s.*, u.nombre AS entrenador_nombre, u.apellido AS entrenador_apellido FROM solicitudes_equipo s JOIN usuarios u ON s.entrenador_id = u.id ORDER BY s.creado_at DESC")
    solicitudes = cur.fetchall()
    solicitudes_academia = [s for s in solicitudes if s.get('tipo') == 'academia']
    solicitudes_nuevo = [s for s in solicitudes if s.get('tipo') == 'nuevo']
    solicitudes_otros = [s for s in solicitudes if s.get('tipo') not in ('nuevo','academia')]
    solicitudes_pendientes = [s for s in solicitudes if s.get('estado') == 'pendiente']
    solicitudes_archivadas = [s for s in solicitudes if s.get('estado') != 'pendiente']
    solicitudes_academia_pendientes = [s for s in solicitudes_academia if s.get('estado') == 'pendiente']
    solicitudes_nuevo_pendientes = [s for s in solicitudes_nuevo if s.get('estado') == 'pendiente']
    solicitudes_otros_pendientes = [s for s in solicitudes_otros if s.get('estado') == 'pendiente']
    print('total', len(solicitudes))
    print('nuevo total', len(solicitudes_nuevo))
    print('nuevo pendientes', len(solicitudes_nuevo_pendientes))
    print('academia total', len(solicitudes_academia))
    print('academia pendientes', len(solicitudes_academia_pendientes))
    print('archivadas', len(solicitudes_archivadas))
    cur.close()
