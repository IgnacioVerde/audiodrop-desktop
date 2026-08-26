"""
youtube_downloader.py

Funciones de búsqueda/info/descarga para AudioDrop.
La búsqueda principal del main.py usa yt-dlp.exe directo, pero estas funciones
quedan para info de URLs y descarga MP3 con la librería yt_dlp.
"""

import os
import re
from pathlib import Path
from typing import Callable

from yt_dlp import YoutubeDL

from tools_manager import obtener_estado_herramientas


ProgressCallback = Callable[[dict], None]


def _sanitizar_nombre(nombre: str) -> str:
    nombre = str(nombre or "").strip()
    nombre = re.sub(r'[<>:"/\\|?*]+', "_", nombre)
    nombre = re.sub(r"\s+", " ", nombre).strip(" .")
    return nombre[:160] or "AudioDrop"


def _archivos_mp3(carpeta: str) -> set[str]:
    ruta = Path(carpeta)
    if not ruta.exists():
        return set()
    return {str(p.resolve()) for p in ruta.glob("*.mp3") if p.is_file()}


def _ffmpeg_location() -> str | None:
    estado = obtener_estado_herramientas()
    ruta = estado.get("ffmpeg_ruta") or ""
    if ruta and os.path.exists(ruta):
        return str(Path(ruta).parent)
    return None


def _base_opts(destino: str, progreso_callback: ProgressCallback | None, calidad: str) -> dict:
    opts = {
        "format": "bestaudio/best",
        "windowsfilenames": True,
        "retries": 3,
        "fragment_retries": 3,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "progress_hooks": [progreso_callback] if progreso_callback else [],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(calidad or "192"),
            }
        ],
    }

    ffmpeg = _ffmpeg_location()
    if ffmpeg:
        opts["ffmpeg_location"] = ffmpeg

    return opts


def buscar_canciones(query: str, limite: int = 8) -> list[dict]:
    """
    Búsqueda de respaldo usando yt_dlp Python.
    El main.py actual usa buscar_canciones_ytdlp() con el exe externo.
    """
    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "default_search": "ytsearch",
    }

    resultados = []

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{int(limite)}:{query}", download=False)

    for item in (info or {}).get("entries", []) or []:
        if not item:
            continue

        video_id = item.get("id") or ""
        url = item.get("webpage_url") or item.get("url") or ""
        if video_id and not str(url).startswith("http"):
            url = f"https://www.youtube.com/watch?v={video_id}"

        resultados.append(
            {
                "title": item.get("title") or "Sin título",
                "duration": item.get("duration_string") or "N/A",
                "channel": {"name": item.get("channel") or item.get("uploader") or ""},
                "link": url,
                "thumbnail": item.get("thumbnail") or "",
            }
        )

    return resultados


def es_playlist(url: str) -> bool:
    texto = str(url or "").lower()
    return "list=" in texto and "watch?" not in texto or "playlist?list=" in texto


def obtener_info_url(url: str) -> dict:
    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
        "no_warnings": True,
        "nocheckcertificate": True,
    }

    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def descargar_mp3(
    url: str,
    destino: str,
    progreso_callback: ProgressCallback | None = None,
    calidad: str = "192",
    nombre_archivo: str | None = None,
) -> dict:
    Path(destino).mkdir(parents=True, exist_ok=True)
    antes = _archivos_mp3(destino)

    opts = _base_opts(destino, progreso_callback, calidad)
    opts["noplaylist"] = True

    if nombre_archivo and str(nombre_archivo).strip():
        nombre = _sanitizar_nombre(nombre_archivo)
        opts["outtmpl"] = os.path.join(destino, f"{nombre}.%(ext)s")
    else:
        opts["outtmpl"] = os.path.join(destino, "%(title).180B.%(ext)s")

    resumen = {
        "tipo": "video",
        "completados": 0,
        "omitidos": 0,
        "errores": [],
        "lineas_log": [],
        "archivos": [],
    }

    try:
        with YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        despues = _archivos_mp3(destino)
        nuevos = sorted(despues - antes)

        resumen["archivos"] = nuevos
        resumen["completados"] = len(nuevos) if nuevos else 1
        resumen["lineas_log"].append("Video descargado correctamente.")
        return resumen
    except Exception as e:
        resumen["errores"].append(str(e))
        raise


def descargar_playlist_mp3(
    url: str,
    destino: str,
    progreso_callback: ProgressCallback | None = None,
    calidad: str = "192",
    nombre_archivo: str | None = None,
) -> dict:
    Path(destino).mkdir(parents=True, exist_ok=True)
    antes = _archivos_mp3(destino)

    opts = _base_opts(destino, progreso_callback, calidad)
    opts.update(
        {
            "noplaylist": False,
            "ignoreerrors": True,
            "outtmpl": os.path.join(destino, "%(playlist_index|)s - %(title).170B.%(ext)s"),
        }
    )

    resumen = {
        "tipo": "playlist",
        "completados": 0,
        "omitidos": 0,
        "errores": [],
        "lineas_log": [],
        "archivos": [],
    }

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        despues = _archivos_mp3(destino)
        nuevos = sorted(despues - antes)
        resumen["archivos"] = nuevos
        resumen["completados"] = len(nuevos)

        entradas = []
        if isinstance(info, dict):
            entradas = [e for e in (info.get("entries") or []) if e]

        total = len(entradas)
        if total:
            resumen["omitidos"] = max(0, total - len(nuevos))

        resumen["lineas_log"].append(
            f"Playlist procesada. Archivos nuevos: {len(nuevos)}."
        )
        return resumen
    except Exception as e:
        resumen["errores"].append(str(e))
        raise
