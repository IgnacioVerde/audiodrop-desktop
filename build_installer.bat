@echo off
cd /d "%~dp0"

if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" AudioDropInstaller.iss
    pause
    exit /b
)

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" AudioDropInstaller.iss
    pause
    exit /b
)

echo No se encontro ISCC.exe.
echo Instala Inno Setup con:
echo winget install --id JRSoftware.InnoSetup -e -s winget
pause
