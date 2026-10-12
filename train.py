# train.py
"""
Entrenamiento IRIS v2 — dataset unificado (train/valid 85/15 + test propio),

Uso:
    python train.py
"""

from pathlib import Path
from ultralytics import YOLO

DATA_YAML = Path(__file__).resolve().parent / "datasets" / "iris.v2i.yolov26" / "data.yaml"

BASE_MODEL = str(Path(__file__).resolve().parent / "ml_models" / "pretrained" / "yolo26s.pt")

EPOCHS = 2
IMG_SIZE = 960
BATCH = 4
RUN_NAME = "iris_v2_yolo26s_960"

PROJECT = str(Path(__file__).resolve().parent / "training_runs")


def main():
    model = YOLO(BASE_MODEL)
    model.train(
        data=DATA_YAML,
        epochs=80,
        patience=20,
        imgsz=960,
        batch=8,               # small tiene más margen de VRAM que medium; calibrar igual
        workers=6,             # subo de 4 a 6: sin cache, hay más RAM libre y tu CPU tiene 14 núcleos
        cache=False,           # obligatorio: cachear 24,000 imgs a 960px pediría ~66 GB de RAM, imposible con 16 GB
        amp=True,
        save_period=10,
        hsv_h=0.0,             # más crítico aún si el x3 ya varió color/exposición
        flipud=0.0, fliplr=0.5, degrees=5, scale=0.5,
        close_mosaic=10,
        project=PROJECT, name="iris_v3_yolo26s_960",
)
    # Al terminar: copiar manualmente el best.pt resultante a
    # ml_models/weapons_v1/best.pt (Sección 3, no se toca por script).


if __name__ == "__main__":
    main()