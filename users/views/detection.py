# users/views/detection.py
"""
Motor de visión de Iris.

Carga del modelo YOLO, detección por frame, streaming de cámaras y
procesamiento de imágenes/video de prueba. Antes esto vivía mezclado
con las vistas HTTP dentro de un único views.py; ahora es un módulo
aparte, sin decoradores de Django, para que sea fácil de reutilizar
o probar por separado (y más adelante, sumar reconocimiento facial
o patrones de robo como módulos hermanos de este).
"""

from datetime import datetime
import logging
import os
import subprocess
import tempfile
import time
import threading

import cv2
import torch
from ultralytics import YOLO

from . import reportes_views
from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from . import facial_views
from ..models import Camera, Alerta

logger = logging.getLogger(__name__)


# ============================================================
# MODELO YOLO
# ============================================================

MODEL_PATH = os.path.join(
    settings.BASE_DIR, 'ml_models', 'weapons_v1', 'best.pt'
)

model = YOLO(MODEL_PATH)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

logger.info(
    f"IRIS: modelo cargado desde '{MODEL_PATH}', usando dispositivo '{DEVICE}'"
)

try:
    facial_views._get_face_app()
    logger.info("IRIS: pipeline facial (InsightFace) precargado")
except Exception:
    logger.exception(
        "IRIS: no se pudo precargar el pipeline facial, se reintentará en el primer frame"
    )

last_capture_times = {}
model_lock = threading.Lock()
last_facial_frame_times = {}
last_incidente_check_times = {}

_capturas_activas = {}
_capturas_lock = threading.Lock()

_camera_cache = {}
_camera_cache_lock = threading.Lock()
CAMERA_CACHE_TTL = 5


def _get_camara_cached(camara_id):
    now = time.time()
    with _camera_cache_lock:
        entry = _camera_cache.get(camara_id)
        if entry and (now - entry[1] < CAMERA_CACHE_TTL):
            return entry[0]
    camara = get_object_or_404(Camera, id=camara_id)
    with _camera_cache_lock:
        _camera_cache[camara_id] = (camara, now)
    return camara

# ============================================================
# DETECCIÓN
# ============================================================

