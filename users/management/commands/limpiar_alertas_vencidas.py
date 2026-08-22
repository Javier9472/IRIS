# users/management/commands/limpiar_alertas_vencidas.py (archivo nuevo)
"""
Borra alertas no relevantes más viejas que ALERTA_RETENTION_DAYS
(AI_CONTEXT.md Sección 9). Pensado para cron/Task Scheduler, no
como señal en Alerta.save().
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import Alerta

logger = logging.getLogger('users')


class Command(BaseCommand):
    help = "Borra alertas no relevantes vencidas según ALERTA_RETENTION_DAYS."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra cuántas se borrarían sin borrar nada.',
        )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=settings.ALERTA_RETENTION_DAYS)

        vencidas = Alerta.objects.filter(
            relevante=False,
            fecha_deteccion__lt=limite,
        )

        if options['dry_run']:
            self.stdout.write(f"[dry-run] {vencidas.count()} alerta(s) vencida(s).")
            return

        borradas = 0

        for alerta in vencidas.iterator():
            alerta.imagen.delete(save=False)
            alerta.delete()
            borradas += 1

        logger.info(
            f"IRIS: retención — {borradas} alerta(s) vencida(s) borrada(s) "
            f"(TTL={settings.ALERTA_RETENTION_DAYS}d)."
        )
        self.stdout.write(f"{borradas} alerta(s) borrada(s).")