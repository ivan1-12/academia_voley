<#
Setup script for Windows PowerShell to create a venv, install dependencies and run DB init.
Usage: Open PowerShell as administrator (if needed) and run: .\setup_dev.ps1
#>
param(
    [string] $dbInitFile = "mysql_init.sql",
    [string] $venvDir = ".venv"
)

Write-Host "Creating virtual environment in $venvDir..."
python -m venv $venvDir
Write-Host "To activate the virtual environment run: & './$venvDir/Scripts/Activate.ps1'"
Write-Host "Installing dependencies from requirements.txt..."
& "${venvDir}/Scripts/python.exe" -m pip install --upgrade pip
& "${venvDir}/Scripts/python.exe" -m pip install -r requirements.txt

Write-Host "If you have MySQL client available, run the next command to initialize DB (requires MySQL credentials):"
Write-Host "mysql -u USER -p < $dbInitFile"

Write-Host "Setup complete. To run tests: ${venvDir}\Scripts\python.exe -m pytest -q"