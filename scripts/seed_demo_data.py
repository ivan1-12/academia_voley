import sys, os
sys.path.insert(0, os.getcwd())
from app import app
from models import get_db

ENTRENAMIENTOS = [
    ("Fuerza de Piernas I", "Sentadillas, zancadas, saltos pliométricos", "Sentadilla 4x8;Zancadas 3x10;Saltos 3x12", 45, "Alta"),
    ("Fuerza de Piernas II", "Trabajo unilateral y potencia", "Split squat 4x8;Saltos 4x10", 50, "Alta"),
    ("Resistencia Aeróbica", "Circuito cardiovascular", "Correr 20min;Saltar cuerda 10min", 40, "Media"),
    ("Core y Estabilidad", "Fortalecimiento de core", "Plancha 3x60s;Russian twists 3x30", 30, "Baja"),
    ("Velocidad y Agilidad", "Drills de velocidad", "Sprints 8x30m;Slalom 6x", 35, "Alta"),
    ("Técnica de Saque", "Ejercicios específicos de saque", "Saque parado 50 rep;Saque en movimiento 30 rep", 30, "Media"),
    ("Bloqueo y Defensa", "Trabajo de manos y reacción", "Bloqueo en parejas 5x10;Defensas 4x12", 45, "Media"),
    ("Saltos y Potencia", "Plyo y fuerza explosiva", "Cajón 5x6;Drop jumps 4x8", 40, "Alta"),
    ("Flexibilidad y Recuperación", "Estiramientos dinámicos y estáticos", "Estiramiento 20min;Movilidad 10min", 30, "Baja"),
    ("Entrenamiento Táctico", "Ejercicios de juego y posicionamiento", "Simulaciones 50min", 50, "Media"),
    ("Circuito Total Cuerpo", "Circuit training para resistencia", "Estación 1-6: 45s ON/15s OFF", 40, "Media"),
    ("Potencia de Brazos", "Foco en fuerza del tren superior", "Press 4x6;Remo 4x8", 35, "Alta"),
    ("Velocidad de Reacción", "Drills con estímulos visuales", "Reacción 6x10;Pases rápidos", 30, "Alta"),
    ("Resistencia Anaeróbica", "Intervalos intensos", "4x(400m) con 2min descanso", 45, "Alta"),
    ("Técnica de Recepción", "Recepciones en parejas y grupos", "Recepciones dirigidas 100 rep", 40, "Media"),
    ("Entrenamiento de Potencia para Saltos", "Enfocado en mejorar el salto vertical", "Plyos + fuerza específica", 45, "Alta"),
    ("Trabajo de Pases", "Mejora de precisión y control", "Pases cortos y largos 30min", 30, "Media"),
    ("Fuerza General", "Sesión de gimnasio orientada a fuerza", "Full body 3x8-10", 60, "Alta"),
    ("Recuperación Activa", "Activación suave post-competición", "Bici 20min;ejercicios movilidad", 25, "Baja"),
    ("Simulación de Partido", "Juego aplicado con condicionantes", "Partido 60min con mapas tácticos", 60, "Alta"),
]

NUTRICION = [
    ("Plan Balanceado - Mantenimiento", "Avena + frutas;Ensalada + pollo;Pescado + quinoa;Yogurt + frutos secos",),
    ("Plan Hipercalórico - Ganancia", "Batidos proteicos;Arroz + ternera;Snacks energéticos;Cena alta en calorías",),
    ("Plan Hipocalórico - Pérdida", "Desayuno ligero;Proteína magra;Verduras al vapor;Snack bajo en calorías",),
    ("Plan Alta Proteína", "Huevos;Pechuga;Batidos;Requesón",),
    ("Plan Vegetariano Proteico", "Legumbres;Tofu;Frutos secos;Huevos opcionales",),
    ("Plan Hidratación y Electrolitos", "Bebidas isotónicas;Agua frecuente;Frutas ricas en potasio",),
    ("Plan Para Competición", "Carb loading controlado;Proteína ligera;Recuperación post-competición",),
    ("Plan Recuperación", "Proteína + carbohidratos simples post-entreno;Antiinflamatorios naturales",),
    ("Plan Peso Ideal", "Control de porciones;Macros balanceados;Snacks saludables",),
    ("Plan Rendimiento", "Comidas antes/después específicas;Suplementación según objetivo",),
]


def seed():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        created_ent = 0
        created_nut = 0
        try:
            # Entrenamientos
            for t in ENTRENAMIENTOS:
                titulo = t[0]
                cur.execute("SELECT id FROM entrenamientos WHERE titulo = %s", (titulo,))
                if cur.fetchone():
                    continue
                cur.execute(
                    "INSERT INTO entrenamientos (titulo, descripcion, ejercicios, duracion_minutos, dificultad) VALUES (%s,%s,%s,%s,%s)",
                    (t[0], t[1], t[2], t[3], t[4] if len(t)>4 else None),
                )
                created_ent += 1

            # Nutrición
            for n in NUTRICION:
                titulo = n[0]
                cur.execute("SELECT id FROM nutricion WHERE titulo = %s", (titulo,))
                if cur.fetchone():
                    continue
                cur.execute(
                    "INSERT INTO nutricion (titulo, desayuno, almuerzo, cena, merienda, hidratacion) VALUES (%s,%s,%s,%s,%s,%s)",
                    (n[0], n[1].split(';')[0] if len(n[1])>0 else '', n[1].split(';')[1] if len(n[1].split(';'))>1 else '', n[1].split(';')[2] if len(n[1].split(';'))>2 else '', n[1].split(';')[3] if len(n[1].split(';'))>3 else '', ''),
                )
                created_nut += 1

            db.commit()
            print(f"Entrenamientos creados: {created_ent}")
            print(f"Planes nutricionales creados: {created_nut}")
        except Exception as e:
            db.rollback()
            print('Error al insertar seed:', e)
        finally:
            cur.close()


if __name__ == '__main__':
    seed()
