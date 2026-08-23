"""
Vistas de gestión de cámaras: alta, baja, panel en vivo, stream y alertas.
"""

import io

import qrcode
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.urls import reverse

from ..forms import CameraForm, CameraSettingsForm
from ..models import Camera, Alerta

from .detection import generar_stream


# ============================================================
# HOME
# ============================================================

@login_required(login_url='login')
def home_view(request):

    camaras = Camera.objects.filter(
        usuario=request.user
    ).order_by('nombre')

    return render(
        request,
        'users/home.html',
        {
            'camaras': camaras
        }
    )


# ============================================================
# QR DE ACCESO REMOTO
# ============================================================

@login_required(login_url='login')
def qr_code_view(request):

    if settings.TUNNEL_DOMAIN:
        url = f'https://{settings.TUNNEL_DOMAIN}{reverse("login_page")}'
    else:
        url = request.build_absolute_uri(reverse('login_page'))

    imagen = qrcode.make(url)

    buffer = io.BytesIO()
    imagen.save(buffer, format='PNG')

    return HttpResponse(
        buffer.getvalue(),
        content_type='image/png'
    )


# ============================================================
# NUEVA CÁMARA
# ============================================================

@login_required(login_url='login')
def nueva_camara_view(request):

    if request.method == 'POST':

        form = CameraForm(
            request.POST
        )

        if form.is_valid():

            camara = form.save(
                commit=False
            )

            camara.usuario = request.user

            camara.save()

            return redirect('home')

    else:

        form = CameraForm()

    return render(
        request,
        'users/nueva_camara.html',
        {
            'form': form
        }
    )


# ============================================================
# ELIMINAR CÁMARA
# ============================================================

@login_required(login_url='login')
def eliminar_camara_view(
    request,
    camara_id
):

    camara = get_object_or_404(
        Camera,
        id=camara_id,
        usuario=request.user
    )

    camara.delete()

    return redirect('home')


# ============================================================
# CÁMARA / GALERÍA EN VIVO
# ============================================================

@login_required(login_url='login')
def galeria_camara_view(
    request,
    camara_id
):

    camara = get_object_or_404(
        Camera,
        id=camara_id,
        usuario=request.user
    )

    alertas = Alerta.objects.filter(
        camara=camara
    ).order_by(
        '-fecha_deteccion'
    )[:10]

    if request.method == 'POST':

        form = CameraSettingsForm(
            request.POST,
            instance=camara
        )

        if form.is_valid():

            form.save()

            return redirect(
                'galeria_camara',
                camara_id=camara.id
            )

    else:

        form = CameraSettingsForm(
            instance=camara
        )

    return render(
        request,
        'users/cam.html',
        {
            'camara': camara,
            'alertas': alertas,
            'form': form
        }
    )


# ============================================================
# VIDEO FEED
# ============================================================

@login_required(login_url='login')
def video_feed(
    request,
    camara_id
):

    camara = get_object_or_404(
        Camera,
        id=camara_id,
        usuario=request.user
    )

    return StreamingHttpResponse(
        generar_stream(
            camara.ip,
            camara.id
        ),
        content_type=(
            'multipart/x-mixed-replace; '
            'boundary=frame'
        )
    )


# ============================================================
# ALERTA
# ============================================================

@login_required(login_url='login')
def obtener_alerta(
    request,
    camara_id
):

    camara = get_object_or_404(
        Camera,
        id=camara_id,
        usuario=request.user
    )

    alerta = (
        Alerta.objects.filter(
            camara=camara
        )
        .order_by(
            '-fecha_deteccion'
        )
        .first()
    )

    if alerta:
        mensaje = alerta.tipo_deteccion
    else:
        mensaje = 'Sin detecciones'

    return JsonResponse(
        {
            'alerta': mensaje
        }
    )


# ============================================================
# GALERÍA DE IMÁGENES DETECTADAS
# ============================================================

@login_required(login_url='login')
def ver_alertas(
    request,
    camara_id
):

    camara = get_object_or_404(
        Camera,
        id=camara_id,
        usuario=request.user
    )

    alertas = Alerta.objects.filter(
        camara=camara
    ).order_by(
        '-fecha_deteccion'
    )

    return render(
        request,
        'users/alertas.html',
        {
            'camara': camara,
            'alertas': alertas
        }
    )