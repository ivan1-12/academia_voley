# Academia Voley - Desarrollo local

Este proyecto es una aplicación Flask para administración de academias de voley.

## Estado actual

- La aplicación importa correctamente: `python -c "import app"` pasa.
- La suite de pruebas local pasa: `6 passed`.
- La configuración actual de dependencias se ha alineado con el entorno activo.

## Requisitos

- Python 3.10+ (probado en 3.14)
- MySQL local con esquema inicial
- `.env` configurado a partir de `.env.example`

## Configurar el entorno

1. Crear y activar el virtualenv:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

3. Editar el archivo `.env` que ya está presente en la raíz del proyecto y ajustar al menos:
   - `SECRET_KEY`
   - `MYSQL_HOST`
   - `MYSQL_PORT`
   - `MYSQL_USER`
   - `MYSQL_PASSWORD`
   - `MYSQL_DB`
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`

5. Ejecutar el script `mysql_init.sql` en tu instancia de MySQL para crear la estructura de base de datos.

## Ejecutar la aplicación

```powershell
python app.py
```

La aplicación mostrará las direcciones disponibles en la consola.

## Levantar en desarrollo (recomendado)

Usa el Python del entorno virtual para evitar problemas de dependencias:

```powershell
cd "C:\Users\JUDITH\Desktop\iver\proyecto app\academia_voley"
.venv\Scripts\python.exe app.py
```

La salida en consola indicará la URL local (por defecto `http://127.0.0.1:5000`), además de rutas estáticas y mensajes de logging.

## Probar la aplicación

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

> `pytest.ini` está configurado para que solo se ejecuten pruebas desde la carpeta `tests/`.

## Notas importantes

- `Flask-Limiter` usa almacenamiento en memoria por defecto en este proyecto. Para producción se recomienda usar un backend persistente como Redis o Memcached.
- Si modificas traducciones, ejecuta:

```powershell
python scripts\compile_translations.py
```

- El proyecto usa un único archivo `.env` en la raíz para configuración local.

- El proyecto ignora el directorio `.venv` y las carpetas de caché en `.gitignore`.

## Estado reciente tras cambios

- Todos los tests unitarios locales pasan (`6 passed`).
- Se corrigieron y mejoraron: flujo de `solicitudes_equipo`, subida y vista previa de galería, gestión de `logros` con asignación a jugadores, y pantalla de `branding`.

Si detectas algún comportamiento inesperado en un entorno concreto (puerto diferente, base de datos remota, o un SGBD distinto), dime y ajusto las instrucciones.

## Configuración de MySQL (XAMPP)

Si usas XAMPP con MySQL en el puerto `3307`:

- `MYSQL_HOST=127.0.0.1`
- `MYSQL_PORT=3307`
- `MYSQL_USER=root`
- `MYSQL_PASSWORD=`
- `MYSQL_DB=academia_voley`

## Logo personalizado

- Manual: reemplaza `static/images/logo.png`
- Desde la app: ingresa como superadmin y usa la opción de branding.

## Dependencias actualizadas

Las versiones fijadas en `requirements.txt` ahora reflejan el entorno activo usado en esta revisión.
