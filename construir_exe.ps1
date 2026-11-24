# Construye el ejecutable de Windows: dist\SistemaProformas.exe
#
# Uso (desde la raíz del proyecto, con el entorno virtual activado):
#     .\construir_exe.ps1
#
# Requiere: pip install -r requirements.txt pyinstaller   (el script instala PyInstaller si falta)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install --quiet --upgrade pyinstaller reportlab

# --onefile   : un solo .exe
# --windowed  : aplicación de ventanas (sin consola negra)
# --paths src : el código vive en src/proformas
# --add-data  : incluye el ícono dentro del ejecutable
python -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name SistemaProformas `
    --icon assets\icono.ico `
    --paths src `
    --add-data "assets\icono.ico;assets" `
    --exclude-module pytest `
    main.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló (código $LASTEXITCODE)" }
Write-Host "`nListo: dist\SistemaProformas.exe" -ForegroundColor Green
