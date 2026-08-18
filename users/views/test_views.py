"""
Vista de prueba del modelo: subir una imagen o video y ver el resultado
de la detección, sin necesidad de tener una cámara conectada.
"""

import os
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .detection import (
    procesar_imagen_temporal,
    procesar_video_temporal,
    reencode_to_h264,
)


@login_required(login_url='login')
def test_modelo(request):

    original_url = None
    resultado_url = None
    es_video = False

    if (
        request.method == 'POST'
        and request.FILES.get('archivo')
    ):

        archivo = request.FILES[
            'archivo'
        ]

        filename = (
            str(uuid.uuid4())
            + '_'
            + archivo.name
        )

        temp_dir = os.path.join(
            settings.MEDIA_ROOT,
            'temp'
        )

        os.makedirs(
            temp_dir,
            exist_ok=True
        )

        temp_path = os.path.join(
            temp_dir,
            filename
        )

        with open(
            temp_path,
            'wb+'
        ) as dest:

            for chunk in archivo.chunks():
                dest.write(chunk)

        if archivo.content_type.startswith(
            'image'
        ):

            procesado_path = (
                procesar_imagen_temporal(
                    temp_path
                )
            )

        elif archivo.content_type.startswith(
            'video'
        ):

            raw = procesar_video_temporal(
                temp_path
            )

            procesado_path = (
                reencode_to_h264(raw)
            )

            es_video = True

        else:

            return render(
                request,
                'users/test_model.html',
                {
                    'error':
                    'Formato no soportado'
                }
            )

        original_url = (
            settings.MEDIA_URL
            + 'temp/'
            + os.path.basename(
                temp_path
            )
        )

        resultado_url = (
            settings.MEDIA_URL
            + 'temp/'
            + os.path.basename(
                procesado_path
            )
        )

    return render(
        request,
        'users/test_model.html',
        {
            'original_url': original_url,
            'resultado_url': resultado_url,
            'es_video': es_video
        }
    )
