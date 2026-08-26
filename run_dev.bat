@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo No existe .venv. Creando entorno virtual...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python main.py
pause
