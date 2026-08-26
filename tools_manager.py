"""
tools_manager.py

Manejo de herramientas externas de AudioDrop:
- yt-dlp.exe
- ffmpeg.exe
- ffprobe.exe

Se guardan en %LOCALAPPDATA%\AudioDrop\tools para que la app pueda
actualizarlas sin tocar Program Files.
"""

import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path


APP_DIR_NAME = "AudioDrop"
TOOLS_DIR_NAME = "tools"

YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def obtener_carpeta_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        carpeta = Path(base) / APP_DIR_NAME
    else:
        carpeta = Path.home() / ".audiodrop"

    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def obtener_carpeta_tools() -> Path:
    carpeta = obtener_carpeta_appdata() / TOOLS_DIR_NAME
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def obtener_ruta_ytdlp() -> str:
    return str(obtener_carpeta_tools() / "yt-dlp.exe")


def obtener_ruta_ffmpeg() -> str:
    return str(obtener_carpeta_tools() / "ffmpeg.exe")


def obtener_ruta_ffprobe() -> str:
    return str(obtener_carpeta_tools() / "ffprobe.exe")


def _startupinfo_windows():
    if os.name != "nt":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}


def _ejecutar_version(comando: list[str], timeout: int = 12) -> tuple[bool, str]:
    try:
        proceso = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            **_startupinfo_windows(),
        )

        salida = (proceso.stdout or proceso.stderr or "").strip()
        primera = salida.splitlines()[0].strip() if salida else "Detectado"
        return proceso.returncode == 0, primera
    except Exception:
        return False, "No disponible"


def _descargar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".tmp")

    if temporal.exists():
        temporal.unlink()

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AudioDrop/1.1.0"},
    )

    with urllib.request.urlopen(req, timeout=120) as respuesta, temporal.open("wb") as f:
        shutil.copyfileobj(respuesta, f)

    if destino.exists():
        destino.unlink()

    temporal.replace(destino)


def descargar_ytdlp() -> None:
    _descargar(YT_DLP_URL, Path(obtener_ruta_ytdlp()))


def descargar_ffmpeg_ffprobe() -> None:
    tools_dir = obtener_carpeta_tools()

    with tempfile.TemporaryDirectory(prefix="audiodrop_ffmpeg_") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "ffmpeg.zip"
        _descargar(FFMPEG_ZIP_URL, zip_path)

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        ffmpeg_encontrado = None
        ffprobe_encontrado = None

        for ruta in extract_dir.rglob("*.exe"):
            nombre = ruta.name.lower()
            if nombre == "ffmpeg.exe":
                ffmpeg_encontrado = ruta
            elif nombre == "ffprobe.exe":
                ffprobe_encontrado = ruta

        if not ffmpeg_encontrado or not ffprobe_encontrado:
            raise RuntimeError("No se encontraron ffmpeg.exe y ffprobe.exe dentro del ZIP descargado.")

        shutil.copy2(ffmpeg_encontrado, tools_dir / "ffmpeg.exe")
        shutil.copy2(ffprobe_encontrado, tools_dir / "ffprobe.exe")


def obtener_estado_herramientas() -> dict:
    tools_dir = obtener_carpeta_tools()

    ytdlp = Path(obtener_ruta_ytdlp())
    ffmpeg_local = Path(obtener_ruta_ffmpeg())
    ffprobe_local = Path(obtener_ruta_ffprobe())

    ffmpeg_sistema = shutil.which("ffmpeg")
    ffprobe_sistema = shutil.which("ffprobe")

    ffmpeg_ruta = str(ffmpeg_local) if ffmpeg_local.exists() else (ffmpeg_sistema or "")
    ffprobe_ruta = str(ffprobe_local) if ffprobe_local.exists() else (ffprobe_sistema or "")

    yt_ok, yt_version = _ejecutar_version([str(ytdlp), "--version"]) if ytdlp.exists() else (False, "No disponible")
    ff_ok, ff_version = _ejecutar_version([ffmpeg_ruta, "-version"]) if ffmpeg_ruta else (False, "No disponible")
    fp_ok, fp_version = _ejecutar_version([ffprobe_ruta, "-version"]) if ffprobe_ruta else (False, "No disponible")

    return {
        "tools_dir": str(tools_dir),
        "yt_dlp_existe": ytdlp.exists(),
        "yt_dlp_version": yt_version if yt_ok else "No disponible",
        "yt_dlp_ruta": str(ytdlp) if ytdlp.exists() else "",
        "ffmpeg_local": ffmpeg_local.exists(),
        "ffmpeg_disponible": bool(ffmpeg_ruta) and ff_ok,
        "ffmpeg_version": ff_version if ff_ok else "No disponible",
        "ffmpeg_ruta": ffmpeg_ruta,
        "ffprobe_local": ffprobe_local.exists(),
        "ffprobe_disponible": bool(ffprobe_ruta) and fp_ok,
        "ffprobe_version": fp_version if fp_ok else "No disponible",
        "ffprobe_ruta": ffprobe_ruta,
    }


def preparar_herramientas_necesarias() -> dict:
    estado = obtener_estado_herramientas()

    if not estado["yt_dlp_existe"]:
        descargar_ytdlp()

    if not estado["ffmpeg_local"] or not estado["ffprobe_local"]:
        descargar_ffmpeg_ffprobe()

    return obtener_estado_herramientas()


def actualizar_todas_las_herramientas() -> dict:
    descargar_ytdlp()
    descargar_ffmpeg_ffprobe()
    return obtener_estado_herramientas()
