import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from ultralytics import YOLO


class Command(BaseCommand):
    help = 'Entrena el modelo YOLOv8 con los datos de Roboflow'

    def handle(self, *args, **kwargs):
        # Antes: 'IaFinal0.v1i.yolov8/data.yaml' (ruta relativa a mano).
        # Ahora el dataset vive en datasets/, ruta absoluta desde BASE_DIR.
        data_path = str(
            settings.BASE_DIR / 'datasets' / 'IaFinal0.v1i.yolov8' / 'data.yaml'
        )

        # 'yolov8n.pt' ya no está en la raíz del proyecto: si no lo
        # encuentra localmente, ultralytics lo descarga solo la primera vez.
        model = YOLO('yolov8n.pt')

        # project/name fijos para que los entrenamientos futuros caigan
        # siempre en training_runs/, en vez de crear un runs/ nuevo
        # cada vez en la raíz del proyecto.
        results = model.train(
            data=data_path,
            epochs=500,
            imgsz=416,
            project=str(settings.BASE_DIR / 'training_runs'),
            name='weapons_v1',
        )

        # Copiamos el mejor checkpoint a la ruta fija que usa la app
        # en producción (users/views/detection.py -> MODEL_PATH),
        # para no tener que tocar código cada vez que reentrenas.
        best_weights = results.save_dir / 'weights' / 'best.pt'
        destino = settings.BASE_DIR / 'ml_models' / 'weapons_v1' / 'best.pt'
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(best_weights, destino)

        self.stdout.write(
            self.style.SUCCESS(
                f'Modelo entrenado correctamente. Pesos copiados a {destino}'
            )
        )