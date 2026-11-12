@echo off
REM Arrancar la aplicacion DCF desde 10-K
REM Uso: doble clic o ejecutar desde la linea de comandos

cd /d "%~dp0"

REM Añadir uv al PATH si no esta
set "PATH=%USERPROFILE%\AppData\Roaming\Python\Python315\Scripts;%PATH%"

echo Iniciando la aplicacion DCF...
echo Accede a http://localhost:8502 en tu navegador
echo.

uv run streamlit run src/dcf_app/ui/app.py --server.headless true --server.port 8502