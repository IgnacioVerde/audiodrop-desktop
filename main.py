import sys
import os
import random
import math
import json
import subprocess
import urllib.request
import webbrowser
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QHBoxLayout,
    QTabWidget,
    QComboBox,
    QScrollArea,
    QFrame,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QInputDialog,
    QMenu,
)

from PyQt6.QtCore import QThread, pyqtSignal, Qt, QUrl, QTimer, QRectF
from PyQt6.QtGui import QPixmap, QIcon, QAction, QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from youtube_downloader import (
    buscar_canciones,
    descargar_mp3,
    es_playlist,
    descargar_playlist_mp3,
    obtener_info_url,
)

from utils import (
    obtener_ruta_musica,
    listar_media_en_carpeta,
    es_url,
)

from styles import obtener_estilo
from config_manager import cargar_config, guardar_config

from playlist_manager import (
    cargar_playlists,
    guardar_playlists,
    crear_playlist,
    borrar_playlist,
    agregar_archivo_a_playlist,
    quitar_archivo_de_playlist,
    obtener_ruta_playlists,
)

from tools_manager import (
    preparar_herramientas_necesarias,
    actualizar_todas_las_herramientas,
    obtener_estado_herramientas,
)


APP_NAME = "AudioDrop"
APP_SUBTITLE = "Buscá, descargá, organizá y reproducí tu música."


