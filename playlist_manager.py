"""
playlist_manager.py

Listas propias de AudioDrop.
Guarda un JSON en %LOCALAPPDATA%\AudioDrop\playlists.json.
"""

import json
import os
from pathlib import Path


APP_DIR_NAME = "AudioDrop"
PLAYLISTS_FILE_NAME = "playlists.json"


def obtener_carpeta_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        carpeta = Path(base) / APP_DIR_NAME
    else:
        carpeta = Path.home() / ".audiodrop"

    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def obtener_ruta_playlists() -> str:
    return str(obtener_carpeta_appdata() / PLAYLISTS_FILE_NAME)


def _normalizar(playlists) -> dict:
    if not isinstance(playlists, dict):
        return {}

    normalizadas = {}

    for nombre, rutas in playlists.items():
        nombre = str(nombre or "").strip()
        if not nombre:
            continue

        if not isinstance(rutas, list):
            rutas = []

        limpias = []
        for ruta in rutas:
            ruta = str(ruta or "").strip()
            if ruta and ruta.lower().endswith(".mp3") and ruta not in limpias:
                limpias.append(ruta)

        normalizadas[nombre] = limpias

    return normalizadas


def cargar_playlists() -> dict:
    ruta = Path(obtener_ruta_playlists())

    if not ruta.exists():
        guardar_playlists({})
        return {}

    try:
        with ruta.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalizar(data)
    except Exception:
        return {}


def guardar_playlists(playlists: dict) -> None:
    ruta = Path(obtener_ruta_playlists())
    data = _normalizar(playlists)

    with ruta.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def crear_playlist(nombre: str) -> dict:
    nombre = str(nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre de la lista no puede estar vacío.")

    playlists = cargar_playlists()
    if nombre not in playlists:
        playlists[nombre] = []
        guardar_playlists(playlists)
    return playlists


def borrar_playlist(nombre: str) -> dict:
    playlists = cargar_playlists()
    playlists.pop(nombre, None)
    guardar_playlists(playlists)
    return playlists


def agregar_archivo_a_playlist(nombre: str, ruta_archivo: str) -> dict:
    nombre = str(nombre or "").strip()
    ruta_archivo = str(ruta_archivo or "").strip()

    if not nombre:
        raise ValueError("No se indicó una lista.")

    if not ruta_archivo.lower().endswith(".mp3"):
        raise ValueError("Solo se pueden agregar archivos MP3.")

    playlists = cargar_playlists()
    playlists.setdefault(nombre, [])

    if ruta_archivo not in playlists[nombre]:
        playlists[nombre].append(ruta_archivo)

    guardar_playlists(playlists)
    return playlists


def quitar_archivo_de_playlist(nombre: str, ruta_archivo: str) -> dict:
    playlists = cargar_playlists()

    if nombre in playlists:
        playlists[nombre] = [ruta for ruta in playlists[nombre] if ruta != ruta_archivo]

    guardar_playlists(playlists)
    return playlists
