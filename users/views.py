from datetime import datetime
from io import BytesIO
import tempfile
import uuid
import time
import cv2
import os
import subprocess

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import StreamingHttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings

from .forms import (
    CustomUserCreationForm,
    CameraForm,
    CameraSettingsForm
)

from .models import Camera, CameraImage, Alerta

from ultralytics import YOLO


# ============================================================
# MODELO YOLO
# ============================================================

model = YOLO("runs/detect/train27/weights/best.pt")

DEVICE = "cpu"

last_capture_times = {}


# ============================================================
# REGISTRO
# ============================================================

def register_view(request):

    # Si ya está conectado, vuelve al home
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        form = CustomUserCreationForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Cuenta creada correctamente. Ahora inicia sesión.'
            )

            # IMPORTANTE:
            # NO hacemos login automático.
            return redirect('login')

        messages.error(
            request,
            'Verifica los datos ingresados.'
        )

    else:

        form = CustomUserCreationForm()

    return render(
        request,
        'users/register.html',
        {
            'form': form
        }
    )


# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            return redirect('home')

        messages.error(
            request,
            'Usuario o contraseña incorrectos.'
        )

    return render(
        request,
        'users/login.html'
    )


# ============================================================
# LOGOUT
# ============================================================

@login_required(login_url='login')
def logout_view(request):

    logout(request)

    return redirect('login')


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
# DETECCIÓN
# ============================================================

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

            success, buffer = cv2.imencode(
                '.jpg',
                frame
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

    # Cámara local del PC
    if str(camara_ip).strip() == '0':

        fuente = 0

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

    print(
        'Fuente de cámara:',
        fuente
    )

    cap = cv2.VideoCapture(
        fuente
    )

    if not cap.isOpened():

        print(
            'No se pudo abrir la cámara:',
            fuente
        )

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
# TEST DEL MODELO
# ============================================================

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