# users/views/facial_views.py — módulo nuevo
"""
Pipeline de reconocimiento facial de personas buscadas (Fase 6).

Módulo hermano de detection.py: no modifica generar_stream() ni el
motor de detección de armas. detect_objects() lo invoca por frame como
paso opcional (ver try/except en detection.py).
"""

import logging
from datetime import datetime

import cv2
import numpy as np
import time

from django.conf import settings
from django.core.files.base import ContentFile

from ..models import AlertaFacial, PersonaBuscada

logger = logging.getLogger(__name__)

_face_app = None
last_facial_capture_times = {}

def _get_face_app():
    # Import diferido: si insightface/torch fallan (no instalado, sin
    # drivers de GPU), el fallo ocurre acá adentro del try/except del
    # caller, no al importar este módulo desde detection.py.
    global _face_app
    if _face_app is None:
        import torch
        from insightface.app import FaceAnalysis

        ctx_id = 0 if torch.cuda.is_available() else -1
        _face_app = FaceAnalysis(name='buffalo_l')
        _face_app.prepare(ctx_id=ctx_id)
    return _face_app


def _similitud_coseno(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def precalcular_embedding(persona: PersonaBuscada):
    """
    Calcula y guarda el embedding ArcFace de una PersonaBuscada a partir
    de su foto_referencia. Se invoca una sola vez por persona (alta
    manual vía shell), no en cada frame del stream.
    """
    img = cv2.imread(persona.foto_referencia.path)
    rostros = _get_face_app().get(img)

    if not rostros:
        raise ValueError(
            f"No se detectó ningún rostro en foto_referencia de '{persona.nombre}'"
        )

    persona.embedding = rostros[0].normed_embedding.astype(np.float32).tobytes()
    persona.save(update_fields=['embedding'])


def procesar_frame_facial(frame, camara_id, detecciones_arma, alertas_creadas=None):
    """
    Compara rostros del frame contra PersonaBuscada activas por similitud
    coseno; registra AlertaFacial por cada match sobre
    settings.FACIAL_SIMILITUD_MINIMA, correlacionando con el arma de
    mayor confianza detectada en el mismo frame (y la Alerta persistida,
    si la hubo).
    """
    personas = list(
        PersonaBuscada.objects.filter(activo=True).exclude(embedding__isnull=True)
    )

    if not personas:
        return

    rostros = _get_face_app().get(frame)

    if not rostros:
        return

    umbral = settings.FACIAL_SIMILITUD_MINIMA
    arma_top = max(detecciones_arma, key=lambda d: d['confianza'], default=None)
    alerta_arma = alertas_creadas[0] if alertas_creadas else None

    # users/views/facial_views.py — reemplaza el cuerpo del for rostro in rostros
    for rostro in rostros:

        mejor_persona = None
        mejor_similitud = 0.0

        for persona in personas:
            similitud = _similitud_coseno(rostro.normed_embedding, persona.get_embedding())
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_persona = persona

        if mejor_persona is None or mejor_similitud < umbral:
            continue

        cooldown_key = (camara_id, mejor_persona.id)
        current_time = time.time()
        last_time = last_facial_capture_times.get(cooldown_key, 0)

        if current_time - last_time < settings.FACIAL_COOLDOWN_SECONDS:
            continue

        last_facial_capture_times[cooldown_key] = current_time

        success, buffer = cv2.imencode(
            '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, settings.ALERTA_JPEG_QUALITY]
        )

        if not success:
            continue

        alerta_facial = AlertaFacial(
            persona=mejor_persona,
            camara_id=camara_id,
            alerta_arma=alerta_arma,
            confianza_facial=mejor_similitud,
            confianza_arma=arma_top['confianza'] if arma_top else None,
        )

        filename = f"facial_{mejor_persona.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        alerta_facial.imagen.save(filename, ContentFile(buffer.tobytes()), save=True)

        logger.warning(
            f"Cámara {camara_id}: match facial '{mejor_persona.nombre}' "
            f"(similitud={mejor_similitud:.2f})"
            + (f", arma correlacionada (confianza={arma_top['confianza']:.2f})" if arma_top else "")
        )