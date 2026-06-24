<#
Automatiza la preparación del entorno de desarrollo en Windows PowerShell.
Uso:
  ./scripts/setup_env.ps1 [-UseDocker] [-DbRootPassword <password>] [-DbPort <port>] [-SkipDbImport]

Opciones:
  -UseDocker           : Levanta un contenedor MySQL (recomendado si no tienes MySQL local).
  -DbRootPassword      : Contraseña para el root de MySQL en Docker (default: rootpw).
  -DbPort              : Puerto en Windows que mapeará al 3306 del contenedor (default: 3307).
  -SkipDbImport        : No ejecutar la importación de `mysql_init.sql`.
  -VenvDir             : Directorio del virtualenv (default: .venv)
  -EnvFile             : Ruta al archivo .env a crear/usar (default: .env)

Ejemplo:
  ./scripts/setup_env.ps1 -UseDocker -DbRootPassword mypw -DbPort 3307
#>

param(
    [switch] $UseDocker = $false,
    [string] $DbRootPassword = "rootpw",
    [int] $DbPort = 3307,
    [switch] $SkipDbImport = $false,
    [string] $VenvDir = ".venv",
    [string] $EnvFile = ".env"
)

Set-StrictMode -Version Latest

$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $here

Write-Host "== Preparando entorno en: $here =="

if (-Not (Test-Path $VenvDir)) {
    Write-Host "Creando virtualenv en $VenvDir..."
    python -m venv $VenvDir
} else {
    Write-Host "Virtualenv ya existe en $VenvDir"
}

Write-Host "Activación rápida (PowerShell): & '$VenvDir/Scripts/Activate.ps1'"

Write-Host "Actualizando pip e instalando dependencias..."
& "$VenvDir/Scripts/python.exe" -m pip install --upgrade pip
& "$VenvDir/Scripts/python.exe" -m pip install -r requirements.txt

# Crear .env si no existe
if (-Not (Test-Path $EnvFile)) {
    Write-Host "Creando archivo $EnvFile con valores por defecto (edítalo si es necesario)..."
    $envContent = @()
    $envContent += "SECRET_KEY=$(python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY)"
    $envContent += "MYSQL_HOST=127.0.0.1"
    $envContent += "MYSQL_USER=root"
    $envContent += "MYSQL_PASSWORD="
    $envContent += "MYSQL_DB=academia_voley"
    $envContent += "MYSQL_PORT=$DbPort"
    $envContent += "FLASK_DEBUG=1"
    $envContent += "FLASK_HOST=0.0.0.0"
    $envContent += "FLASK_PORT=5000"
    $envContent | Out-File -FilePath $EnvFile -Encoding utf8
} else {
    Write-Host "$EnvFile ya existe — no lo sobrescribo (edítalo si necesitas cambiar valores)."
}

if ($UseDocker) {
    # Levantar MySQL con Docker
    Write-Host "Iniciando MySQL en Docker (contenedor: academia-db)..."
    # Comprobar si el contenedor ya existe
    $exists = docker ps -a --format "{{.Names}}" | Select-String -Pattern "^academia-db$"
    if ($exists) {
        Write-Host "Contenedor academia-db ya existe. Si quieres recrearlo, elimínalo con: docker rm -f academia-db"
    } else {
        docker run --name academia-db -e MYSQL_ROOT_PASSWORD=$DbRootPassword -e MYSQL_DATABASE=academia_voley -p $DbPort:3306 -d mysql:8 || {
            Write-Host "Fallo levantando el contenedor MySQL. Asegúrate de que Docker está corriendo."; Pop-Location; exit 1
        }
        Write-Host "Esperando 10 segundos para que MySQL inicialice..."
        Start-Sleep -Seconds 10
    }

    if (-Not $SkipDbImport) {
        Write-Host "Importando mysql_init.sql al contenedor (si existe)..."
        if (Test-Path "mysql_init.sql") {
            docker cp "mysql_init.sql" academia-db:/tmp/mysql_init.sql
            docker exec -i academia-db sh -c "mysql -u root -p\"$DbRootPassword\" academia_voley < /tmp/mysql_init.sql" || Write-Host "Advertencia: Import falló. Comprueba logs del contenedor."
        } else {
            Write-Host "No se encontró mysql_init.sql en la raíz del repo — salto import."
        }
    } else {
        Write-Host "SkipDbImport activado — no se importa la base de datos."
    }
} else {
    Write-Host "UseDocker no activado. Asumo que tienes MySQL local disponible en el puerto configurado ($DbPort)."
    if (-Not $SkipDbImport) {
        Write-Host "Si tienes cliente mysql, puedes importar la BD ahora con:\nmysql -u root -p -h 127.0.0.1 -P $DbPort < mysql_init.sql"
    }
}

Write-Host "Setup finalizado. Para activar el entorno y ejecutar la app:"
Write-Host "  & '$VenvDir/Scripts/Activate.ps1'"
Write-Host "  .\$VenvDir\Scripts\python.exe app.py"

Pop-Location

Write-Host "Listo."