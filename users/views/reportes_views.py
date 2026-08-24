# users/views/reportes_views.py
"""
Fase 7 — Incidentes y reportes PDF.

Gestión del ciclo de vida de Incidente (apertura, acumulación de
Alerta/AlertaFacial, cierre por ventana de inactividad y generación
del PDF vía WeasyPrint), más la vista de galería. Se engancha desde
detection.py como paso adicional dentro de detect_objects(), igual
que facial_views en Fase 6.
"""
import threading
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from ..models import AlertaFacial, Incidente

logger = logging.getLogger(__name__)


def gestionar_incidente(camara_id, alertas_creadas):
    ahora = timezone.now()

    limite_reciente = ahora - timedelta(seconds=settings.INCIDENTE_TIMEOUT_SECONDS)

    facial_pendientes = AlertaFacial.objects.filter(
        camara_id=camara_id,
        incidentes__isnull=True,
        fecha_deteccion__gte=limite_reciente
    )

    if not alertas_creadas and not facial_pendientes.exists():
        return

    incidente = Incidente.objects.filter(
        camara_id=camara_id,
        hora_fin__isnull=True
    ).first()

    if incidente is None:
        incidente = Incidente.objects.create(
            camara_id=camara_id,
            ultima_deteccion=ahora
        )

    if alertas_creadas:
        incidente.alertas.add(*alertas_creadas)

    if facial_pendientes.exists():
        incidente.alertas_faciales.add(*facial_pendientes)

    incidente.ultima_deteccion = ahora
    incidente.recalcular_tipo()
    incidente.save()


def cerrar_incidentes_vencidos(camara_id):
    limite = timezone.now() - timedelta(seconds=settings.INCIDENTE_TIMEOUT_SECONDS)

    vencidos = Incidente.objects.filter(
        camara_id=camara_id,
        hora_fin__isnull=True,
        ultima_deteccion__lt=limite
    )

    for incidente in vencidos:
        try:
            generar_pdf_incidente(incidente)
        except Exception:
            logger.exception(
                f"Incidente {incidente.id}: fallo generando el PDF, se reintentará en el próximo ciclo"
            )
            continue

        incidente.hora_fin = incidente.ultima_deteccion
        incidente.save(update_fields=['hora_fin'])


def cerrar_incidente_por_desconexion(camara_id):
    abiertos = Incidente.objects.filter(
        camara_id=camara_id,
        hora_fin__isnull=True
    )

    for incidente in abiertos:
        try:
            generar_pdf_incidente(incidente)
        except Exception:
            logger.exception(
                f"Incidente {incidente.id}: fallo generando el PDF al desconectar, se reintentará en el próximo ciclo"
            )
            continue

        incidente.hora_fin = incidente.ultima_deteccion
        incidente.save(update_fields=['hora_fin'])


def generar_pdf_incidente(incidente):
    alertas = [
        {'obj': a, 'imagen_uri': Path(a.imagen.path).as_uri() if a.imagen else None}
        for a in incidente.alertas.order_by('fecha_deteccion')
    ]
    alertas_faciales = [
        {'obj': af, 'imagen_uri': Path(af.imagen.path).as_uri() if af.imagen else None}
        for af in incidente.alertas_faciales.order_by('fecha_deteccion')
    ]

    # Logo del reporte: mismo activo que usa el dashboard (static/img/),
    # resuelto por ruta absoluta (no por STATIC_URL, WeasyPrint no corre
    # bajo el servidor Django). Ausente en disco -> no rompe el PDF.
    logo_path = Path(settings.BASE_DIR) / 'static' / 'img' / 'logo.png'
    logo_uri = logo_path.as_uri() if logo_path.exists() else None

    html_string = render_to_string('users/reporte_incidente.html', {
        'incidente': incidente,
        'alertas': alertas,
        'alertas_faciales': alertas_faciales,
        'logo_uri': logo_uri,
        'ubicacion': settings.INCIDENTE_UBICACION_FIJA,
        'generado_en': timezone.now(),
    })

    pdf_bytes = HTML(string=html_string).write_pdf()

    filename = (
        f"incidente_{incidente.id}_"
        f"{incidente.hora_inicio.strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    incidente.pdf.save(filename, ContentFile(pdf_bytes), save=True)

    logger.info(
        f"Incidente {incidente.id}: PDF generado "
        f"(tipo={incidente.tipo}, cámara={incidente.camara_id})"
    )


@login_required
def reportes_view(request):
    incidentes = Incidente.objects.filter(
        hora_fin__isnull=False
    ).select_related('camara').order_by('-hora_inicio')

    return render(request, 'users/reportes.html', {'incidentes': incidentes})