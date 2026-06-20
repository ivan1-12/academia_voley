# Academia Voley - Desarrollo local

Instrucciones rápidas para configurar el entorno y ejecutar pruebas localmente.

Requisitos

- Python 3.10+ (se usó un virtualenv en el proyecto)
- MySQL local con esquema inicial (ver `mysql_init.sql`)

Instalación (recomendado dentro de un virtualenv)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configurar la base de datos

- Ajusta `config.py` para apuntar a tu instancia MySQL local.
- Ejecuta `mysql_init.sql` para crear tablas y datos iniciales.

Ejecutar tests

```bash
.venv\Scripts\python.exe -m pytest -q
```

Notas

- Las pruebas usan la base de datos configurada en `config.py`; algunas pruebas crean usuarios temporales y limpian al final.
- Para problemas de CSRF en tests, las pruebas extraen el token desde las páginas GET antes de POST.
- Para formateo y linting, se incluye `.pre-commit-config.yaml` y `black`/`ruff` en `requirements.txt`.
Academia Voley - configuración MySQL (XAMPP)

Pasos rápidos para ejecutar la aplicación conectando a MySQL en XAMPP (puerto 3307):

1. Copia el ejemplo de variables de entorno (PowerShell):

   Copy-Item .env.example .env

2. Edita `.env` y ajusta al menos:
   - `SECRET_KEY` (clave larga y aleatoria)
   - `MYSQL_USER`, `MYSQL_PASSWORD` si corresponde
   - `ADMIN_PASSWORD` (cambia la contraseña por defecto del admin)

   Valores por defecto de base de datos:

   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3307
   MYSQL_USER=root
   MYSQL_PASSWORD=
   MYSQL_DB=academia_voley

3. Asegúrate que XAMPP esté ejecutando MySQL en el puerto `3307`.

4. Importa la base de datos si aún no lo hiciste: abre `mysql_init.sql` en phpMyAdmin o MySQL Workbench y ejecútalo.

5. Usa el superusuario predeterminado para acceso inicial (cámbialo en producción):
   - Email: `admin@academiavoley.net`
   - Contraseña: la definida en `ADMIN_PASSWORD` del `.env`

6. Instala dependencias e inicia la app:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\compile_translations.py
python app.py
```

> Si tu Python por defecto es 3.14 y tienes problemas para instalar `Pillow`, usa `py -3.12 -m venv .venv` en lugar de `py -3.14 -m venv .venv`.

7. Al iniciar `python app.py`, la app imprimirá las direcciones disponibles:

- `http://127.0.0.1:5000` para la misma PC
- `http://<IP_LOCAL_DE_TU_PC>:5000` para el teléfono si está en la misma red

8. Si quieres permitir el acceso desde otros dispositivos en tu red, cambia en `.env`:

```text
FLASK_HOST=0.0.0.0
```

9. Cambia el idioma en la app desde el selector en la esquina superior derecha. El idioma seleccionado se guarda en la sesión y, si el usuario está autenticado, también en su perfil.

## Logo personalizado

Tienes dos formas de cambiar el logo de "Juventud Global Sport":

**Opción A (manual):** Copia tu imagen descargada a:

`static/images/logo.png`

**Opción B (desde la app):** Inicia sesión como superadmin → Mi Panel → **Logo / Branding** → sube tu archivo.

Formatos aceptados: PNG, JPG, WEBP o SVG.

## Notas

- `FLASK_DEBUG=0` en `.env` para uso normal; pon `1` solo mientras desarrollas.
- Compila traducciones después de cambiar archivos `.po`: `python scripts\compile_translations.py`
- Un superadministrador puede gestionar usuarios, reportes y branding desde la barra de navegación.
- Cualquier usuario autenticado puede cambiar su contraseña desde el menú **Contraseña**.
