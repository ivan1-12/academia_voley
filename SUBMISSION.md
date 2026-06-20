## Entrega del proyecto - Checklist

Pasos recomendados antes de subir al repositorio de la universidad:

1. Verifica que `config.py` apunta a tu base de datos local y que `mysql_init.sql` fue importado.
2. Ejecuta las pruebas localmente:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

3. Aplica el formateo y lint (si no lo hiciste):

```powershell
.venv\Scripts\python.exe -m black .
.venv\Scripts\python.exe -m ruff check --fix .
```

4. Inicializa git y sube a tu repositorio escolar (reemplaza la URL del remote):

```powershell
git init
git add .
git commit -m "Entrega proyecto academia_voley - listo para corrección"
git remote add origin https://github.com/UNIVERSIDAD/REPO.git
git branch -M main
git push -u origin main
```

5. Incluye en la descripción del repo las instrucciones breves para ejecutar (usa `README.md`).

Si quieres, puedo:
- preparar el commit automáticamente (solo si me das la URL del remote y autorizas el push),
- o generar un ZIP listo para subir.
