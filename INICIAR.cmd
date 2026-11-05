@echo off
setlocal
set "FLOOD_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%FLOOD_PYTHON%" (
  echo No se encontro el entorno Python. Consulta README.md para instalarlo.
  pause
  exit /b 1
)
echo Abre http://127.0.0.1:5050 en tu navegador cuando aparezca Running on.
echo Mantiene esta ventana abierta. Ctrl+C detiene el servidor.
"%FLOOD_PYTHON%" "%~dp0run.py"
pause
