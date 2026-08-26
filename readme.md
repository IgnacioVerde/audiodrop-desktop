# AudioDrop 1.1.0

App de escritorio para Windows hecha con Python + PyQt6.

## Funciones incluidas

- Buscar música en YouTube usando yt-dlp.
- Previsualizar audio antes de descargar.
- Descargar MP3 individual.
- Descargar playlists omitiendo errores.
- Biblioteca local.
- Listas propias.
- Historial.
- Reproductor inferior.
- Visualizador estético.
- Tema oscuro/claro.
- Configuración persistente en `%LOCALAPPDATA%\AudioDrop`.
- Herramientas internas en `%LOCALAPPDATA%\AudioDrop\tools`.

## Ejecutar en desarrollo

```bat
cd /d D:\programacion\ytdownloader
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

También podés usar:

```bat
run_dev.bat
```

## Crear EXE

```bat
build_exe.bat
```

O manualmente:

```bat
cd /d D:\programacion\ytdownloader
.venv\Scripts\activate
rmdir /s /q build
rmdir /s /q dist
python -m PyInstaller --noconfirm --clean AudioDrop.spec
```

## Crear instalador

Primero instalá Inno Setup si no lo tenés:

```bat
winget install --id JRSoftware.InnoSetup -e -s winget
```

Después:

```bat
build_installer.bat
```

El instalador sale en:

```text
installer\AudioDropSetup_1.1.0.exe
```
