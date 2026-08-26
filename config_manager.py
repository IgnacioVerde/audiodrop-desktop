"""
config_manager.py

Configuración persistente de AudioDrop.
Guarda un JSON en %LOCALAPPDATA%\AudioDrop\config.json.
"""

import json
import os
from pathlib import Path


APP_DIR_NAME = "AudioDrop"
CONFIG_FILE_NAME = "config.json"

DEFAULT_CONFIG = {
    "carpeta_destino": "",
    "calidad_mp3": "192",
    "ultima_pestana": 0,
    "tema": "oscuro",
}

CALIDADES_VALIDAS = {"128", "192", "256", "320"}
TEMAS_VALIDOS = {"oscuro", "claro"}


def obtener_carpeta_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        carpeta = Path(base) / APP_DIR_NAME
    else:
        carpeta = Path.home() / ".audiodrop"

    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def obtener_ruta_config() -> Path:
    return obtener_carpeta_appdata() / CONFIG_FILE_NAME


def normalizar_config(config: dict) -> dict:
    normalizada = dict(DEFAULT_CONFIG)

    if isinstance(config, dict):
        normalizada.update(config)

    normalizada["calidad_mp3"] = str(normalizada.get("calidad_mp3", "192"))
    if normalizada["calidad_mp3"] not in CALIDADES_VALIDAS:
        normalizada["calidad_mp3"] = "192"

    normalizada["tema"] = str(normalizada.get("tema", "oscuro"))
    if normalizada["tema"] not in TEMAS_VALIDOS:
        normalizada["tema"] = "oscuro"

    try:
        normalizada["ultima_pestana"] = int(normalizada.get("ultima_pestana", 0))
    except Exception:
        normalizada["ultima_pestana"] = 0

    normalizada["carpeta_destino"] = str(normalizada.get("carpeta_destino", "") or "")

    return normalizada


def cargar_config() -> dict:
    ruta = obtener_ruta_config()

    if not ruta.exists():
        guardar_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        with ruta.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return normalizar_config(data)
    except Exception:
        return dict(DEFAULT_CONFIG)


def guardar_config(config: dict) -> None:
    ruta = obtener_ruta_config()
    data = normalizar_config(config)

    with ruta.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
