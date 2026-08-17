from django.core.management.base import BaseCommand
from ultralytics import YOLO

class Command(BaseCommand):
    help = 'Entrena el modelo YOLOv8 con los datos de Roboflow'

    def handle(self, *args, **kwargs):
        data_path = 'IaFinal0.v1i.yolov8/data.yaml'  # <- cambia esto por la ruta real
        model = YOLO('yolov8n.pt')
        model.train(data=data_path, epochs=500, imgsz=416)
        self.stdout.write(self.style.SUCCESS('Modelo entrenado correctamente.'))