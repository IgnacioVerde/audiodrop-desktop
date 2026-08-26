"""
utils.py

Funciones auxiliares de rutas, archivos y detección simple de URLs.
"""

import os
import re
from pathlib import Path
from datetime import datetime


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".webm"}


def obtener_ruta_musica() -> str:
    """
    Devuelve una carpeta Música/Musica usable y la crea si no existe.
    En Windows intenta usar ~/Music. Si no existe, usa Desktop/Musica.
    """
    posibles = [
        Path.home() / "Music",
        Path.home() / "Música",
        Path.home() / "Desktop" / "Musica",
        Path.home() / "Escritorio" / "Musica",
    ]

    for ruta in posibles:
        try:
            ruta.mkdir(parents=True, exist_ok=True)
            return str(ruta)
        except Exception:
            continue

    ruta = Path.home() / "AudioDrop"
    ruta.mkdir(parents=True, exist_ok=True)
    return str(ruta)


def _formatear_tamano(bytes_size: int) -> str:
    try:
        size = int(bytes_size)
    except Exception:
        return "-"

    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def listar_media_en_carpeta(carpeta: str, tipo: str = "audio") -> list[dict]:
    """
    Lista archivos multimedia en una carpeta.
    Para AudioDrop desktop se usa principalmente con tipo='audio'.
    """
    carpeta_path = Path(carpeta or "")
    if not carpeta_path.exists() or not carpeta_path.is_dir():
        return []

    extensiones = AUDIO_EXTENSIONS if tipo == "audio" else AUDIO_EXTENSIONS
    archivos = []

    for ruta in carpeta_path.iterdir():
        if not ruta.is_file():
            continue

        if ruta.suffix.lower() not in extensiones:
            continue

        try:
            stat = ruta.stat()
            fecha = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
            tamano = _formatear_tamano(stat.st_size)
        except Exception:
            fecha = "-"
            tamano = "-"

        archivos.append(
            {
                "nombre": ruta.name,
                "ruta": str(ruta),
                "tipo": "audio",
                "icono": "♪",
                "tamano": tamano,
                "fecha": fecha,
            }
        )

    archivos.sort(key=lambda item: item["nombre"].lower())
    return archivos


def listar_mp3_en_carpeta(carpeta: str) -> list[str]:
    if not os.path.exists(carpeta):
        return []
    return [f for f in os.listdir(carpeta) if f.lower().endswith(".mp3")]


def es_url(texto: str) -> bool:
    texto = str(texto or "").strip()
    if not texto:
        return False

    patron = re.compile(
        r"^(https?://)?"
        r"([\w\-]+\.)+[\w\-]+"
        r"(:\d+)?"
        r"(/[^\s]*)?$",
        re.IGNORECASE,
    )
    return bool(patron.match(texto))
