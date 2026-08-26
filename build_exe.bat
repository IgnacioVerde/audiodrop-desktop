@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean AudioDrop.spec
pause