def obtener_ruta_recurso(ruta_relativa):
    """
    Devuelve la ruta absoluta de un recurso.

    Funciona en desarrollo y compilado con PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    return str(base_path / ruta_relativa)



def obtener_ruta_ytdlp_para_busqueda():
    """
    Devuelve la ruta de yt-dlp.exe para búsquedas.

    Esta búsqueda NO usa youtube-search-python ni httpx.
    Usa el mismo yt-dlp externo que ya usa AudioDrop para descargar/previsualizar.
    """
    try:
        estado = obtener_estado_herramientas()
        tools_dir = estado.get("tools_dir", "")

        if tools_dir:
            posible = os.path.join(tools_dir, "yt-dlp.exe")
            if os.path.exists(posible):
                return posible
    except Exception:
        pass

    posible_local = obtener_ruta_recurso("tools/yt-dlp.exe")
    if os.path.exists(posible_local):
        return posible_local

    return "yt-dlp"


def formatear_duracion_segundos(segundos):
    """
    Convierte una duración en segundos a formato mm:ss o hh:mm:ss.
    """
    try:
        segundos = int(segundos or 0)
    except Exception:
        return "N/A"

    if segundos <= 0:
        return "N/A"

    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    seg = segundos % 60

    if horas > 0:
        return f"{horas}:{minutos:02d}:{seg:02d}"

    return f"{minutos}:{seg:02d}"


def obtener_mejor_miniatura(info):
    """
    Toma la mejor miniatura disponible de yt-dlp.
    """
    miniatura = info.get("thumbnail") or ""

    thumbnails = info.get("thumbnails") or []
    if isinstance(thumbnails, list) and thumbnails:
        candidatos = []

        for item in thumbnails:
            if not isinstance(item, dict):
                continue

            url = item.get("url") or ""
            if not url:
                continue

            ancho = int(item.get("width") or 0)
            alto = int(item.get("height") or 0)
            candidatos.append((ancho * alto, url))

        if candidatos:
            candidatos.sort(reverse=True)
            miniatura = candidatos[0][1]

    return miniatura


def buscar_canciones_ytdlp(query, limite=8):
    """
    Busca videos en YouTube usando yt-dlp directamente.

    Esto evita el error de:
        post() got an unexpected keyword argument 'proxies'

    Ese error viene de youtube-search-python/httpx. Para el instalador definitivo
    conviene depender de yt-dlp, que AudioDrop ya usa para descargas y preview.
    """
    yt_dlp = obtener_ruta_ytdlp_para_busqueda()
    consulta = f"ytsearch{int(limite)}:{query}"

    comando = [
        yt_dlp,
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--ignore-errors",
        consulta,
    ]

    kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": 45,
        "encoding": "utf-8",
        "errors": "replace",
    }

    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        proceso = subprocess.run(comando, **kwargs)
    except subprocess.TimeoutExpired:
        raise Exception("La búsqueda tardó demasiado. Probá de nuevo en unos segundos.")
    except FileNotFoundError:
        raise Exception("No se encontró yt-dlp.exe. Revisá la pestaña Configuración y prepará las herramientas.")

    if proceso.returncode != 0 and not proceso.stdout.strip():
        error = (proceso.stderr or "No se pudo buscar en YouTube.").strip()
        raise Exception(error)

    resultados = []

    for linea in proceso.stdout.splitlines():
        linea = linea.strip()
        if not linea:
            continue

        try:
            info = json.loads(linea)
        except Exception:
            continue

        video_id = info.get("id") or ""
        url = info.get("url") or info.get("webpage_url") or ""

        if video_id and not str(url).startswith("http"):
            url = f"https://www.youtube.com/watch?v={video_id}"

        titulo = info.get("title") or "Sin título"
        canal = info.get("channel") or info.get("uploader") or info.get("uploader_id") or ""
        duracion = info.get("duration_string") or formatear_duracion_segundos(info.get("duration"))
        miniatura = obtener_mejor_miniatura(info)

        if not url:
            continue

        resultados.append(
            {
                "title": titulo,
                "duration": duracion,
                "channel": {"name": canal},
                "link": url,
                "thumbnail": miniatura,
            }
        )

        if len(resultados) >= limite:
            break

    return resultados


class AudioDropLineEdit(QLineEdit):
    """
    QLineEdit personalizado para que el menú contextual salga en español.
    """

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        accion_deshacer = QAction("Deshacer\tCtrl+Z", self)
        accion_deshacer.triggered.connect(self.undo)
        accion_deshacer.setEnabled(self.isUndoAvailable())
        menu.addAction(accion_deshacer)

        accion_rehacer = QAction("Rehacer\tCtrl+Y", self)
        accion_rehacer.triggered.connect(self.redo)
        accion_rehacer.setEnabled(self.isRedoAvailable())
        menu.addAction(accion_rehacer)

        menu.addSeparator()

        accion_cortar = QAction("Cortar\tCtrl+X", self)
        accion_cortar.triggered.connect(self.cut)
        accion_cortar.setEnabled(self.hasSelectedText())
        menu.addAction(accion_cortar)

        accion_copiar = QAction("Copiar\tCtrl+C", self)
        accion_copiar.triggered.connect(self.copy)
        accion_copiar.setEnabled(self.hasSelectedText())
        menu.addAction(accion_copiar)

        accion_pegar = QAction("Pegar\tCtrl+V", self)
        accion_pegar.triggered.connect(self.paste)
        accion_pegar.setEnabled(bool(QApplication.clipboard().text()))
        menu.addAction(accion_pegar)

        accion_eliminar = QAction("Eliminar", self)
        accion_eliminar.triggered.connect(lambda: self.insert(""))
        accion_eliminar.setEnabled(self.hasSelectedText())
        menu.addAction(accion_eliminar)

        menu.addSeparator()

        accion_todo = QAction("Seleccionar todo\tCtrl+A", self)
        accion_todo.triggered.connect(self.selectAll)
        accion_todo.setEnabled(len(self.text()) > 0)
        menu.addAction(accion_todo)

        menu.exec(event.globalPos())


class VisualizadorWidget(QWidget):
    """
    Visualizador estético hecho con PyQt6 puro.

    No analiza frecuencias reales todavía. Se anima según:
    - estado de reproducción,
    - posición del tema,
    - volumen,
    - valores suaves pseudoaleatorios.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(320)
        self.setMouseTracking(True)

        self.reproductor = None
        self.audio_output = None
        self.titulo_actual = "Nada reproduciendo"
        self.tema = "oscuro"
        self.modo = "Barras suaves"
        self.intensidad = 70
        self.velocidad = 60
        self.fase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)

    def set_reproductor(self, reproductor, audio_output):
        self.reproductor = reproductor
        self.audio_output = audio_output

    def set_tema(self, tema):
        self.tema = tema or "oscuro"
        self.update()

    def set_modo(self, modo):
        self.modo = modo or "Barras suaves"
        self.update()

    def set_intensidad(self, valor):
        self.intensidad = max(10, min(100, int(valor)))
        self.update()

    def set_velocidad(self, valor):
        self.velocidad = max(10, min(100, int(valor)))
        self.update()

    def set_titulo(self, titulo):
        self.titulo_actual = titulo or "Nada reproduciendo"
        self.update()

    def esta_reproduciendo(self):
        if not self.reproductor:
            return False
        return self.reproductor.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def obtener_posicion_normalizada(self):
        if not self.reproductor:
            return 0.0

        duracion = self.reproductor.duration()
        posicion = self.reproductor.position()

        if duracion <= 0:
            return 0.0

        return max(0.0, min(1.0, posicion / duracion))

    def obtener_volumen(self):
        if not self.audio_output:
            return 0.65
        return max(0.05, min(1.0, self.audio_output.volume()))

    def tick(self):
        avance = 0.035 + (self.velocidad / 1000.0)
        if self.esta_reproduciendo():
            self.fase += avance
        else:
            self.fase += avance * 0.18
        self.update()

    def colores(self):
        if self.tema == "claro":
            return {
                "fondo_1": QColor("#F7FAFE"),
                "fondo_2": QColor("#DDEAF7"),
                "linea": QColor("#2563EB"),
                "linea_2": QColor("#06A5D8"),
                "texto": QColor("#0C1B31"),
                "muted": QColor("#60758D"),
                "grid": QColor(37, 99, 235, 32),
                "panel": QColor(255, 255, 255, 135),
            }

        return {
            "fondo_1": QColor("#09111B"),
            "fondo_2": QColor("#122942"),
            "linea": QColor("#3B82F6"),
            "linea_2": QColor("#22D3EE"),
            "texto": QColor("#EAF4FF"),
            "muted": QColor("#8EA4BC"),
            "grid": QColor(95, 165, 255, 35),
            "panel": QColor(16, 30, 46, 145),
        }

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(8, 8, -8, -8)
        c = self.colores()

        grad = QLinearGradient(float(rect.left()), float(rect.top()), float(rect.right()), float(rect.bottom()))
        grad.setColorAt(0.0, c["fondo_1"])
        grad.setColorAt(1.0, c["fondo_2"])
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(c["grid"], 1))
        painter.drawRoundedRect(rect, 18, 18)

        self.dibujar_grid_suave(painter, rect, c)

        panel_titulo = QRectF(rect.left() + 18, rect.top() + 16, rect.width() - 36, 54)
        painter.setBrush(QBrush(c["panel"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(panel_titulo, 12, 12)

        painter.setPen(c["texto"])
        fuente = painter.font()
        fuente.setPointSize(12)
        fuente.setBold(True)
        painter.setFont(fuente)
        painter.drawText(panel_titulo.adjusted(14, 6, -14, -24), Qt.AlignmentFlag.AlignLeft, "Visualizador")

        fuente.setPointSize(9)
        fuente.setBold(False)
        painter.setFont(fuente)
        painter.setPen(c["muted"])
        estado = "Reproduciendo" if self.esta_reproduciendo() else "En espera / pausado"
        texto = f"{estado} · {self.modo} · {self.titulo_actual}"
        painter.drawText(panel_titulo.adjusted(14, 28, -14, -4), Qt.AlignmentFlag.AlignLeft, texto)

        area = rect.adjusted(24, 88, -24, -26)

        try:
            if self.modo == "Ondas suaves":
                self.dibujar_ondas(painter, area, c)
            elif self.modo == "Círculo pulsante":
                self.dibujar_circulo(painter, area, c)
            elif self.modo == "Nebulosa":
                self.dibujar_nebulosa(painter, area, c)
            else:
                self.dibujar_barras(painter, area, c)
        except Exception:
            # Fallback visual: si un modo falla, no dejamos que el paintEvent
            # tire abajo la app. Volvemos a barras, que es el modo más simple.
            self.dibujar_barras(painter, area, c)

    def dibujar_grid_suave(self, painter, rect, c):
        painter.setPen(QPen(c["grid"], 1))
        paso = 42
        x = rect.left() + paso
        while x < rect.right():
            painter.drawLine(int(x), int(rect.top() + 12), int(x), int(rect.bottom() - 12))
            x += paso

        y = rect.top() + paso
        while y < rect.bottom():
            painter.drawLine(int(rect.left() + 12), int(y), int(rect.right() - 12), int(y))
            y += paso

    def intensidad_base(self):
        volumen = self.obtener_volumen()
        reproduciendo = 1.0 if self.esta_reproduciendo() else 0.28
        return (self.intensidad / 100.0) * volumen * reproduciendo

    def dibujar_barras(self, painter, area, c):
        barras = 54
        espacio = 5
        ancho = max(4, (area.width() - espacio * (barras - 1)) / barras)
        centro_y = area.center().y()
        base = self.intensidad_base()
        progreso = self.obtener_posicion_normalizada()

        for i in range(barras):
            x = area.left() + i * (ancho + espacio)
            onda = math.sin(self.fase * 2.0 + i * 0.38) * 0.5 + 0.5
            onda2 = math.sin(self.fase * 3.1 + i * 0.17 + progreso * 8) * 0.5 + 0.5
            altura = 18 + (area.height() * 0.78) * base * (0.18 + onda * 0.58 + onda2 * 0.24)
            y = centro_y - altura / 2

            color = QColor(c["linea"])
            if i % 3 == 0:
                color = QColor(c["linea_2"])
            color.setAlpha(150 + int(90 * onda))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(x, y, ancho, altura), 4, 4)

    def dibujar_ondas(self, painter, area, c):
        """
        Dibuja ondas suaves sin usar sobrecargas ambiguas de PyQt6.

        Corrección importante:
        PyQt6 puede crashear o tirar TypeError si a QPen se le pasa un ancho
        float directamente en el constructor. Por eso usamos setWidthF().
        También usamos QPainterPath con coordenadas float, que es más estable
        para curvas/líneas suaves que drawLine en bucle.
        """
        base = self.intensidad_base()

        for capa in range(4):
            color = QColor(c["linea"] if capa % 2 == 0 else c["linea_2"])
            color.setAlpha(max(45, 185 - capa * 34))

            pen = QPen(color)
            pen.setWidthF(max(1.0, 2.2 - capa * 0.25))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            amplitud = area.height() * (0.08 + 0.06 * capa) * (0.45 + base)
            frecuencia = 2.0 + capa * 0.65

            path = QPainterPath()
            primer_punto = True

            for px in range(int(area.left()), int(area.right()), 6):
                t = (float(px) - float(area.left())) / max(1.0, float(area.width()))

                y = float(area.center().y())
                y += math.sin(t * math.pi * 2 * frecuencia + self.fase * (1.4 + capa * 0.35)) * amplitud
                y += math.sin(t * math.pi * 2 * (frecuencia * 0.43) - self.fase * 0.8) * amplitud * 0.35

                if primer_punto:
                    path.moveTo(float(px), float(y))
                    primer_punto = False
                else:
                    path.lineTo(float(px), float(y))

            painter.drawPath(path)

    def dibujar_circulo(self, painter, area, c):
        base = self.intensidad_base()
        centro = area.center()
        radio_base = min(area.width(), area.height()) * 0.20

        for i in range(7):
            pulso = math.sin(self.fase * 2.5 - i * 0.5) * 0.5 + 0.5
            radio = radio_base + i * 18 + pulso * 26 * base
            color = QColor(c["linea"] if i % 2 == 0 else c["linea_2"])
            color.setAlpha(max(22, 150 - i * 18))
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(centro, radio, radio)

        color_centro = QColor(c["linea"])
        color_centro.setAlpha(190)
        painter.setBrush(QBrush(color_centro))
        painter.setPen(Qt.PenStyle.NoPen)
        radio_centro = radio_base * 0.55 + math.sin(self.fase * 3.5) * 8 * base
        painter.drawEllipse(centro, radio_centro, radio_centro)

    def dibujar_nebulosa(self, painter, area, c):
        base = self.intensidad_base()
        cantidad = 80
        for i in range(cantidad):
            t = i / cantidad
            ang = t * math.pi * 8 + self.fase * (0.6 + t)
            dist = (0.12 + 0.82 * t) * min(area.width(), area.height()) * 0.48
            dist *= 0.65 + base * 0.55
            x = area.center().x() + math.cos(ang) * dist
            y = area.center().y() + math.sin(ang * 0.74) * dist * 0.62
            r = 2.0 + (math.sin(self.fase * 2 + i) * 0.5 + 0.5) * 5.5 * base
            color = QColor(c["linea"] if i % 2 == 0 else c["linea_2"])
            color.setAlpha(70 + int(120 * (1 - t)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QRectF(x - r, y - r, r * 2, r * 2))


class WorkerPreviewAudio(QThread):
    """
    Obtiene una URL temporal de audio usando yt-dlp para previsualizar
    sin descargar el MP3 final.
    """

    terminado = pyqtSignal(bool, str, str)

    def __init__(self, url_video):
        super().__init__()
        self.url_video = url_video

    def run(self):
        try:
            estado = obtener_estado_herramientas()
            tools_dir = estado.get("tools_dir", "")

            yt_dlp = "yt-dlp"
            if tools_dir:
                posible = os.path.join(tools_dir, "yt-dlp.exe")
                if os.path.exists(posible):
                    yt_dlp = posible

            if yt_dlp == "yt-dlp":
                posible_local = obtener_ruta_recurso("tools/yt-dlp.exe")
                if os.path.exists(posible_local):
                    yt_dlp = posible_local

            comando = [
                yt_dlp,
                "--no-playlist",
                "--no-warnings",
                "-f",
                "bestaudio/best",
                "-g",
                self.url_video,
            ]

            kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 35,
                "encoding": "utf-8",
                "errors": "replace",
            }

            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            proceso = subprocess.run(comando, **kwargs)

            if proceso.returncode != 0:
                error = (proceso.stderr or proceso.stdout or "No se pudo obtener el audio.").strip()
                self.terminado.emit(False, error, "")
                return

            lineas = [linea.strip() for linea in proceso.stdout.splitlines() if linea.strip()]
            url_audio = ""

            for linea in lineas:
                if linea.startswith("http://") or linea.startswith("https://"):
                    url_audio = linea
                    break

            if not url_audio:
                self.terminado.emit(False, "yt-dlp no devolvió una URL de audio válida.", "")
                return

            self.terminado.emit(True, "Preview listo.", url_audio)

        except subprocess.TimeoutExpired:
            self.terminado.emit(False, "La preparación del preview tardó demasiado.", "")
        except Exception as e:
            self.terminado.emit(False, str(e), "")


class WorkerDescarga(QThread):
    progreso = pyqtSignal(int)
    terminado = pyqtSignal(bool, str, dict)

    def __init__(self, url, destino, calidad_mp3="192", nombre_archivo=None):
        super().__init__()
        self.url = url
        self.destino = destino
        self.calidad_mp3 = calidad_mp3
        self.nombre_archivo = nombre_archivo

    def run(self):
        def callback(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                descargado = d.get("downloaded_bytes", 0)

                if total:
                    porcentaje = int(descargado * 100 / total)
                    self.progreso.emit(porcentaje)

        resumen = {
            "tipo": "playlist" if es_playlist(self.url) else "video",
            "completados": 0,
            "omitidos": 0,
            "errores": [],
            "lineas_log": [],
            "archivos": [],
        }

        try:
            if es_playlist(self.url):
                resumen = descargar_playlist_mp3(
                    self.url,
                    self.destino,
                    progreso_callback=callback,
                    calidad=self.calidad_mp3,
                    nombre_archivo=None,
                )
            else:
                resumen = descargar_mp3(
                    self.url,
                    self.destino,
                    progreso_callback=callback,
                    calidad=self.calidad_mp3,
                    nombre_archivo=self.nombre_archivo,
                )

            completados = resumen.get("completados", 0)
            omitidos = resumen.get("omitidos", 0)

            if resumen.get("tipo") == "playlist":
                mensaje = f"Playlist finalizada. Completados: {completados}. Omitidos: {omitidos}."
            else:
                mensaje = "Descarga completa."

            self.terminado.emit(True, mensaje, resumen)

        except Exception as e:
            resumen["errores"].append(str(e))
            self.terminado.emit(False, str(e), resumen)


class WorkerPrepararHerramientas(QThread):
    terminado = pyqtSignal(bool, str)

    def run(self):
        try:
            estado = preparar_herramientas_necesarias()

            mensaje = (
                "Herramientas preparadas correctamente.\n\n"
                f"yt-dlp: {estado['yt_dlp_version']}\n"
                f"FFmpeg: {estado['ffmpeg_version']}\n"
                f"FFprobe: {estado['ffprobe_version']}"
            )

            self.terminado.emit(True, mensaje)

        except Exception as e:
            self.terminado.emit(False, str(e))


class WorkerActualizarHerramientas(QThread):
    terminado = pyqtSignal(bool, str)

    def run(self):
        try:
            estado = actualizar_todas_las_herramientas()

            mensaje = (
                "Herramientas actualizadas correctamente.\n\n"
                f"yt-dlp: {estado['yt_dlp_version']}\n"
                f"FFmpeg: {estado['ffmpeg_version']}\n"
                f"FFprobe: {estado['ffprobe_version']}"
            )

            self.terminado.emit(True, mensaje)

        except Exception as e:
            self.terminado.emit(False, str(e))


class App(QWidget):
    ESTADO_PENDIENTE = "Pendiente"
    ESTADO_DESCARGANDO = "Descargando"
    ESTADO_COMPLETADO = "Completado"
    ESTADO_ERROR = "Error"

    CALIDADES_VALIDAS = ["128", "192", "256", "320"]

    COL_RUTA = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)

        ruta_icono = obtener_ruta_recurso("assets/audiodrop_icon.ico")
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))

        self.resize(1160, 720)
        self.setMinimumSize(940, 580)

        self.config = cargar_config()
        self.tema_actual = self.config.get("tema", "oscuro")

        carpeta_config = self.config.get("carpeta_destino", "").strip()

        if carpeta_config and os.path.exists(carpeta_config):
            self.ruta_destino = carpeta_config
        else:
            self.ruta_destino = obtener_ruta_musica()
            self.config["carpeta_destino"] = self.ruta_destino

        self.calidad_mp3 = str(self.config.get("calidad_mp3", "192"))

        if self.calidad_mp3 not in self.CALIDADES_VALIDAS:
            self.calidad_mp3 = "192"
            self.config["calidad_mp3"] = self.calidad_mp3

        self.lista_descarga_items = []
        self.thread = None
        self.thread_tools = None
        self.thread_preview = None
        self.resultados = []
        self.descargando_lista = False
        self.indice_descarga_actual = None
        self.resultado_actual = None
        self.log_items = []

        self.biblioteca_base = []
        self.biblioteca_visible = []
        self.playlists = cargar_playlists()
        self.playlist_actual_nombre = ""

        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.65)

        self.reproductor_ruta_actual = ""
        self.reproductor_indice_actual = -1
        self.reproductor_cola_actual = []
        self.reproductor_modo = "biblioteca"
        self.reproductor_arrastrando_slider = False
        self.preview_video_url_actual = ""
        self.preview_audio_url_actual = ""

        self.init_ui()
        self.configurar_reproductor()
        self.aplicar_config_inicial()
        self.guardar_config_actual()
        self.verificar_herramientas_inicio()

    # ============================================================
    # UI GENERAL
    # ============================================================

    def init_ui(self):
        self.setStyleSheet(obtener_estilo(self.tema_actual))

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(10, 8, 10, 8)
        layout_principal.setSpacing(7)

        header = QFrame()
        header.setObjectName("HeaderFrame")
        header.setMaximumHeight(76)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(10)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("LogoBox")
        self.logo_label.setFixedSize(48, 48)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cargar_logo_en_header()
        header_layout.addWidget(self.logo_label)

        header_textos = QVBoxLayout()
        header_textos.setContentsMargins(0, 0, 0, 0)
        header_textos.setSpacing(1)

        self.label_titulo = QLabel(APP_NAME)
        self.label_titulo.setObjectName("TitleLabel")
        header_textos.addWidget(self.label_titulo)

        self.label_subtitulo = QLabel(APP_SUBTITLE)
        self.label_subtitulo.setObjectName("SubtitleLabel")
        header_textos.addWidget(self.label_subtitulo)

        header_layout.addLayout(header_textos, 1)

        self.label_header_estado = QLabel("Centro Musical")
        self.label_header_estado.setObjectName("MutedLabel")
        self.label_header_estado.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        header_layout.addWidget(self.label_header_estado)

        layout_principal.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.tab_cambiada)
        layout_principal.addWidget(self.tabs, 1)

        self.crear_tab_busqueda()
        self.crear_tab_descargas()
        self.crear_tab_biblioteca()
        self.crear_tab_listas()
        self.crear_tab_visualizador()
        self.crear_tab_log()
        self.crear_tab_configuracion()

        self.crear_panel_reproductor(layout_principal)

        self.cargar_biblioteca()
        self.cargar_listas_en_ui()

    def cargar_logo_en_header(self):
        rutas_posibles = [
            obtener_ruta_recurso("assets/audiodrop_icon.png"),
            obtener_ruta_recurso("assets/audiodrop_icon.ico"),
        ]

        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                pixmap = QPixmap(ruta)

                if not pixmap.isNull():
                    pixmap = pixmap.scaled(
                        36,
                        36,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.logo_label.setPixmap(pixmap)
                    return

        self.logo_label.setText("♪")

    def aplicar_config_inicial(self):
        self.label_carpeta.setText(f"Carpeta destino: {self.ruta_destino}")
        self.label_config_carpeta.setText(f"Actual: {self.ruta_destino}")

        index_calidad = self.combo_calidad.findData(self.calidad_mp3)

        if index_calidad >= 0:
            self.combo_calidad.setCurrentIndex(index_calidad)

        index_tema = self.combo_tema.findData(self.tema_actual)

        if index_tema >= 0:
            self.combo_tema.setCurrentIndex(index_tema)

        ultima_pestana = int(self.config.get("ultima_pestana", 0))

        if 0 <= ultima_pestana < self.tabs.count():
            self.tabs.setCurrentIndex(ultima_pestana)

        self.slider_volumen.setValue(65)

    def guardar_config_actual(self):
        self.config["carpeta_destino"] = self.ruta_destino
        self.config["calidad_mp3"] = self.calidad_mp3
        self.config["ultima_pestana"] = self.tabs.currentIndex()
        self.config["tema"] = self.tema_actual

        try:
            guardar_config(self.config)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Configuración",
                f"No se pudo guardar la configuración:\n\n{e}",
            )

    def texto_corto(self, texto, maximo=72):
        texto = str(texto or "").strip()
        if len(texto) <= maximo:
            return texto
        return texto[: maximo - 3].rstrip() + "..."

    # ============================================================
    # TABS
    # ============================================================

    def crear_tab_busqueda(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        label = QLabel("Buscar canción o pegar URL de video:")
        layout.addWidget(label)

        fila_busqueda = QHBoxLayout()
        fila_busqueda.setSpacing(7)

        self.input_busqueda = AudioDropLineEdit()
        self.input_busqueda.setPlaceholderText(
            "Ejemplo: Linkin Park Numb o https://youtube.com/..."
        )
        self.input_busqueda.returnPressed.connect(self.buscar_o_previsualizar)
        fila_busqueda.addWidget(self.input_busqueda, 1)

        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.setObjectName("PrimaryButton")
        self.btn_buscar.clicked.connect(self.buscar_o_previsualizar)
        fila_busqueda.addWidget(self.btn_buscar)

        layout.addLayout(fila_busqueda)

        fila_contenido = QHBoxLayout()
        fila_contenido.setSpacing(10)

        columna_resultados = QVBoxLayout()
        columna_resultados.setSpacing(5)

        self.label_resultados = QLabel("Resultados:")
        columna_resultados.addWidget(self.label_resultados)

        self.lista_resultados = QListWidget()
        self.lista_resultados.currentRowChanged.connect(self.resultado_seleccionado)
        columna_resultados.addWidget(self.lista_resultados, 1)

        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(7)

        self.btn_descargar = QPushButton("Descargar seleccionado")
        self.btn_descargar.setObjectName("SuccessButton")
        self.btn_descargar.clicked.connect(self.iniciar_descarga)
        fila_botones.addWidget(self.btn_descargar)

        self.btn_agregar = QPushButton("Agregar a descargas")
        self.btn_agregar.setObjectName("SecondaryButton")
        self.btn_agregar.clicked.connect(self.agregar_a_lista)
        fila_botones.addWidget(self.btn_agregar)

        columna_resultados.addLayout(fila_botones)

        preview_panel = QFrame()
        preview_panel.setObjectName("PanelFrame")
        preview_panel.setMinimumWidth(330)
        preview_panel.setMaximumWidth(365)

        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(12, 10, 12, 12)
        preview_layout.setSpacing(7)

        preview_title = QLabel("Vista previa")
        preview_title.setObjectName("SectionTitle")
        preview_layout.addWidget(preview_title)

        # Miniatura chica y aislada. El texto va SIEMPRE debajo, nunca encima.
        preview_image_frame = QFrame()
        preview_image_frame.setObjectName("PanelFrame")
        preview_image_frame.setMinimumHeight(142)
        preview_image_frame.setMaximumHeight(142)

        preview_image_layout = QHBoxLayout(preview_image_frame)
        preview_image_layout.setContentsMargins(8, 8, 8, 8)
        preview_image_layout.setSpacing(0)
        preview_image_layout.addStretch(1)

        self.preview_imagen = QLabel()
        self.preview_imagen.setObjectName("PreviewBox")
        self.preview_imagen.setFixedSize(220, 124)
        self.preview_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_imagen.setText("Sin video")
        preview_image_layout.addWidget(self.preview_imagen)

        preview_image_layout.addStretch(1)
        preview_layout.addWidget(preview_image_frame)

        # Datos del video en un bloque compacto y sólido, separado de la imagen.
        preview_info_frame = QFrame()
        preview_info_frame.setObjectName("PanelFrame")
        preview_info_layout = QVBoxLayout(preview_info_frame)
        preview_info_layout.setContentsMargins(9, 7, 9, 7)
        preview_info_layout.setSpacing(3)

        label_titulo_preview = QLabel("Título")
        label_titulo_preview.setObjectName("MutedLabel")
        preview_info_layout.addWidget(label_titulo_preview)

        self.preview_titulo = QLabel("-")
        self.preview_titulo.setObjectName("PreviewTitle")
        self.preview_titulo.setWordWrap(True)
        self.preview_titulo.setMaximumHeight(34)
        preview_info_layout.addWidget(self.preview_titulo)

        self.preview_canal = QLabel("Canal: -")
        self.preview_canal.setObjectName("MutedLabel")
        self.preview_canal.setWordWrap(False)
        self.preview_canal.setMaximumHeight(22)
        preview_info_layout.addWidget(self.preview_canal)

        self.preview_duracion = QLabel("Duración: -")
        self.preview_duracion.setObjectName("MutedLabel")
        preview_info_layout.addWidget(self.preview_duracion)

        preview_layout.addWidget(preview_info_frame)

        self.btn_preview_audio = QPushButton("▶ Previsualizar")
        self.btn_preview_audio.setObjectName("SecondaryButton")
        self.btn_preview_audio.setMaximumHeight(30)
        self.btn_preview_audio.setEnabled(False)
        self.btn_preview_audio.clicked.connect(self.toggle_preview_resultado)
        preview_layout.addWidget(self.btn_preview_audio)

        # Sacamos el botón de abrir video para ganar aire y evitar que la columna quede cargada.
        self.btn_abrir_video = QPushButton("Abrir video")
        self.btn_abrir_video.setObjectName("SecondaryButton")
        self.btn_abrir_video.setMaximumHeight(26)
        self.btn_abrir_video.clicked.connect(self.abrir_video_actual)
        self.btn_abrir_video.hide()

        label_nombre = QLabel("Nombre personalizado:")
        label_nombre.setObjectName("MutedLabel")
        preview_layout.addWidget(label_nombre)

        self.input_nombre_archivo = AudioDropLineEdit()
        self.input_nombre_archivo.setPlaceholderText("Opcional")
        self.input_nombre_archivo.setMaximumHeight(34)
        preview_layout.addWidget(self.input_nombre_archivo)

        preview_layout.addStretch(1)

        fila_contenido.addLayout(columna_resultados, 1)
        fila_contenido.addWidget(preview_panel)

        layout.addLayout(fila_contenido, 1)

        self.tabs.addTab(tab, "Buscar")

    def crear_tab_descargas(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        fila_playlist = QHBoxLayout()
        fila_playlist.setSpacing(7)

        label_playlist = QLabel("Playlist:")
        fila_playlist.addWidget(label_playlist)

        self.input_playlist = AudioDropLineEdit()
        self.input_playlist.setPlaceholderText("Pegá acá una URL de playlist de YouTube")
        self.input_playlist.returnPressed.connect(self.agregar_playlist_a_lista)
        fila_playlist.addWidget(self.input_playlist, 1)

        self.btn_agregar_playlist = QPushButton("Agregar")
        self.btn_agregar_playlist.setObjectName("SecondaryButton")
        self.btn_agregar_playlist.clicked.connect(self.agregar_playlist_a_lista)
        fila_playlist.addWidget(self.btn_agregar_playlist)

        layout.addLayout(fila_playlist)

        self.label_lista = QLabel("Descargas:")
        layout.addWidget(self.label_lista)

        self.lista_descarga = QListWidget()
        layout.addWidget(self.lista_descarga, 1)

        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(7)

        self.btn_descargar_lista = QPushButton("Descargar pendientes")
        self.btn_descargar_lista.setObjectName("SuccessButton")
        self.btn_descargar_lista.clicked.connect(self.iniciar_descarga_lista)
        fila_botones.addWidget(self.btn_descargar_lista)

        self.btn_eliminar = QPushButton("Quitar")
        self.btn_eliminar.setObjectName("DangerButton")
        self.btn_eliminar.clicked.connect(self.eliminar_de_lista)
        fila_botones.addWidget(self.btn_eliminar)

        self.btn_limpiar_lista = QPushButton("Limpiar")
        self.btn_limpiar_lista.setObjectName("SecondaryButton")
        self.btn_limpiar_lista.clicked.connect(self.limpiar_lista)
        fila_botones.addWidget(self.btn_limpiar_lista)

        self.btn_reintentar_errores = QPushButton("Reintentar errores")
        self.btn_reintentar_errores.setObjectName("SecondaryButton")
        self.btn_reintentar_errores.clicked.connect(self.reintentar_errores)
        fila_botones.addWidget(self.btn_reintentar_errores)

        layout.addLayout(fila_botones)

        self.tabs.addTab(tab, "Descargas")

    def crear_tab_biblioteca(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(7)

        titulo = QLabel("Biblioteca musical")
        titulo.setObjectName("SectionTitle")
        fila_superior.addWidget(titulo)

        fila_superior.addStretch(1)

        label_buscar = QLabel("Buscar:")
        fila_superior.addWidget(label_buscar)

        self.input_buscar_biblioteca = AudioDropLineEdit()
        self.input_buscar_biblioteca.setPlaceholderText("Filtrar canciones...")
        self.input_buscar_biblioteca.textChanged.connect(self.aplicar_filtros_biblioteca)
        fila_superior.addWidget(self.input_buscar_biblioteca, 1)

        label_orden = QLabel("Orden:")
        fila_superior.addWidget(label_orden)

        self.combo_orden_biblioteca = QComboBox()
        self.combo_orden_biblioteca.addItem("Nombre", "nombre")
        self.combo_orden_biblioteca.addItem("Fecha", "fecha")
        self.combo_orden_biblioteca.addItem("Tamaño", "tamano")
        self.combo_orden_biblioteca.currentIndexChanged.connect(self.aplicar_filtros_biblioteca)
        fila_superior.addWidget(self.combo_orden_biblioteca)

        self.btn_actualizar_biblioteca = QPushButton("Actualizar")
        self.btn_actualizar_biblioteca.setObjectName("SecondaryButton")
        self.btn_actualizar_biblioteca.clicked.connect(self.cargar_biblioteca)
        fila_superior.addWidget(self.btn_actualizar_biblioteca)

        layout.addLayout(fila_superior)

        self.label_carpeta = QLabel(f"Carpeta destino: {self.ruta_destino}")
        self.label_carpeta.setObjectName("MutedLabel")
        self.label_carpeta.setWordWrap(True)
        layout.addWidget(self.label_carpeta)

        self.label_biblioteca_resumen = QLabel("Canciones encontradas: 0.")
        self.label_biblioteca_resumen.setObjectName("MutedLabel")
        layout.addWidget(self.label_biblioteca_resumen)

        self.tabla_biblioteca = QTableWidget()
        self.configurar_tabla_musica(self.tabla_biblioteca)
        self.tabla_biblioteca.itemDoubleClicked.connect(self.reproducir_item_tabla_biblioteca)

        self.tabla_biblioteca.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_biblioteca.customContextMenuRequested.connect(self.menu_contextual_biblioteca)

        layout.addWidget(self.tabla_biblioteca, 1)

        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(7)

        self.btn_reproducir_biblioteca = QPushButton("Reproducir")
        self.btn_reproducir_biblioteca.setObjectName("PrimaryButton")
        self.btn_reproducir_biblioteca.clicked.connect(self.reproducir_seleccion_biblioteca)
        fila_acciones.addWidget(self.btn_reproducir_biblioteca)

        self.btn_agregar_a_lista = QPushButton("Agregar a lista")
        self.btn_agregar_a_lista.setObjectName("SecondaryButton")
        self.btn_agregar_a_lista.clicked.connect(self.agregar_seleccion_a_lista)
        fila_acciones.addWidget(self.btn_agregar_a_lista)

        self.btn_elegir_carpeta = QPushButton("Elegir carpeta")
        self.btn_elegir_carpeta.setObjectName("SecondaryButton")
        self.btn_elegir_carpeta.clicked.connect(self.elegir_carpeta)
        fila_acciones.addWidget(self.btn_elegir_carpeta)

        self.btn_abrir_carpeta = QPushButton("Abrir carpeta")
        self.btn_abrir_carpeta.setObjectName("SecondaryButton")
        self.btn_abrir_carpeta.clicked.connect(self.abrir_carpeta)
        fila_acciones.addWidget(self.btn_abrir_carpeta)

        self.btn_borrar_archivo = QPushButton("Borrar seleccionado")
        self.btn_borrar_archivo.setObjectName("DangerButton")
        self.btn_borrar_archivo.clicked.connect(self.borrar_archivo)
        fila_acciones.addWidget(self.btn_borrar_archivo)

        fila_acciones.addStretch(1)

        layout.addLayout(fila_acciones)

        self.tabs.addTab(tab, "Biblioteca")

    def crear_tab_listas(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(9)

        columna_listas = QVBoxLayout()
        columna_listas.setSpacing(6)

        titulo_listas = QLabel("Listas propias")
        titulo_listas.setObjectName("SectionTitle")
        columna_listas.addWidget(titulo_listas)

        self.lista_playlists = QListWidget()
        self.lista_playlists.currentItemChanged.connect(self.playlist_seleccionada)

        self.lista_playlists.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lista_playlists.customContextMenuRequested.connect(self.menu_contextual_lista_playlists)

        columna_listas.addWidget(self.lista_playlists, 1)

        fila_listas_botones = QHBoxLayout()
        fila_listas_botones.setSpacing(7)

        self.btn_crear_playlist = QPushButton("Crear")
        self.btn_crear_playlist.setObjectName("PrimaryButton")
        self.btn_crear_playlist.clicked.connect(self.crear_lista_propia)
        fila_listas_botones.addWidget(self.btn_crear_playlist)

        self.btn_borrar_playlist = QPushButton("Borrar")
        self.btn_borrar_playlist.setObjectName("DangerButton")
        self.btn_borrar_playlist.clicked.connect(self.borrar_lista_propia)
        fila_listas_botones.addWidget(self.btn_borrar_playlist)

        columna_listas.addLayout(fila_listas_botones)

        layout.addLayout(columna_listas, 1)

        columna_canciones = QVBoxLayout()
        columna_canciones.setSpacing(6)

        fila_titulo = QHBoxLayout()
        fila_titulo.setSpacing(7)

        self.label_playlist_actual = QLabel("Seleccioná una lista")
        self.label_playlist_actual.setObjectName("SectionTitle")
        fila_titulo.addWidget(self.label_playlist_actual)

        fila_titulo.addStretch(1)

        self.btn_abrir_playlists_json = QPushButton("Abrir JSON")
        self.btn_abrir_playlists_json.setObjectName("SecondaryButton")
        self.btn_abrir_playlists_json.clicked.connect(self.abrir_archivo_playlists)
        fila_titulo.addWidget(self.btn_abrir_playlists_json)

        columna_canciones.addLayout(fila_titulo)

        self.tabla_playlist = QTableWidget()
        self.configurar_tabla_musica(self.tabla_playlist)
        self.tabla_playlist.itemDoubleClicked.connect(self.reproducir_item_tabla_playlist)

        self.tabla_playlist.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla_playlist.customContextMenuRequested.connect(self.menu_contextual_tabla_playlist)

        columna_canciones.addWidget(self.tabla_playlist, 1)

        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(7)

        self.btn_reproducir_playlist = QPushButton("Reproducir lista")
        self.btn_reproducir_playlist.setObjectName("PrimaryButton")
        self.btn_reproducir_playlist.clicked.connect(self.reproducir_lista_actual)
        fila_acciones.addWidget(self.btn_reproducir_playlist)

        self.btn_quitar_de_playlist = QPushButton("Quitar seleccionado")
        self.btn_quitar_de_playlist.setObjectName("DangerButton")
        self.btn_quitar_de_playlist.clicked.connect(self.quitar_seleccion_de_lista)
        fila_acciones.addWidget(self.btn_quitar_de_playlist)

        fila_acciones.addStretch(1)

        columna_canciones.addLayout(fila_acciones)

        layout.addLayout(columna_canciones, 3)

        self.tabs.addTab(tab, "Listas")

    def crear_tab_visualizador(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        fila = QHBoxLayout()
        fila.setSpacing(8)

        titulo = QLabel("Visualizador")
        titulo.setObjectName("SectionTitle")
        fila.addWidget(titulo)

        fila.addStretch(1)

        label_estilo = QLabel("Estilo:")
        fila.addWidget(label_estilo)

        self.combo_visualizador = QComboBox()
        self.combo_visualizador.addItem("Barras suaves")
        self.combo_visualizador.addItem("Ondas suaves")
        self.combo_visualizador.addItem("Círculo pulsante")
        self.combo_visualizador.addItem("Nebulosa")
        self.combo_visualizador.currentTextChanged.connect(self.visualizador_estilo_cambiado)
        fila.addWidget(self.combo_visualizador)

        label_intensidad = QLabel("Intensidad")
        fila.addWidget(label_intensidad)

        self.slider_visualizador_intensidad = QSlider(Qt.Orientation.Horizontal)
        self.slider_visualizador_intensidad.setRange(10, 100)
        self.slider_visualizador_intensidad.setValue(70)
        self.slider_visualizador_intensidad.setFixedWidth(120)
        self.slider_visualizador_intensidad.valueChanged.connect(self.visualizador_intensidad_cambiada)
        fila.addWidget(self.slider_visualizador_intensidad)

        label_velocidad = QLabel("Velocidad")
        fila.addWidget(label_velocidad)

        self.slider_visualizador_velocidad = QSlider(Qt.Orientation.Horizontal)
        self.slider_visualizador_velocidad.setRange(10, 100)
        self.slider_visualizador_velocidad.setValue(60)
        self.slider_visualizador_velocidad.setFixedWidth(120)
        self.slider_visualizador_velocidad.valueChanged.connect(self.visualizador_velocidad_cambiada)
        fila.addWidget(self.slider_visualizador_velocidad)

        layout.addLayout(fila)

        self.visualizador_widget = VisualizadorWidget(self)
        self.visualizador_widget.set_reproductor(self.media_player, self.audio_output)
        self.visualizador_widget.set_tema(self.tema_actual)
        layout.addWidget(self.visualizador_widget, 1)

        ayuda = QLabel("Visualización estética opcional. No afecta descargas ni reproducción.")
        ayuda.setObjectName("MutedLabel")
        layout.addWidget(ayuda)

        self.tabs.addTab(tab, "Visualizador")

    def crear_tab_log(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        label = QLabel("Historial de actividad:")
        layout.addWidget(label)

        self.lista_log = QListWidget()
        layout.addWidget(self.lista_log, 1)

        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(7)

        self.btn_limpiar_log = QPushButton("Limpiar historial")
        self.btn_limpiar_log.setObjectName("SecondaryButton")
        self.btn_limpiar_log.clicked.connect(self.limpiar_log)
        fila_botones.addWidget(self.btn_limpiar_log)

        self.btn_copiar_log = QPushButton("Copiar historial")
        self.btn_copiar_log.setObjectName("SecondaryButton")
        self.btn_copiar_log.clicked.connect(self.copiar_log)
        fila_botones.addWidget(self.btn_copiar_log)

        layout.addLayout(fila_botones)

        self.tabs.addTab(tab, "Historial")

    def crear_tab_configuracion(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(7)

        titulo_tema = QLabel("Apariencia")
        titulo_tema.setObjectName("SectionTitle")
        layout.addWidget(titulo_tema)

        fila_tema = QHBoxLayout()
        fila_tema.setSpacing(7)

        label_tema = QLabel("Tema visual:")
        fila_tema.addWidget(label_tema)

        self.combo_tema = QComboBox()
        self.combo_tema.addItem("Oscuro moderno", "oscuro")
        self.combo_tema.addItem("Claro azul", "claro")
        self.combo_tema.currentIndexChanged.connect(self.tema_cambiado)
        fila_tema.addWidget(self.combo_tema, 1)

        layout.addLayout(fila_tema)

        titulo_calidad = QLabel("Calidad de audio")
        titulo_calidad.setObjectName("SectionTitle")
        layout.addWidget(titulo_calidad)

        descripcion_calidad = QLabel(
            "Elegí la calidad de conversión MP3. Más calidad ocupa más espacio."
        )
        descripcion_calidad.setObjectName("MutedLabel")
        layout.addWidget(descripcion_calidad)

        fila_calidad = QHBoxLayout()
        fila_calidad.setSpacing(7)

        label_calidad = QLabel("Calidad MP3:")
        fila_calidad.addWidget(label_calidad)

        self.combo_calidad = QComboBox()
        self.combo_calidad.addItem("128 kbps - Liviano", "128")
        self.combo_calidad.addItem("192 kbps - Recomendado", "192")
        self.combo_calidad.addItem("256 kbps - Alta", "256")
        self.combo_calidad.addItem("320 kbps - Máxima", "320")
        self.combo_calidad.currentIndexChanged.connect(self.calidad_cambiada)
        fila_calidad.addWidget(self.combo_calidad, 1)

        layout.addLayout(fila_calidad)

        titulo_carpeta = QLabel("Carpeta de descarga / biblioteca")
        titulo_carpeta.setObjectName("SectionTitle")
        layout.addWidget(titulo_carpeta)

        self.label_config_carpeta = QLabel(f"Actual: {self.ruta_destino}")
        self.label_config_carpeta.setObjectName("MutedLabel")
        self.label_config_carpeta.setWordWrap(True)
        layout.addWidget(self.label_config_carpeta)

        self.btn_config_elegir_carpeta = QPushButton("Cambiar carpeta destino")
        self.btn_config_elegir_carpeta.setObjectName("SecondaryButton")
        self.btn_config_elegir_carpeta.clicked.connect(self.elegir_carpeta)
        layout.addWidget(self.btn_config_elegir_carpeta)

        titulo_listas = QLabel("Listas propias")
        titulo_listas.setObjectName("SectionTitle")
        layout.addWidget(titulo_listas)

        self.label_config_playlists = QLabel(f"Archivo: {obtener_ruta_playlists()}")
        self.label_config_playlists.setObjectName("MutedLabel")
        self.label_config_playlists.setWordWrap(True)
        layout.addWidget(self.label_config_playlists)

        titulo_herramientas = QLabel("Herramientas internas")
        titulo_herramientas.setObjectName("SectionTitle")
        layout.addWidget(titulo_herramientas)

        self.label_tools_estado = QLabel("Estado: pendiente")
        self.label_tools_estado.setObjectName("MutedLabel")
        self.label_tools_estado.setWordWrap(True)
        layout.addWidget(self.label_tools_estado)

        self.btn_preparar_tools = QPushButton("Preparar herramientas faltantes")
        self.btn_preparar_tools.setObjectName("PrimaryButton")
        self.btn_preparar_tools.clicked.connect(self.preparar_herramientas_desde_ui)
        layout.addWidget(self.btn_preparar_tools)

        self.btn_actualizar_tools = QPushButton("Actualizar yt-dlp + FFmpeg")
        self.btn_actualizar_tools.setObjectName("SecondaryButton")
        self.btn_actualizar_tools.clicked.connect(self.actualizar_herramientas_desde_ui)
        layout.addWidget(self.btn_actualizar_tools)

        self.btn_refrescar_tools = QPushButton("Revisar herramientas")
        self.btn_refrescar_tools.setObjectName("SecondaryButton")
        self.btn_refrescar_tools.clicked.connect(self.actualizar_estado_herramientas)
        layout.addWidget(self.btn_refrescar_tools)

        self.btn_guardar_config = QPushButton("Guardar configuración ahora")
        self.btn_guardar_config.setObjectName("SecondaryButton")
        self.btn_guardar_config.clicked.connect(self.guardar_config_manual)
        layout.addWidget(self.btn_guardar_config)

        layout.addStretch(1)

        scroll.setWidget(contenido)
        tab_layout.addWidget(scroll)

        self.tabs.addTab(tab, "Configuración")

    def crear_panel_reproductor(self, layout_principal):
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setValue(0)
        self.barra_progreso.setMaximumHeight(9)
        layout_principal.addWidget(self.barra_progreso)

        player_bar = QFrame()
        player_bar.setObjectName("PlayerBar")
        player_bar.setMaximumHeight(94)

        player_layout = QVBoxLayout(player_bar)
        player_layout.setContentsMargins(9, 6, 9, 6)
        player_layout.setSpacing(5)

        fila_info = QHBoxLayout()
        fila_info.setSpacing(8)

        info_pill = QFrame()
        info_pill.setObjectName("PlayerInfoPill")
        info_layout = QHBoxLayout(info_pill)
        info_layout.setContentsMargins(8, 5, 8, 5)
        info_layout.setSpacing(8)

        self.label_player_icon = QLabel("♪")
        self.label_player_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_player_icon.setFixedSize(26, 26)
        info_layout.addWidget(self.label_player_icon)

        columna_tema = QVBoxLayout()
        columna_tema.setSpacing(0)

        self.label_player_titulo = QLabel("Nada reproduciendo")
        self.label_player_titulo.setObjectName("PlayerTitle")
        columna_tema.addWidget(self.label_player_titulo)

        self.label_player_sub = QLabel("Biblioteca musical")
        self.label_player_sub.setObjectName("PlayerSub")
        columna_tema.addWidget(self.label_player_sub)

        info_layout.addLayout(columna_tema, 1)

        fila_info.addWidget(info_pill, 1)

        self.label_estado = QLabel("Listo")
        self.label_estado.setObjectName("StatusLabel")
        self.label_estado.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        fila_info.addWidget(self.label_estado)

        self.btn_salir = QPushButton("Salir")
        self.btn_salir.setObjectName("SecondaryButton")
        self.btn_salir.clicked.connect(self.close)
        fila_info.addWidget(self.btn_salir)

        player_layout.addLayout(fila_info)

        fila_control = QHBoxLayout()
        fila_control.setSpacing(7)

        self.btn_player_anterior = QPushButton("‹‹")
        self.btn_player_anterior.setObjectName("PlayerButton")
        self.btn_player_anterior.clicked.connect(self.reproductor_anterior)
        fila_control.addWidget(self.btn_player_anterior)

        self.btn_player_play = QPushButton("▶")
        self.btn_player_play.setObjectName("PlayMainButton")
        self.btn_player_play.clicked.connect(self.reproductor_toggle_play)
        fila_control.addWidget(self.btn_player_play)

        self.btn_player_stop = QPushButton("■")
        self.btn_player_stop.setObjectName("PlayerButton")
        self.btn_player_stop.clicked.connect(self.reproductor_stop)
        fila_control.addWidget(self.btn_player_stop)

        self.btn_player_siguiente = QPushButton("››")
        self.btn_player_siguiente.setObjectName("PlayerButton")
        self.btn_player_siguiente.clicked.connect(self.reproductor_siguiente)
        fila_control.addWidget(self.btn_player_siguiente)

        self.btn_player_random = QPushButton("⤨")
        self.btn_player_random.setObjectName("PlayerButton")
        self.btn_player_random.setCheckable(True)
        self.btn_player_random.setToolTip("Aleatorio")
        fila_control.addWidget(self.btn_player_random)

        self.btn_player_repeat = QPushButton("↻")
        self.btn_player_repeat.setObjectName("PlayerButton")
        self.btn_player_repeat.setCheckable(True)
        self.btn_player_repeat.setToolTip("Repetir")
        fila_control.addWidget(self.btn_player_repeat)

        self.slider_reproduccion = QSlider(Qt.Orientation.Horizontal)
        self.slider_reproduccion.setRange(0, 0)
        self.slider_reproduccion.sliderPressed.connect(self.reproductor_slider_presionado)
        self.slider_reproduccion.sliderReleased.connect(self.reproductor_slider_soltado)
        fila_control.addWidget(self.slider_reproduccion, 1)

        self.label_tiempo = QLabel("00:00 / 00:00")
        self.label_tiempo.setObjectName("PlayerTimeLabel")
        fila_control.addWidget(self.label_tiempo)

        label_vol = QLabel("Vol")
        label_vol.setObjectName("MutedLabel")
        fila_control.addWidget(label_vol)

        self.slider_volumen = QSlider(Qt.Orientation.Horizontal)
        self.slider_volumen.setRange(0, 100)
        self.slider_volumen.setValue(65)
        self.slider_volumen.setFixedWidth(100)
        self.slider_volumen.valueChanged.connect(self.reproductor_cambiar_volumen)
        fila_control.addWidget(self.slider_volumen)

        player_layout.addLayout(fila_control)

        layout_principal.addWidget(player_bar)

    # ============================================================
    # VISUALIZADOR
    # ============================================================

    def visualizador_estilo_cambiado(self, texto):
        if hasattr(self, "visualizador_widget"):
            self.visualizador_widget.set_modo(texto)

    def visualizador_intensidad_cambiada(self, valor):
        if hasattr(self, "visualizador_widget"):
            self.visualizador_widget.set_intensidad(valor)

    def visualizador_velocidad_cambiada(self, valor):
        if hasattr(self, "visualizador_widget"):
            self.visualizador_widget.set_velocidad(valor)

    # ============================================================
    # MENÚS CONTEXTUALES
    # ============================================================

    def menu_contextual_biblioteca(self, posicion):
        fila = self.tabla_biblioteca.rowAt(posicion.y())

        if fila >= 0:
            self.tabla_biblioteca.setCurrentCell(fila, 1)
            ruta = self.obtener_ruta_fila_tabla(self.tabla_biblioteca, fila)
        else:
            ruta = ""

        menu = QMenu(self)

        if ruta:
            accion_reproducir = QAction("▶ Reproducir", self)
            accion_reproducir.triggered.connect(self.reproducir_seleccion_biblioteca)
            menu.addAction(accion_reproducir)

            submenu_listas = menu.addMenu("➕ Agregar a lista")

            if self.playlists:
                for nombre_lista in sorted(self.playlists.keys(), key=lambda x: x.lower()):
                    accion_lista = QAction(nombre_lista, self)
                    accion_lista.triggered.connect(
                        lambda checked=False, n=nombre_lista, r=ruta: self.agregar_ruta_a_lista(n, r)
                    )
                    submenu_listas.addAction(accion_lista)
            else:
                accion_sin_listas = QAction("No hay listas creadas", self)
                accion_sin_listas.setEnabled(False)
                submenu_listas.addAction(accion_sin_listas)

            submenu_listas.addSeparator()

            accion_crear_y_agregar = QAction("Crear nueva lista...", self)
            accion_crear_y_agregar.triggered.connect(
                lambda checked=False, r=ruta: self.crear_lista_y_agregar_ruta(r)
            )
            submenu_listas.addAction(accion_crear_y_agregar)

            menu.addSeparator()

            accion_abrir_ubicacion = QAction("📂 Abrir ubicación del archivo", self)
            accion_abrir_ubicacion.triggered.connect(
                lambda checked=False, r=ruta: self.abrir_ubicacion_archivo(r)
            )
            menu.addAction(accion_abrir_ubicacion)

            accion_borrar = QAction("🗑 Borrar archivo", self)
            accion_borrar.triggered.connect(self.borrar_archivo)
            menu.addAction(accion_borrar)

        else:
            accion_actualizar = QAction("🔄 Actualizar biblioteca", self)
            accion_actualizar.triggered.connect(self.cargar_biblioteca)
            menu.addAction(accion_actualizar)

            accion_elegir = QAction("📁 Elegir carpeta", self)
            accion_elegir.triggered.connect(self.elegir_carpeta)
            menu.addAction(accion_elegir)

            accion_abrir = QAction("📂 Abrir carpeta actual", self)
            accion_abrir.triggered.connect(self.abrir_carpeta)
            menu.addAction(accion_abrir)

        menu.exec(self.tabla_biblioteca.viewport().mapToGlobal(posicion))

    def menu_contextual_lista_playlists(self, posicion):
        item = self.lista_playlists.itemAt(posicion)

        if item:
            self.lista_playlists.setCurrentItem(item)
            self.playlist_actual_nombre = item.text()

        menu = QMenu(self)

        if item:
            accion_reproducir = QAction("▶ Reproducir lista", self)
            accion_reproducir.triggered.connect(self.reproducir_lista_actual)
            menu.addAction(accion_reproducir)

            menu.addSeparator()

        accion_crear = QAction("➕ Crear lista", self)
        accion_crear.triggered.connect(self.crear_lista_propia)
        menu.addAction(accion_crear)

        if item:
            accion_borrar = QAction("🗑 Borrar lista", self)
            accion_borrar.triggered.connect(self.borrar_lista_propia)
            menu.addAction(accion_borrar)

        menu.addSeparator()

        accion_abrir_json = QAction("📄 Abrir playlists.json", self)
        accion_abrir_json.triggered.connect(self.abrir_archivo_playlists)
        menu.addAction(accion_abrir_json)

        menu.exec(self.lista_playlists.viewport().mapToGlobal(posicion))

    def menu_contextual_tabla_playlist(self, posicion):
        fila = self.tabla_playlist.rowAt(posicion.y())

        if fila >= 0:
            self.tabla_playlist.setCurrentCell(fila, 1)
            ruta = self.obtener_ruta_fila_tabla(self.tabla_playlist, fila)
        else:
            ruta = ""

        menu = QMenu(self)

        if ruta:
            accion_reproducir = QAction("▶ Reproducir", self)
            accion_reproducir.triggered.connect(
                lambda checked=False, f=fila: self.reproducir_playlist_desde_fila(f)
            )
            menu.addAction(accion_reproducir)

            accion_quitar = QAction("➖ Quitar de esta lista", self)
            accion_quitar.triggered.connect(self.quitar_seleccion_de_lista)
            menu.addAction(accion_quitar)

            menu.addSeparator()

            accion_abrir_ubicacion = QAction("📂 Abrir ubicación del archivo", self)
            accion_abrir_ubicacion.triggered.connect(
                lambda checked=False, r=ruta: self.abrir_ubicacion_archivo(r)
            )
            menu.addAction(accion_abrir_ubicacion)

        else:
            accion_reproducir_lista = QAction("▶ Reproducir lista", self)
            accion_reproducir_lista.triggered.connect(self.reproducir_lista_actual)
            menu.addAction(accion_reproducir_lista)

            accion_crear = QAction("➕ Crear lista", self)
            accion_crear.triggered.connect(self.crear_lista_propia)
            menu.addAction(accion_crear)

            accion_abrir_json = QAction("📄 Abrir playlists.json", self)
            accion_abrir_json.triggered.connect(self.abrir_archivo_playlists)
            menu.addAction(accion_abrir_json)

        menu.exec(self.tabla_playlist.viewport().mapToGlobal(posicion))

    # ============================================================
    # TABLAS
    # ============================================================

    def configurar_tabla_musica(self, tabla):
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["", "Nombre", "Tamaño", "Fecha", "Ruta"])
        tabla.setAlternatingRowColors(True)
        tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)
        tabla.setSortingEnabled(False)

        header = tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        tabla.setColumnWidth(0, 34)
        tabla.setColumnWidth(2, 85)
        tabla.setColumnWidth(3, 130)

    def crear_item_tabla(self, texto, ruta=None):
        item = QTableWidgetItem(texto)

        if ruta:
            item.setData(self.COL_RUTA, ruta)

        return item

    def cargar_archivos_en_tabla(self, tabla, archivos):
        tabla.setRowCount(0)

        for archivo in archivos:
            fila = tabla.rowCount()
            tabla.insertRow(fila)

            ruta = archivo["ruta"]

            tabla.setItem(fila, 0, self.crear_item_tabla("♪", ruta))
            tabla.setItem(fila, 1, self.crear_item_tabla(archivo["nombre"], ruta))
            tabla.setItem(fila, 2, self.crear_item_tabla(archivo.get("tamano", "-"), ruta))
            tabla.setItem(fila, 3, self.crear_item_tabla(archivo.get("fecha", "-"), ruta))
            tabla.setItem(fila, 4, self.crear_item_tabla(ruta, ruta))

        tabla.resizeRowsToContents()

    def obtener_ruta_fila_tabla(self, tabla, fila=None):
        if fila is None:
            fila = tabla.currentRow()

        if fila < 0:
            return ""

        item = tabla.item(fila, 1)

        if not item:
            item = tabla.item(fila, 0)

        if not item:
            return ""

        ruta = item.data(self.COL_RUTA)

        return ruta or ""

    # ============================================================
    # REPRODUCTOR
    # ============================================================

    def configurar_reproductor(self):
        self.media_player.positionChanged.connect(self.reproductor_posicion_cambiada)
        self.media_player.durationChanged.connect(self.reproductor_duracion_cambiada)
        self.media_player.playbackStateChanged.connect(self.reproductor_estado_cambiado)
        self.media_player.mediaStatusChanged.connect(self.reproductor_media_status_cambiado)
        self.media_player.errorOccurred.connect(self.reproductor_error)

    def formato_tiempo(self, ms):
        segundos = int(ms / 1000)
        minutos = segundos // 60
        segundos = segundos % 60
        return f"{minutos:02d}:{segundos:02d}"

    def archivo_a_objeto_musica(self, ruta):
        ruta = str(ruta)

        nombre = os.path.basename(ruta)
        tamano = "-"
        fecha = "-"

        try:
            size = os.path.getsize(ruta)

            if size < 1024 * 1024:
                tamano = f"{size / 1024:.1f} KB"
            else:
                tamano = f"{size / (1024 * 1024):.1f} MB"

            fecha = datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass

        return {
            "nombre": nombre,
            "ruta": ruta,
            "tipo": "audio",
            "icono": "♪",
            "tamano": tamano,
            "fecha": fecha,
        }

    def reproductor_cargar_y_reproducir(self, ruta, cola=None, indice=-1, modo="biblioteca"):
        if hasattr(self, "btn_preview_audio"):
            self.btn_preview_audio.setText("▶ Previsualizar")
            self.btn_preview_audio.setEnabled(bool(self.resultado_actual))
        self.preview_audio_url_actual = ""

        if not ruta or not os.path.exists(ruta):
            QMessageBox.warning(self, "Reproductor", "No se encontró el archivo.")
            return

        if not ruta.lower().endswith(".mp3"):
            QMessageBox.information(
                self,
                "Reproductor",
                "Por ahora el reproductor interno está enfocado en música MP3.",
            )
            return

        if cola is not None:
            self.reproductor_cola_actual = cola

        self.reproductor_ruta_actual = ruta
        self.reproductor_indice_actual = indice
        self.reproductor_modo = modo

        nombre = os.path.basename(ruta)

        self.label_player_titulo.setText(nombre)

        if hasattr(self, "visualizador_widget"):
            self.visualizador_widget.set_titulo(nombre)

        if modo == "playlist" and self.playlist_actual_nombre:
            self.label_player_sub.setText(f"Lista: {self.playlist_actual_nombre}")
        else:
            self.label_player_sub.setText("Biblioteca musical")

        self.label_player_icon.setText("♪")
        self.agregar_log(f"Reproduciendo: {nombre}")

        self.media_player.setSource(QUrl.fromLocalFile(ruta))
        self.media_player.play()

    def reproductor_toggle_play(self):
        if not self.reproductor_ruta_actual:
            if self.tabs.currentIndex() == 3:
                self.reproducir_lista_actual()
            else:
                self.reproducir_seleccion_biblioteca()
            return

        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def reproductor_stop(self):
        if self.reproductor_modo == "preview":
            self.detener_preview()
            return

        self.media_player.stop()
        self.btn_player_play.setText("▶")
        self.slider_reproduccion.setValue(0)

    def reproductor_anterior(self):
        if not self.reproductor_cola_actual:
            return

        if self.reproductor_indice_actual <= 0:
            indice = len(self.reproductor_cola_actual) - 1
        else:
            indice = self.reproductor_indice_actual - 1

        self.reproductor_reproducir_indice(indice)

    def reproductor_siguiente(self):
        if not self.reproductor_cola_actual:
            return

        if self.btn_player_repeat.isChecked() and self.reproductor_indice_actual >= 0:
            indice = self.reproductor_indice_actual
        elif self.btn_player_random.isChecked() and len(self.reproductor_cola_actual) > 1:
            indice = random.randint(0, len(self.reproductor_cola_actual) - 1)

            if indice == self.reproductor_indice_actual:
                indice = (indice + 1) % len(self.reproductor_cola_actual)
        else:
            indice = self.reproductor_indice_actual + 1

            if indice >= len(self.reproductor_cola_actual):
                indice = 0

        self.reproductor_reproducir_indice(indice)

    def reproductor_reproducir_indice(self, indice):
        if indice < 0 or indice >= len(self.reproductor_cola_actual):
            return

        archivo = self.reproductor_cola_actual[indice]
        ruta = archivo["ruta"]

        if self.reproductor_modo == "playlist":
            self.tabla_playlist.setCurrentCell(indice, 1)
        else:
            self.tabla_biblioteca.setCurrentCell(indice, 1)

        self.reproductor_cargar_y_reproducir(
            ruta=ruta,
            cola=self.reproductor_cola_actual,
            indice=indice,
            modo=self.reproductor_modo,
        )

    def reproductor_posicion_cambiada(self, posicion):
        if not self.reproductor_arrastrando_slider:
            self.slider_reproduccion.setValue(posicion)

        duracion = self.media_player.duration()
        self.label_tiempo.setText(
            f"{self.formato_tiempo(posicion)} / {self.formato_tiempo(duracion)}"
        )

    def reproductor_duracion_cambiada(self, duracion):
        self.slider_reproduccion.setRange(0, duracion)
        posicion = self.media_player.position()
        self.label_tiempo.setText(
            f"{self.formato_tiempo(posicion)} / {self.formato_tiempo(duracion)}"
        )

    def reproductor_estado_cambiado(self, estado):
        if estado == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_player_play.setText("Ⅱ")
            self.label_estado.setText("Reproduciendo")

            if self.reproductor_modo == "preview" and hasattr(self, "btn_preview_audio"):
                self.btn_preview_audio.setText("■ Detener preview")
        else:
            self.btn_player_play.setText("▶")

            if estado == QMediaPlayer.PlaybackState.PausedState:
                self.label_estado.setText("Pausado")
            else:
                self.label_estado.setText("Listo")

                if self.reproductor_modo == "preview" and hasattr(self, "btn_preview_audio"):
                    self.btn_preview_audio.setText("▶ Previsualizar")
                    self.btn_preview_audio.setEnabled(bool(self.resultado_actual))

    def reproductor_media_status_cambiado(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.reproductor_modo == "preview":
                self.detener_preview()
            else:
                self.reproductor_siguiente()

    def reproductor_error(self, error, error_string):
        if error_string:
            self.agregar_log(f"Error de reproducción: {error_string}")

            if self.reproductor_modo == "preview" and hasattr(self, "btn_preview_audio"):
                self.btn_preview_audio.setText("▶ Previsualizar")
                self.btn_preview_audio.setEnabled(bool(self.resultado_actual))
                self.set_estado("Falló la reproducción del preview.")

    def reproductor_slider_presionado(self):
        self.reproductor_arrastrando_slider = True

    def reproductor_slider_soltado(self):
        self.reproductor_arrastrando_slider = False
        self.media_player.setPosition(self.slider_reproduccion.value())

    def reproductor_cambiar_volumen(self, valor):
        self.audio_output.setVolume(valor / 100)

    # ============================================================
    # BIBLIOTECA MUSICAL
    # ============================================================

    def cargar_biblioteca(self):
        archivos = listar_media_en_carpeta(self.ruta_destino, "audio")

        biblioteca = []

        for archivo in archivos:
            ruta = archivo["ruta"]

            if not ruta.lower().endswith(".mp3"):
                continue

            fecha = "-"

            try:
                fecha = datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            archivo["fecha"] = fecha
            biblioteca.append(archivo)

        self.biblioteca_base = biblioteca
        self.aplicar_filtros_biblioteca()

    def aplicar_filtros_biblioteca(self):
        texto = ""

        if hasattr(self, "input_buscar_biblioteca"):
            texto = self.input_buscar_biblioteca.text().strip().lower()

        orden = "nombre"

        if hasattr(self, "combo_orden_biblioteca"):
            orden = self.combo_orden_biblioteca.currentData() or "nombre"

        visibles = []

        for archivo in self.biblioteca_base:
            nombre = archivo["nombre"].lower()
            ruta = archivo["ruta"].lower()

            if texto and texto not in nombre and texto not in ruta:
                continue

            visibles.append(archivo)

        if orden == "fecha":
            visibles.sort(
                key=lambda item: os.path.getmtime(item["ruta"]) if os.path.exists(item["ruta"]) else 0,
                reverse=True,
            )
        elif orden == "tamano":
            visibles.sort(
                key=lambda item: os.path.getsize(item["ruta"]) if os.path.exists(item["ruta"]) else 0,
                reverse=True,
            )
        else:
            visibles.sort(key=lambda item: item["nombre"].lower())

        self.biblioteca_visible = visibles

        if hasattr(self, "tabla_biblioteca"):
            self.cargar_archivos_en_tabla(self.tabla_biblioteca, visibles)

        if hasattr(self, "label_biblioteca_resumen"):
            self.label_biblioteca_resumen.setText(
                f"Canciones encontradas: {len(visibles)} | Total en carpeta: {len(self.biblioteca_base)}"
            )

        self.set_estado(f"Biblioteca actualizada. Canciones visibles: {len(visibles)}.")

    def reproducir_item_tabla_biblioteca(self, item):
        fila = item.row()
        ruta = self.obtener_ruta_fila_tabla(self.tabla_biblioteca, fila)

        if not ruta:
            return

        self.reproductor_cola_actual = self.biblioteca_visible
        self.reproductor_modo = "biblioteca"

        self.reproductor_cargar_y_reproducir(
            ruta=ruta,
            cola=self.biblioteca_visible,
            indice=fila,
            modo="biblioteca",
        )

    def reproducir_seleccion_biblioteca(self):
        fila = self.tabla_biblioteca.currentRow()

        if fila < 0 and self.biblioteca_visible:
            fila = 0

        if fila < 0:
            QMessageBox.information(
                self,
                "Biblioteca",
                "No hay canciones para reproducir.",
            )
            return

        ruta = self.obtener_ruta_fila_tabla(self.tabla_biblioteca, fila)

        self.reproductor_cargar_y_reproducir(
            ruta=ruta,
            cola=self.biblioteca_visible,
            indice=fila,
            modo="biblioteca",
        )

    # ============================================================
    # LISTAS PROPIAS
    # ============================================================

    def cargar_listas_en_ui(self):
        self.playlists = cargar_playlists()

        if not hasattr(self, "lista_playlists"):
            return

        seleccion_anterior = self.playlist_actual_nombre

        self.lista_playlists.clear()

        for nombre in sorted(self.playlists.keys(), key=lambda x: x.lower()):
            self.lista_playlists.addItem(nombre)

        if seleccion_anterior:
            items = self.lista_playlists.findItems(seleccion_anterior, Qt.MatchFlag.MatchExactly)

            if items:
                self.lista_playlists.setCurrentItem(items[0])
                return

        if self.lista_playlists.count() > 0:
            self.lista_playlists.setCurrentRow(0)
        else:
            self.playlist_actual_nombre = ""
            self.label_playlist_actual.setText("Sin listas creadas")
            self.tabla_playlist.setRowCount(0)

    def playlist_seleccionada(self, actual, anterior):
        if not actual:
            self.playlist_actual_nombre = ""
            self.label_playlist_actual.setText("Seleccioná una lista")
            self.tabla_playlist.setRowCount(0)
            return

        nombre = actual.text()
        self.playlist_actual_nombre = nombre
        self.label_playlist_actual.setText(nombre)

        self.cargar_canciones_playlist(nombre)

    def cargar_canciones_playlist(self, nombre):
        rutas = self.playlists.get(nombre, [])
        archivos = []

        rutas_existentes = []

        for ruta in rutas:
            if os.path.exists(ruta) and ruta.lower().endswith(".mp3"):
                archivos.append(self.archivo_a_objeto_musica(ruta))
                rutas_existentes.append(ruta)

        if len(rutas_existentes) != len(rutas):
            self.playlists[nombre] = rutas_existentes
            guardar_playlists(self.playlists)

        self.cargar_archivos_en_tabla(self.tabla_playlist, archivos)

        self.label_playlist_actual.setText(f"{nombre} ({len(archivos)} canciones)")

    def crear_lista_propia(self):
        nombre, ok = QInputDialog.getText(
            self,
            "Crear lista",
            "Nombre de la nueva lista:",
        )

        if not ok:
            return

        try:
            self.playlists = crear_playlist(nombre)
            self.playlist_actual_nombre = nombre.strip()
            self.cargar_listas_en_ui()
            self.agregar_log(f"Lista creada: {nombre.strip()}")

        except Exception as e:
            QMessageBox.warning(self, "Lista", str(e))

    def crear_lista_y_agregar_ruta(self, ruta):
        nombre, ok = QInputDialog.getText(
            self,
            "Crear lista",
            "Nombre de la nueva lista:",
        )

        if not ok:
            return

        nombre = nombre.strip()

        if not nombre:
            QMessageBox.warning(self, "Lista", "El nombre de la lista está vacío.")
            return

        try:
            self.playlists = crear_playlist(nombre)
            self.playlists = agregar_archivo_a_playlist(nombre, ruta)
            self.playlist_actual_nombre = nombre
            self.cargar_listas_en_ui()
            self.agregar_log(f"Lista creada y canción agregada: {nombre}")

        except Exception as e:
            QMessageBox.warning(self, "Lista", str(e))

    def borrar_lista_propia(self):
        if not self.playlist_actual_nombre:
            QMessageBox.information(self, "Listas", "No hay lista seleccionada.")
            return

        confirmacion = QMessageBox.question(
            self,
            "Borrar lista",
            f"¿Seguro que querés borrar la lista?\n\n{self.playlist_actual_nombre}",
        )

        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        nombre = self.playlist_actual_nombre

        self.playlists = borrar_playlist(nombre)
        self.playlist_actual_nombre = ""
        self.cargar_listas_en_ui()
        self.agregar_log(f"Lista borrada: {nombre}")

    def agregar_ruta_a_lista(self, nombre, ruta):
        try:
            self.playlists = agregar_archivo_a_playlist(nombre, ruta)
            self.playlist_actual_nombre = nombre
            self.cargar_listas_en_ui()
            self.agregar_log(f"Agregado a lista '{nombre}': {os.path.basename(ruta)}")
        except Exception as e:
            QMessageBox.warning(self, "Listas", str(e))

    def agregar_seleccion_a_lista(self):
        ruta = self.obtener_ruta_fila_tabla(self.tabla_biblioteca)

        if not ruta:
            QMessageBox.information(
                self,
                "Biblioteca",
                "Seleccioná una canción en Biblioteca.",
            )
            return

        if not self.playlists:
            respuesta = QMessageBox.question(
                self,
                "Listas",
                "No tenés listas creadas. ¿Querés crear una ahora?",
            )

            if respuesta == QMessageBox.StandardButton.Yes:
                self.crear_lista_y_agregar_ruta(ruta)
            else:
                return

            return

        nombres = sorted(self.playlists.keys(), key=lambda x: x.lower())

        nombre, ok = QInputDialog.getItem(
            self,
            "Agregar a lista",
            "Elegí la lista:",
            nombres,
            0,
            False,
        )

        if not ok or not nombre:
            return

        self.agregar_ruta_a_lista(nombre, ruta)
        self.tabs.setCurrentIndex(3)

    def quitar_seleccion_de_lista(self):
        if not self.playlist_actual_nombre:
            QMessageBox.information(self, "Listas", "No hay lista seleccionada.")
            return

        ruta = self.obtener_ruta_fila_tabla(self.tabla_playlist)

        if not ruta:
            QMessageBox.information(self, "Listas", "Seleccioná una canción.")
            return

        nombre_lista = self.playlist_actual_nombre

        self.playlists = quitar_archivo_de_playlist(nombre_lista, ruta)
        self.cargar_listas_en_ui()
        self.agregar_log(f"Quitado de lista '{nombre_lista}': {os.path.basename(ruta)}")

    def reproducir_item_tabla_playlist(self, item):
        fila = item.row()
        self.reproducir_playlist_desde_fila(fila)

    def reproducir_playlist_desde_fila(self, fila):
        if not self.playlist_actual_nombre:
            return

        rutas = self.playlists.get(self.playlist_actual_nombre, [])

        archivos = [
            self.archivo_a_objeto_musica(ruta)
            for ruta in rutas
            if os.path.exists(ruta) and ruta.lower().endswith(".mp3")
        ]

        if not archivos:
            QMessageBox.information(self, "Listas", "La lista no tiene canciones disponibles.")
            return

        if fila < 0 or fila >= len(archivos):
            fila = 0

        self.reproductor_cargar_y_reproducir(
            ruta=archivos[fila]["ruta"],
            cola=archivos,
            indice=fila,
            modo="playlist",
        )

    def reproducir_lista_actual(self):
        fila = self.tabla_playlist.currentRow()

        if fila < 0:
            fila = 0

        self.reproducir_playlist_desde_fila(fila)

    def abrir_archivo_playlists(self):
        ruta = obtener_ruta_playlists()

        try:
            if not os.path.exists(ruta):
                guardar_playlists(self.playlists)

            if sys.platform.startswith("win"):
                os.startfile(str(ruta))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(ruta)])
            else:
                subprocess.Popen(["xdg-open", str(ruta)])

        except Exception as e:
            QMessageBox.warning(
                self,
                "Listas",
                f"No se pudo abrir playlists.json:\n\n{e}",
            )

    # ============================================================
    # HISTORIAL
    # ============================================================

    def agregar_log(self, texto):
        hora = datetime.now().strftime("%H:%M:%S")
        linea = f"[{hora}] {texto}"

        self.log_items.append(linea)

        if hasattr(self, "lista_log"):
            self.lista_log.addItem(linea)
            self.lista_log.scrollToBottom()

    def agregar_log_resumen(self, resumen):
        if not resumen:
            return

        completados = resumen.get("completados", 0)
        omitidos = resumen.get("omitidos", 0)
        errores = resumen.get("errores", [])
        archivos = resumen.get("archivos", [])

        self.agregar_log(
            f"Resumen: completados={completados}, omitidos={omitidos}, errores={len(errores)}"
        )

        for archivo in archivos[-10:]:
            self.agregar_log(f"Archivo generado: {archivo}")

        for error in errores[-10:]:
            self.agregar_log(f"Omitido/Error: {error}")

    def limpiar_log(self):
        self.log_items.clear()
        self.lista_log.clear()
        self.agregar_log("Historial limpiado.")

    def copiar_log(self):
        texto = "\n".join(self.log_items)
        QApplication.clipboard().setText(texto)
        QMessageBox.information(self, "Historial", "Historial copiado al portapapeles.")

    # ============================================================
    # HERRAMIENTAS
    # ============================================================

    def verificar_herramientas_inicio(self):
        self.actualizar_estado_herramientas()

        estado = obtener_estado_herramientas()

        falta_ytdlp = not estado["yt_dlp_existe"]
        falta_ffmpeg = not estado["ffmpeg_local"]
        falta_ffprobe = not estado["ffprobe_local"]

        if not (falta_ytdlp or falta_ffmpeg or falta_ffprobe):
            self.set_estado("Herramientas internas listas.")
            self.agregar_log("Herramientas internas listas.")
            return

        faltantes = []

        if falta_ytdlp:
            faltantes.append("- yt-dlp.exe")

        if falta_ffmpeg:
            faltantes.append("- ffmpeg.exe")

        if falta_ffprobe:
            faltantes.append("- ffprobe.exe")

        mensaje = (
            "Faltan herramientas internas necesarias para descargar y convertir audio.\n\n"
            "La app necesita preparar:\n"
            + "\n".join(faltantes)
            + "\n\n¿Querés descargarlas y prepararlas ahora?"
        )

        respuesta = QMessageBox.question(
            self,
            "Herramientas necesarias",
            mensaje,
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            self.preparar_herramientas_desde_ui(mostrar_mensaje_final=True)
        else:
            self.set_estado("Faltan herramientas internas.")
            self.agregar_log("El usuario omitió la preparación de herramientas.")

    def preparar_herramientas_desde_ui(self, mostrar_mensaje_final=True):
        if self.thread_tools and self.thread_tools.isRunning():
            QMessageBox.information(
                self,
                "Herramientas",
                "Ya hay una preparación/actualización en curso.",
            )
            return

        self.set_estado("Preparando herramientas internas...")
        self.agregar_log("Preparando herramientas internas...")
        self.set_botones_tools(False)

        self.thread_tools = WorkerPrepararHerramientas()
        self.thread_tools.terminado.connect(
            lambda ok, mensaje: self.herramientas_terminadas(
                ok,
                mensaje,
                mostrar_mensaje_final,
            )
        )
        self.thread_tools.start()

    def actualizar_herramientas_desde_ui(self):
        if self.thread_tools and self.thread_tools.isRunning():
            QMessageBox.information(
                self,
                "Herramientas",
                "Ya hay una preparación/actualización en curso.",
            )
            return

        confirmacion = QMessageBox.question(
            self,
            "Actualizar herramientas",
            "Esto va a descargar nuevamente yt-dlp.exe, ffmpeg.exe y ffprobe.exe.\n\n¿Continuar?",
        )

        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        self.set_estado("Actualizando yt-dlp + FFmpeg...")
        self.agregar_log("Actualizando yt-dlp + FFmpeg...")
        self.set_botones_tools(False)

        self.thread_tools = WorkerActualizarHerramientas()
        self.thread_tools.terminado.connect(
            lambda ok, mensaje: self.herramientas_terminadas(
                ok,
                mensaje,
                True,
            )
        )
        self.thread_tools.start()

    def herramientas_terminadas(self, ok, mensaje, mostrar_mensaje_final=True):
        self.set_botones_tools(True)
        self.actualizar_estado_herramientas()

        if ok:
            self.set_estado("Herramientas listas.")
            self.agregar_log("Herramientas listas.")

            if mostrar_mensaje_final:
                QMessageBox.information(
                    self,
                    "Herramientas",
                    mensaje,
                )
        else:
            self.set_estado("Error preparando herramientas.")
            self.agregar_log(f"Error preparando herramientas: {mensaje}")

            QMessageBox.critical(
                self,
                "Error",
                mensaje,
            )

    def set_botones_tools(self, habilitado):
        self.btn_preparar_tools.setEnabled(habilitado)
        self.btn_actualizar_tools.setEnabled(habilitado)
        self.btn_refrescar_tools.setEnabled(habilitado)

    def actualizar_estado_herramientas(self):
        estado = obtener_estado_herramientas()

        texto = (
            f"Carpeta tools:\n{estado['tools_dir']}\n\n"
            f"yt-dlp.exe: {'OK' if estado['yt_dlp_existe'] else 'No encontrado'}\n"
            f"Versión: {estado['yt_dlp_version']}\n"
            f"Ruta: {estado['yt_dlp_ruta']}\n\n"
            f"ffmpeg.exe local: {'OK' if estado['ffmpeg_local'] else 'No encontrado'}\n"
            f"FFmpeg disponible: {'OK' if estado['ffmpeg_disponible'] else 'No encontrado'}\n"
            f"Versión: {estado['ffmpeg_version']}\n"
            f"Ruta: {estado['ffmpeg_ruta'] or '-'}\n\n"
            f"ffprobe.exe local: {'OK' if estado['ffprobe_local'] else 'No encontrado'}\n"
            f"FFprobe disponible: {'OK' if estado['ffprobe_disponible'] else 'No encontrado'}\n"
            f"Versión: {estado['ffprobe_version']}\n"
            f"Ruta: {estado['ffprobe_ruta'] or '-'}"
        )

        self.label_tools_estado.setText(texto)

    # ============================================================
    # CONFIGURACIÓN
    # ============================================================

    def tab_cambiada(self, index):
        self.config["ultima_pestana"] = index
        self.guardar_config_actual()

    def tema_cambiado(self):
        tema = self.combo_tema.currentData()

        if not tema:
            return

        self.tema_actual = str(tema)
        self.config["tema"] = self.tema_actual
        self.setStyleSheet(obtener_estilo(self.tema_actual))

        if hasattr(self, "visualizador_widget"):
            self.visualizador_widget.set_tema(self.tema_actual)

        self.guardar_config_actual()

        if self.tema_actual == "claro":
            self.set_estado("Tema claro azul aplicado.")
            self.agregar_log("Tema cambiado: claro azul.")
        else:
            self.set_estado("Tema oscuro moderno aplicado.")
            self.agregar_log("Tema cambiado: oscuro moderno.")

    def calidad_cambiada(self):
        calidad = self.combo_calidad.currentData()

        if calidad:
            self.calidad_mp3 = str(calidad)
            self.config["calidad_mp3"] = self.calidad_mp3
            self.guardar_config_actual()
            self.set_estado(f"Calidad MP3 configurada en {self.calidad_mp3} kbps.")
            self.agregar_log(f"Calidad configurada: {self.calidad_mp3} kbps.")

    def guardar_config_manual(self):
        self.guardar_config_actual()
        self.agregar_log("Configuración guardada manualmente.")
        QMessageBox.information(
            self,
            "Configuración",
            "Configuración guardada correctamente.",
        )

    # ============================================================
    # PREVIEW / BÚSQUEDA
    # ============================================================

    def obtener_thumbnail_resultado(self, resultado):
        thumbnails = resultado.get("thumbnails")

        if isinstance(thumbnails, list) and thumbnails:
            ultimo = thumbnails[-1]

            if isinstance(ultimo, dict):
                return ultimo.get("url", "")

        return resultado.get("thumbnail", "")

    def resultado_seleccionado(self, index):
        if index < 0 or index >= len(self.resultados):
            self.resultado_actual = None
            self.limpiar_preview()
            return

        resultado = self.resultados[index]
        self.resultado_actual = resultado

        titulo = resultado.get("title", "Sin título")
        duracion = resultado.get("duration", "N/A")
        canal = resultado.get("channel", {}).get("name", "")

        self.preview_titulo.setText(self.texto_corto(titulo, 52))
        self.preview_titulo.setToolTip(titulo)

        self.preview_canal.setText(self.texto_corto(canal or "-", 44))
        self.preview_canal.setToolTip(canal or "-")

        self.preview_duracion.setText(f"Duración: {duracion or '-'}")

        thumbnail_url = self.obtener_thumbnail_resultado(resultado)
        self.cargar_thumbnail(thumbnail_url)

        self.input_nombre_archivo.setText(titulo)

        self.btn_preview_audio.setEnabled(True)
        if (
            self.reproductor_modo == "preview"
            and self.preview_video_url_actual
            and self.preview_video_url_actual == resultado.get("link")
            and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.btn_preview_audio.setText("■ Detener preview")
        else:
            self.btn_preview_audio.setText("▶ Previsualizar")

    def limpiar_preview(self):
        self.preview_imagen.clear()
        self.preview_imagen.setText("Sin video")
        self.preview_titulo.setText("-")
        self.preview_titulo.setToolTip("")
        self.preview_canal.setText("Canal: -")
        self.preview_canal.setToolTip("")
        self.preview_duracion.setText("Duración: -")
        self.input_nombre_archivo.clear()
        self.btn_preview_audio.setEnabled(False)
        self.btn_preview_audio.setText("▶ Previsualizar")

    def cargar_thumbnail(self, url):
        if not url:
            self.preview_imagen.clear()
            self.preview_imagen.setText("Sin miniatura")
            return

        try:
            datos = urllib.request.urlopen(url, timeout=10).read()

            pixmap = QPixmap()
            pixmap.loadFromData(datos)

            if pixmap.isNull():
                self.preview_imagen.setText("No se pudo cargar")
                return

            pixmap = pixmap.scaled(
                self.preview_imagen.width(),
                self.preview_imagen.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.preview_imagen.setPixmap(pixmap)
            self.preview_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)

        except Exception:
            self.preview_imagen.clear()
            self.preview_imagen.setText("No se pudo cargar")


    def toggle_preview_resultado(self):
        if self.reproductor_modo == "preview" and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.detener_preview()
            return

        self.iniciar_preview_resultado()

    def iniciar_preview_resultado(self):
        if not self.resultado_actual:
            QMessageBox.warning(
                self,
                "Atención",
                "Seleccioná un resultado primero.",
            )
            return

        url_video = self.resultado_actual.get("link")

        if not url_video:
            QMessageBox.warning(
                self,
                "Atención",
                "El resultado seleccionado no tiene URL.",
            )
            return

        if self.thread_preview and self.thread_preview.isRunning():
            self.set_estado("Ya se está preparando un preview...")
            return

        self.btn_preview_audio.setEnabled(False)
        self.btn_preview_audio.setText("Preparando...")
        self.set_estado("Preparando preview de audio...")
        self.agregar_log(f"Preparando preview: {url_video}")

        self.thread_preview = WorkerPreviewAudio(url_video)
        self.thread_preview.terminado.connect(
            lambda ok, mensaje, url_audio, video_url=url_video: self.preview_url_obtenida(
                ok, mensaje, url_audio, video_url
            )
        )
        self.thread_preview.start()

    def preview_url_obtenida(self, ok, mensaje, url_audio, url_video):
        self.thread_preview = None
        self.btn_preview_audio.setEnabled(True)

        if not ok:
            self.btn_preview_audio.setText("▶ Previsualizar")
            self.set_estado("No se pudo preparar el preview.")
            self.agregar_log(f"Error de preview: {mensaje}")
            QMessageBox.warning(
                self,
                "Preview",
                f"No se pudo previsualizar este audio:\n\n{mensaje}",
            )
            return

        self.preview_video_url_actual = url_video
        self.preview_audio_url_actual = url_audio

        titulo = "Preview"
        if self.resultado_actual:
            titulo = self.resultado_actual.get("title", "Preview")

        self.reproductor_modo = "preview"
        self.reproductor_cola_actual = []
        self.reproductor_indice_actual = -1
        self.reproductor_ruta_actual = "__preview__"

        self.label_player_titulo.setText(f"Preview: {self.texto_corto(titulo, 80)}")
        self.label_player_sub.setText("Audio temporal de YouTube")
        self.label_player_icon.setText("▶")

        if hasattr(self, "visualizador_widget"):
            self.visualizador_widget.set_titulo(f"Preview: {titulo}")

        self.media_player.stop()
        self.media_player.setSource(QUrl(url_audio))
        self.media_player.play()

        self.btn_preview_audio.setText("■ Detener preview")
        self.set_estado("Reproduciendo preview.")
        self.agregar_log("Preview iniciado.")

    def detener_preview(self):
        if self.reproductor_modo == "preview":
            self.media_player.stop()
            self.reproductor_ruta_actual = ""
            self.reproductor_indice_actual = -1
            self.reproductor_cola_actual = []
            self.preview_audio_url_actual = ""

            self.label_player_titulo.setText("Nada reproduciendo")
            self.label_player_sub.setText("Elegí una canción de la biblioteca o una lista")
            self.label_player_icon.setText("♪")
            self.slider_reproduccion.setValue(0)
            self.label_tiempo.setText("00:00 / 00:00")

            if hasattr(self, "visualizador_widget"):
                self.visualizador_widget.set_titulo("Sin reproducción")

        self.btn_preview_audio.setEnabled(bool(self.resultado_actual))
        self.btn_preview_audio.setText("▶ Previsualizar")
        self.set_estado("Preview detenido.")
        self.agregar_log("Preview detenido.")

    def abrir_video_actual(self):
        if not self.resultado_actual:
            QMessageBox.warning(
                self,
                "Atención",
                "Seleccioná un video primero.",
            )
            return

        url = self.resultado_actual.get("link")

        if not url:
            QMessageBox.warning(
                self,
                "Atención",
                "El resultado seleccionado no tiene URL.",
            )
            return

        self.agregar_log(f"Abriendo video: {url}")
        webbrowser.open(url)

    def buscar_o_previsualizar(self):
        texto = self.input_busqueda.text().strip()

        self.lista_resultados.clear()
        self.resultados = []
        self.resultado_actual = None
        self.limpiar_preview()

        if not texto:
            QMessageBox.warning(
                self,
                "Atención",
                "Escribí algo para buscar o pegá un link.",
            )
            return

        if es_playlist(texto):
            QMessageBox.critical(
                self,
                "Error",
                "No pongas playlists en el buscador principal. Usá la pestaña 'Descargas'.",
            )
            return

        self.set_estado("Buscando...")
        self.agregar_log(f"Búsqueda iniciada: {texto}")

        try:
            if es_url(texto):
                info = obtener_info_url(texto)

                if not info:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "No se pudo obtener información de la URL.",
                    )
                    self.set_estado("No se pudo leer la URL.")
                    self.agregar_log("No se pudo leer la URL.")
                    return

                duracion = info.get("duration")
                duracion_texto = str(duracion) if duracion else "N/A"

                self.resultados = [
                    {
                        "title": info.get("title", "Sin título"),
                        "duration": duracion_texto,
                        "channel": {"name": info.get("channel") or info.get("uploader", "")},
                        "link": texto,
                        "thumbnail": info.get("thumbnail", ""),
                    }
                ]

                self.lista_resultados.addItem(
                    f"{info.get('title', 'Sin título')} ({duracion_texto})"
                )

                self.lista_resultados.setCurrentRow(0)
                self.set_estado("Video cargado correctamente.")
                self.agregar_log("Video cargado correctamente.")
                return

            # Búsqueda estable para instalador: usa yt-dlp directo.
            # No usa youtube-search-python/httpx, así evitamos el error de proxies.
            resultados = buscar_canciones_ytdlp(texto, limite=8)
            self.resultados = resultados

            if not resultados:
                self.set_estado("No se encontraron resultados.")
                self.agregar_log("Sin resultados.")
                QMessageBox.information(
                    self,
                    "Sin resultados",
                    "No se encontraron resultados para esa búsqueda.",
                )
                return

            for r in resultados:
                titulo = r.get("title", "Sin título")
                duracion = r.get("duration", "N/A")
                canal = r.get("channel", {}).get("name", "")

                self.lista_resultados.addItem(f"{titulo} ({duracion}) - {canal}")

            self.lista_resultados.setCurrentRow(0)
            self.set_estado(f"Se encontraron {len(resultados)} resultados.")
            self.agregar_log(f"Resultados encontrados: {len(resultados)}.")

        except Exception as e:
            self.set_estado("Error durante la búsqueda.")
            self.agregar_log(f"Error durante la búsqueda: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo completar la búsqueda:\n\n{e}",
            )

    # ============================================================
    # DESCARGAS
    # ============================================================

    def agregar_a_lista(self):
        index = self.lista_resultados.currentRow()

        if index < 0 or index >= len(self.resultados):
            QMessageBox.warning(
                self,
                "Atención",
                "Seleccioná un resultado para agregar.",
            )
            return

        url = self.resultados[index]["link"]
        titulo = self.resultados[index].get("title", "Sin título")
        nombre_archivo = self.input_nombre_archivo.text().strip()

        agregado = self.agregar_item_a_cola(
            url=url,
            titulo=titulo,
            tipo="video",
            nombre_archivo=nombre_archivo,
        )

        if agregado:
            self.set_estado("Elemento agregado a descargas.")
            self.agregar_log(f"Agregado a descargas: {titulo}")
            self.tabs.setCurrentIndex(1)

    def agregar_playlist_a_lista(self):
        url = self.input_playlist.text().strip()

        if not url:
            QMessageBox.warning(
                self,
                "Atención",
                "Pegá la URL de la playlist para agregar.",
            )
            return

        if not es_playlist(url):
            QMessageBox.critical(
                self,
                "Error",
                "La URL no parece ser una playlist válida.",
            )
            return

        agregado = self.agregar_item_a_cola(
            url=url,
            titulo=url,
            tipo="playlist",
            nombre_archivo="",
        )

        if agregado:
            self.input_playlist.clear()
            self.set_estado("Playlist agregada a descargas.")
            self.agregar_log(f"Playlist agregada a descargas: {url}")

    def eliminar_de_lista(self):
        index = self.lista_descarga.currentRow()

        if index < 0:
            QMessageBox.warning(
                self,
                "Atención",
                "Seleccioná un elemento.",
            )
            return

        item = self.lista_descarga_items[index]
        self.agregar_log(f"Quitado de descargas: {item.get('titulo', '')}")

        self.lista_descarga_items.pop(index)
        self.lista_descarga.takeItem(index)

        self.set_estado("Elemento quitado.")

    def limpiar_lista(self):
        if not self.lista_descarga_items:
            self.set_estado("La lista ya está vacía.")
            return

        confirmacion = QMessageBox.question(
            self,
            "Confirmar",
            "¿Seguro que querés limpiar toda la lista?",
        )

        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        self.lista_descarga_items.clear()
        self.lista_descarga.clear()
        self.barra_progreso.setValue(0)

        self.set_estado("Lista limpiada.")
        self.agregar_log("Lista de descargas limpiada.")

    def reintentar_errores(self):
        errores = 0

        for index, item in enumerate(self.lista_descarga_items):
            if item.get("estado") == self.ESTADO_ERROR:
                item["estado"] = self.ESTADO_PENDIENTE
                item["error"] = ""
                item["mensaje_resultado"] = ""
                item["resumen"] = {}
                self.refrescar_item_cola(index)
                errores += 1

        if errores == 0:
            QMessageBox.information(
                self,
                "Sin errores",
                "No hay elementos con error para reintentar.",
            )
            return

        self.set_estado(f"Errores reactivados: {errores}.")
        self.agregar_log(f"Errores reactivados: {errores}.")

    def iniciar_descarga(self):
        index = self.lista_resultados.currentRow()

        if index < 0 or index >= len(self.resultados):
            QMessageBox.warning(
                self,
                "Atención",
                "Seleccioná un resultado válido.",
            )
            return

        url = self.resultados[index]["link"]
        titulo = self.resultados[index].get("title", "Sin título")
        nombre_archivo = self.input_nombre_archivo.text().strip()

        self.agregar_log(f"Descarga individual iniciada: {titulo}")
        self.iniciar_descarga_url(url, nombre_archivo=nombre_archivo)

    def iniciar_descarga_url(self, url, nombre_archivo=None):
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(
                self,
                "Atención",
                "Ya hay una descarga en curso.",
            )
            return

        self.descargando_lista = False
        self.indice_descarga_actual = None

        self.barra_progreso.setValue(0)
        self.set_controles_descarga(False)
        self.set_estado(f"Descargando en MP3 {self.calidad_mp3} kbps...")

        self.thread = WorkerDescarga(
            url=url,
            destino=self.ruta_destino,
            calidad_mp3=self.calidad_mp3,
            nombre_archivo=nombre_archivo,
        )

        self.thread.progreso.connect(self.barra_progreso.setValue)
        self.thread.terminado.connect(self.descarga_terminada_individual)
        self.thread.start()

    def descarga_terminada_individual(self, ok, mensaje, resumen):
        self.set_controles_descarga(True)

        self.agregar_log_resumen(resumen)

        if ok:
            self.cargar_biblioteca()
            self.set_estado(mensaje)
            self.agregar_log(mensaje)
            QMessageBox.information(self, "Listo", mensaje)
        else:
            self.set_estado("La descarga falló.")
            self.agregar_log(f"Descarga fallida: {mensaje}")
            QMessageBox.critical(self, "Error", mensaje)

        self.barra_progreso.setValue(0)

    def iniciar_descarga_lista(self):
        if not self.lista_descarga_items:
            QMessageBox.warning(
                self,
                "Atención",
                "La lista está vacía.",
            )
            return

        if self.thread and self.thread.isRunning():
            QMessageBox.warning(
                self,
                "Atención",
                "Ya hay una descarga en curso.",
            )
            return

        pendientes = [
            item
            for item in self.lista_descarga_items
            if item.get("estado") == self.ESTADO_PENDIENTE
        ]

        if not pendientes:
            QMessageBox.information(
                self,
                "Sin pendientes",
                "No hay elementos pendientes para descargar.",
            )
            return

        self.tabs.setCurrentIndex(1)
        self.descargando_lista = True
        self.set_controles_descarga(False)
        self.barra_progreso.setValue(0)

        self.agregar_log(f"Descarga de lista iniciada. Pendientes: {len(pendientes)}.")
        self.descargar_siguiente_pendiente()

    def descargar_siguiente_pendiente(self):
        siguiente_index = None

        for index, item in enumerate(self.lista_descarga_items):
            if item.get("estado") == self.ESTADO_PENDIENTE:
                siguiente_index = index
                break

        if siguiente_index is None:
            self.finalizar_descarga_lista()
            return

        self.indice_descarga_actual = siguiente_index

        item_actual = self.lista_descarga_items[siguiente_index]
        item_actual["estado"] = self.ESTADO_DESCARGANDO
        item_actual["error"] = ""
        item_actual["mensaje_resultado"] = ""

        self.refrescar_item_cola(siguiente_index)
        self.lista_descarga.setCurrentRow(siguiente_index)

        total = len(self.lista_descarga_items)
        conteo = self.contar_estados_cola()
        completados = conteo.get(self.ESTADO_COMPLETADO, 0)

        self.barra_progreso.setValue(0)
        self.set_estado(
            f"Descargando {completados + 1} de {total} en MP3 {self.calidad_mp3} kbps: {item_actual['titulo']}"
        )
        self.agregar_log(f"Descargando item: {item_actual['titulo']}")

        self.thread = WorkerDescarga(
            url=item_actual["url"],
            destino=self.ruta_destino,
            calidad_mp3=self.calidad_mp3,
            nombre_archivo=item_actual.get("nombre_archivo", ""),
        )

        self.thread.progreso.connect(self.barra_progreso.setValue)
        self.thread.terminado.connect(self.descarga_item_cola_terminada)
        self.thread.start()

    def descarga_item_cola_terminada(self, ok, mensaje, resumen):
        index = self.indice_descarga_actual

        if index is None or index < 0 or index >= len(self.lista_descarga_items):
            self.finalizar_descarga_lista()
            return

        item_actual = self.lista_descarga_items[index]
        item_actual["resumen"] = resumen

        completados = resumen.get("completados", 0)
        omitidos = resumen.get("omitidos", 0)

        if ok:
            item_actual["estado"] = self.ESTADO_COMPLETADO

            if item_actual.get("tipo") == "playlist":
                item_actual["mensaje_resultado"] = f"completos {completados}, omitidos {omitidos}"
            else:
                item_actual["mensaje_resultado"] = "completo"

            item_actual["error"] = ""
            self.agregar_log(
                f"Item completado: {item_actual['titulo']} | {item_actual['mensaje_resultado']}"
            )
        else:
            item_actual["estado"] = self.ESTADO_ERROR
            item_actual["error"] = mensaje
            item_actual["mensaje_resultado"] = "error"
            self.agregar_log(f"Item con error: {item_actual['titulo']} | {mensaje}")

        self.agregar_log_resumen(resumen)
        self.refrescar_item_cola(index)
        self.descargar_siguiente_pendiente()

    def finalizar_descarga_lista(self):
        self.cargar_biblioteca()
        self.set_controles_descarga(True)
        self.barra_progreso.setValue(0)
        self.indice_descarga_actual = None
        self.descargando_lista = False

        conteo = self.contar_estados_cola()

        items_completados = conteo.get(self.ESTADO_COMPLETADO, 0)
        items_error = conteo.get(self.ESTADO_ERROR, 0)
        items_pendientes = conteo.get(self.ESTADO_PENDIENTE, 0)

        archivos_completados = 0
        internos_omitidos = 0

        for item in self.lista_descarga_items:
            resumen = item.get("resumen", {})
            archivos_completados += int(resumen.get("completados", 0) or 0)
            internos_omitidos += int(resumen.get("omitidos", 0) or 0)

        mensaje_estado = (
            f"Lista terminada. Archivos completos: {archivos_completados}. "
            f"Omitidos: {internos_omitidos}. Items con error: {items_error}."
        )

        self.set_estado(mensaje_estado)
        self.agregar_log(mensaje_estado)

        if items_error > 0 or internos_omitidos > 0:
            QMessageBox.warning(
                self,
                "Descarga finalizada con observaciones",
                f"La lista terminó.\n\n"
                f"Archivos completos: {archivos_completados}\n"
                f"Omitidos dentro de playlists: {internos_omitidos}\n"
                f"Items completados: {items_completados}\n"
                f"Items con error: {items_error}\n"
                f"Pendientes: {items_pendientes}\n\n"
                f"Revisá la pestaña Historial para más detalle.",
            )
        else:
            QMessageBox.information(
                self,
                "Listo",
                f"Descarga de lista completada.\n\n"
                f"Archivos completos: {archivos_completados}",
            )

    # ============================================================
    # UTILIDADES DESCARGAS
    # ============================================================

    def url_ya_en_lista(self, url):
        for item in self.lista_descarga_items:
            if item["url"] == url:
                return True
        return False

    def crear_texto_item_cola(self, item):
        estado = item.get("estado", self.ESTADO_PENDIENTE)
        titulo = item.get("titulo", "Sin título")
        tipo = item.get("tipo", "video")
        nombre_archivo = item.get("nombre_archivo", "")
        mensaje_resultado = item.get("mensaje_resultado", "")

        prefijo_tipo = "Playlist" if tipo == "playlist" else "Video"

        if estado == self.ESTADO_PENDIENTE:
            icono = "⏳"
        elif estado == self.ESTADO_DESCARGANDO:
            icono = "⬇"
        elif estado == self.ESTADO_COMPLETADO:
            icono = "✓"
        elif estado == self.ESTADO_ERROR:
            icono = "✕"
        else:
            icono = "•"

        extra_nombre = f" → {nombre_archivo}" if nombre_archivo else ""
        extra_resultado = f" | {mensaje_resultado}" if mensaje_resultado else ""

        return f"{icono} [{estado}] {prefijo_tipo}: {titulo}{extra_nombre}{extra_resultado}"

    def refrescar_item_cola(self, index):
        if index < 0 or index >= len(self.lista_descarga_items):
            return

        item_data = self.lista_descarga_items[index]
        item_widget = item_data.get("item_widget")

        if item_widget is None:
            return

        item_widget.setText(self.crear_texto_item_cola(item_data))

        if item_data.get("estado") == self.ESTADO_ERROR:
            item_widget.setToolTip(item_data.get("error", ""))
        else:
            item_widget.setToolTip(item_data.get("url", ""))

    def agregar_item_a_cola(self, url, titulo, tipo, nombre_archivo=None):
        if self.url_ya_en_lista(url):
            QMessageBox.information(
                self,
                "Duplicado",
                "Ese elemento ya está en la lista.",
            )
            return False

        item_data = {
            "url": url,
            "titulo": titulo,
            "tipo": tipo,
            "nombre_archivo": nombre_archivo or "",
            "estado": self.ESTADO_PENDIENTE,
            "error": "",
            "mensaje_resultado": "",
            "resumen": {},
            "item_widget": None,
        }

        item_widget = QListWidgetItem(self.crear_texto_item_cola(item_data))
        item_widget.setToolTip(url)

        item_data["item_widget"] = item_widget

        self.lista_descarga_items.append(item_data)
        self.lista_descarga.addItem(item_widget)

        return True

    def contar_estados_cola(self):
        conteo = {
            self.ESTADO_PENDIENTE: 0,
            self.ESTADO_DESCARGANDO: 0,
            self.ESTADO_COMPLETADO: 0,
            self.ESTADO_ERROR: 0,
        }

        for item in self.lista_descarga_items:
            estado = item.get("estado", self.ESTADO_PENDIENTE)
            conteo[estado] = conteo.get(estado, 0) + 1

        return conteo

    # ============================================================
    # CARPETAS / ARCHIVOS
    # ============================================================

    def elegir_carpeta(self):
        ruta = QFileDialog.getExistingDirectory(
            self,
            "Elegir carpeta destino",
            self.ruta_destino,
        )

        if ruta:
            self.ruta_destino = ruta

            self.label_carpeta.setText(f"Carpeta destino: {ruta}")
            self.label_config_carpeta.setText(f"Actual: {ruta}")

            self.config["carpeta_destino"] = self.ruta_destino
            self.guardar_config_actual()

            self.cargar_biblioteca()
            self.set_estado("Carpeta destino actualizada.")
            self.agregar_log(f"Carpeta destino actualizada: {ruta}")

    def abrir_carpeta(self):
        if not os.path.exists(self.ruta_destino):
            QMessageBox.warning(
                self,
                "Atención",
                "La carpeta destino no existe.",
            )
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(self.ruta_destino)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.ruta_destino])
            else:
                subprocess.Popen(["xdg-open", self.ruta_destino])

            self.set_estado("Carpeta abierta.")
            self.agregar_log(f"Carpeta abierta: {self.ruta_destino}")

        except Exception as e:
            self.agregar_log(f"No se pudo abrir la carpeta: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir la carpeta:\n\n{e}",
            )

    def abrir_ubicacion_archivo(self, ruta_archivo):
        if not ruta_archivo or not os.path.exists(ruta_archivo):
            QMessageBox.warning(
                self,
                "Archivo",
                "No se encontró el archivo.",
            )
            return

        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta_archivo)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", ruta_archivo])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(ruta_archivo)])

            self.agregar_log(f"Abriendo ubicación: {ruta_archivo}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Archivo",
                f"No se pudo abrir la ubicación:\n\n{e}",
            )

    def borrar_archivo(self):
        ruta_archivo = self.obtener_ruta_fila_tabla(self.tabla_biblioteca)

        if not ruta_archivo:
            QMessageBox.warning(
                self,
                "Atención",
                "Seleccioná un archivo para borrar.",
            )
            return

        archivo = os.path.basename(ruta_archivo)

        confirmacion = QMessageBox.question(
            self,
            "Confirmar borrado",
            f"¿Seguro que querés borrar este archivo?\n\n{archivo}",
        )

        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        try:
            if os.path.abspath(ruta_archivo) == os.path.abspath(self.reproductor_ruta_actual):
                self.reproductor_stop()
                self.reproductor_ruta_actual = ""
                self.label_player_titulo.setText("Nada reproduciendo")
                self.label_player_sub.setText("Biblioteca musical")
                if hasattr(self, "visualizador_widget"):
                    self.visualizador_widget.set_titulo("Nada reproduciendo")

            os.remove(ruta_archivo)

            self.cargar_biblioteca()
            self.cargar_listas_en_ui()

            self.agregar_log(f"Archivo borrado: {archivo}")

            QMessageBox.information(
                self,
                "Borrado",
                f"Archivo borrado:\n\n{archivo}",
            )

        except Exception as e:
            self.agregar_log(f"No se pudo borrar archivo: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo borrar:\n\n{e}",
            )

    # ============================================================
    # UTILIDADES GENERALES
    # ============================================================

    def set_estado(self, texto):
        if hasattr(self, "label_estado"):
            self.label_estado.setText(texto)

    def set_controles_descarga(self, habilitado):
        self.btn_buscar.setEnabled(habilitado)
        self.btn_descargar.setEnabled(habilitado)
        self.btn_agregar.setEnabled(habilitado)
        self.btn_agregar_playlist.setEnabled(habilitado)
        self.btn_eliminar.setEnabled(habilitado)
        self.btn_descargar_lista.setEnabled(habilitado)
        self.btn_limpiar_lista.setEnabled(habilitado)
        self.btn_reintentar_errores.setEnabled(habilitado)
        self.btn_elegir_carpeta.setEnabled(habilitado)
        self.btn_borrar_archivo.setEnabled(habilitado)
        self.btn_config_elegir_carpeta.setEnabled(habilitado)
        self.btn_guardar_config.setEnabled(habilitado)
        self.btn_preparar_tools.setEnabled(habilitado)
        self.btn_actualizar_tools.setEnabled(habilitado)
        self.btn_refrescar_tools.setEnabled(habilitado)

        self.input_busqueda.setEnabled(habilitado)
        self.input_playlist.setEnabled(habilitado)
        self.input_nombre_archivo.setEnabled(habilitado)
        self.combo_calidad.setEnabled(habilitado)
        self.combo_tema.setEnabled(habilitado)

        if hasattr(self, "input_buscar_biblioteca"):
            self.input_buscar_biblioteca.setEnabled(habilitado)

        if hasattr(self, "combo_orden_biblioteca"):
            self.combo_orden_biblioteca.setEnabled(habilitado)

        if hasattr(self, "btn_actualizar_biblioteca"):
            self.btn_actualizar_biblioteca.setEnabled(habilitado)

    # ============================================================
    # CIERRE
    # ============================================================

    def closeEvent(self, event):
        self.media_player.stop()
        self.guardar_config_actual()
        event.accept()


def main():
    app = QApplication(sys.argv)

    ruta_icono = obtener_ruta_recurso("assets/audiodrop_icon.ico")
    if os.path.exists(ruta_icono):
        app.setWindowIcon(QIcon(ruta_icono))

    ventana = App()
    ventana.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