def detect_objects(
    frame,
    camara_id
):

    camara = _get_camara_cached(camara_id)

    with model_lock:
        results = model(
            frame,
            device=DEVICE
        )

    result = results[0]

    boxes = result.boxes

    capture_delay = (
        camara.intervalo_captura
    )

    nombres_detectados = []
    detecciones_arma = []

    if boxes is not None and len(boxes) > 0:

        boxes = boxes[
            boxes.conf >= camara.certeza_minima
        ]

        result.boxes = boxes

        for box in boxes:

            class_id = int(
                box.cls[0].item()
            )

            class_name = model.names[
                class_id
            ]

            nombres_detectados.append(
                class_name
            )

            detecciones_arma.append({
                'tipo': class_name,
                'confianza': float(box.conf[0].item())
            })

    alertas_creadas = []

    if nombres_detectados:

        current_time = time.time()

        last_time = last_capture_times.get(
            camara_id,
            0
        )

        if (
            current_time - last_time
            >= capture_delay
        ):

            success, buffer = cv2.imencode(
                '.jpg',
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, settings.ALERTA_JPEG_QUALITY]
            )

            if success:

                image_data = buffer.tobytes()

                for deteccion in set(
                    nombres_detectados
                ):

                    alerta = Alerta(
                        camara_id=camara_id,
                        tipo_deteccion=deteccion
                    )

                    filename = (
                        f"{deteccion}_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    )

                    alerta.imagen.save(
                        filename,
                        ContentFile(
                            image_data
                        ),
                        save=True
                    )

                    alertas_creadas.append(alerta)

                last_capture_times[
                    camara_id
                ] = current_time

    current_time_facial = time.time()
    last_facial = last_facial_frame_times.get(camara_id, 0)

    if current_time_facial - last_facial >= settings.FACIAL_FRAME_INTERVAL_SECONDS:
        last_facial_frame_times[camara_id] = current_time_facial
        try:
            with model_lock:
                facial_views.procesar_frame_facial(
                    frame,
                    camara_id,
                    detecciones_arma,
                    alertas_creadas
                )
        except Exception:
            logger.exception(
                f"Cámara {camara_id}: fallo en pipeline facial, se omite este frame"
            )

    current_time_incidente = time.time()
    last_incidente_check = last_incidente_check_times.get(camara_id, 0)

    if alertas_creadas or (
        current_time_incidente - last_incidente_check
        >= settings.INCIDENTE_CHECK_INTERVAL_SECONDS
    ):
        last_incidente_check_times[camara_id] = current_time_incidente
        try:
            reportes_views.gestionar_incidente(camara_id, alertas_creadas)
            reportes_views.cerrar_incidentes_vencidos(camara_id)
        except Exception:
            logger.exception(
                f"Cámara {camara_id}: fallo en gestión de incidentes, se omite este frame"
            )

    return result.plot()

# ============================================================
# STREAM DE CÁMARA
# ============================================================

def generar_stream(camara_ip, camara_id):

    if str(camara_ip).strip().isdigit():
        fuente = int(str(camara_ip).strip())
    elif (
        str(camara_ip).startswith('rtsp://')
        or str(camara_ip).startswith('http://')
        or str(camara_ip).startswith('https://')
    ):
        fuente = camara_ip
    else:
        fuente = 'http://' + str(camara_ip) + ':8080/video'

    with _capturas_lock:
        anterior = _capturas_activas.get(camara_id)
        if anterior is not None:
            logger.warning(
                f"Cámara {camara_id}: había una captura previa sin liberar, se cierra antes de abrir la nueva"
            )
            anterior.release()

        logger.info(f"Cámara {camara_id}: abriendo fuente '{fuente}'")
        # Backend explícito para fuentes locales: en Windows, MSMF (default
        # de OpenCV) tarda varios segundos en abrir un índice de cámara —
        # causa directa del lag reportado al abrir. DSHOW abre casi
        # instantáneo. Fuentes IP/URL usan el backend default (DSHOW no
        # aplica a streams de red).
        if isinstance(fuente, int):
            cap = cv2.VideoCapture(fuente, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(fuente)
        _capturas_activas[camara_id] = cap

    if not cap.isOpened():
        logger.error(f"Cámara {camara_id}: no se pudo abrir la fuente '{fuente}'")
        with _capturas_lock:
            if _capturas_activas.get(camara_id) is cap:
                del _capturas_activas[camara_id]
        return

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            frame = detect_objects(frame, camara_id)

            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                continue

            frame_bytes = buffer.tobytes()

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                + frame_bytes
                + b'\r\n'
            )
    finally:
        cap.release()
        with _capturas_lock:
            if _capturas_activas.get(camara_id) is cap:
                del _capturas_activas[camara_id]
        try:
            reportes_views.cerrar_incidente_por_desconexion(camara_id)
        except Exception:
            logger.exception(
                f"Cámara {camara_id}: fallo cerrando incidentes al desconectar el stream"
            )

# ============================================================
# PROCESAR IMAGEN TEMPORAL
# ============================================================

def procesar_imagen_temporal(path):

    img = cv2.imread(path)

    results = model(
        img,
        device=DEVICE
    )

    result = results[0].plot()

    temp_dir = os.path.join(
        settings.MEDIA_ROOT,
        'temp'
    )

    os.makedirs(
        temp_dir,
        exist_ok=True
    )

    temp_file = tempfile.NamedTemporaryFile(
        suffix='.jpg',
        delete=False,
        dir=temp_dir
    )

    cv2.imwrite(
        temp_file.name,
        result
    )

    return temp_file.name


# ============================================================
# PROCESAR VIDEO TEMPORAL
# ============================================================

def procesar_video_temporal(path):

    cap = cv2.VideoCapture(path)

    fourcc = cv2.VideoWriter_fourcc(
        *'mp4v'
    )

    temp_dir = os.path.join(
        settings.MEDIA_ROOT,
        'temp'
    )

    os.makedirs(
        temp_dir,
        exist_ok=True
    )

    out_path = tempfile.NamedTemporaryFile(
        suffix='.mp4',
        delete=False,
        dir=temp_dir
    ).name

    fps = cap.get(
        cv2.CAP_PROP_FPS
    )

    width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    if fps <= 0:
        fps = 25

    out = cv2.VideoWriter(
        out_path,
        fourcc,
        fps,
        (width, height)
    )

    try:

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            results = model(
                frame,
                device=DEVICE
            )

            processed = results[0].plot()

            out.write(
                processed
            )

    finally:

        cap.release()
        out.release()

    return out_path


# ============================================================
# REENCODE H264
# ============================================================

def reencode_to_h264(input_path):

    output_path = input_path.replace(
        '.mp4',
        '_h264.mp4'
    )

    subprocess.run(
        [
            'ffmpeg',
            '-y',
            '-i',
            input_path,
            '-vcodec',
            'libx264',
            '-preset',
            'fast',
            '-crf',
            '23',
            output_path
        ],
        check=True
    )

    return output_path