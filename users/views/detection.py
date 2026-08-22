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

import cv2
import torch
from ultralytics import YOLO

from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404

from ..models import Camera, Alerta

logger = logging.getLogger(__name__)


# ============================================================
# MODELO YOLO
# ============================================================

# Ruta absoluta a partir de BASE_DIR: no depende de la máquina ni de
# desde dónde se ejecute manage.py. Apunta al peso versionado en
# ml_models/ (Sección 3 de AI_CONTEXT.md), no a un run local de
# training_runs/ (gitignored, no reproducible en otro entorno).
MODEL_PATH = os.path.join(
    settings.BASE_DIR, 'ml_models', 'weapons_v1', 'best.pt'
)

model = YOLO(MODEL_PATH)

model = YOLO(MODEL_PATH)

# Antes estaba fijo en "cpu". Si hay GPU disponible (CUDA), la usamos:
# la inferencia por frame es varias veces más rápida, lo que importa
# mucho en un stream en vivo.
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

logger.info(
    f"IRIS: modelo cargado desde '{MODEL_PATH}', usando dispositivo '{DEVICE}'"
)

last_capture_times = {}


# ============================================================
# DETECCIÓN
# ============================================================

# users/views/detection.py — reemplaza la función detect_objects()
def detect_objects(
    frame,
    camara_id
):

    camara = get_object_or_404(
        Camera,
        id=camara_id
    )

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

            # Compresión JPEG de la política de retención (Sección 9).
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

                last_capture_times[
                    camara_id
                ] = current_time

    return result.plot()


# ============================================================
# STREAM DE CÁMARA
# ============================================================

def generar_stream(
    camara_ip,
    camara_id
):

# Cámara local del PC o múltiples USB
    if str(camara_ip).strip().isdigit():

        fuente = int(str(camara_ip).strip())

    # Si ya es una URL
    elif (
        str(camara_ip).startswith(
            'rtsp://'
        )
        or str(camara_ip).startswith(
            'http://'
        )
        or str(camara_ip).startswith(
            'https://'
        )
    ):

        fuente = camara_ip

    # Cámara IP tipo celular
    else:

        fuente = (
            'http://'
            + str(camara_ip)
            + ':8080/video'
        )

    logger.info(f"Cámara {camara_id}: abriendo fuente '{fuente}'")

    cap = cv2.VideoCapture(
        fuente
    )

    if not cap.isOpened():

        logger.error(f"Cámara {camara_id}: no se pudo abrir la fuente '{fuente}'")

        return

    try:

        while True:

            success, frame = cap.read()

            if not success:
                break

            frame = detect_objects(
                frame,
                camara_id
            )

            success, buffer = cv2.imencode(
                '.jpg',
                frame
            )

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
