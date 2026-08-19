# train.py
"""
Entrenamiento IRIS v1.0 — Fase 2, sobre el dataset unificado y limpio
generado por datasets/merge_and_clean.py.

Uso:
    python train.py
"""

from pathlib import Path
from ultralytics import YOLO

DATA_YAML = Path(__file__).resolve().parent / "datasets" / "iris_v1" / "data.yaml"

BASE_MODEL = "yolo11s.pt"  # YOLO11 (antes yolov8s.pt); "yolo11m.pt" si la
                           # GPU/VRAM lo permite y se busca más precisión

EPOCHS = 100
IMG_SIZE = 960
BATCH = 8
PROJECT = "training_runs"
RUN_NAME = "iris_v1_yolo11s_960"


def main():
    model = YOLO(BASE_MODEL)
    model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        project=PROJECT,
        name=RUN_NAME,
        device=0,  # GPU 0 (CUDA); usar "cpu" si no hay GPU disponible
        patience=20,
        val=True,
    )
    # Al terminar: copiar manualmente el best.pt resultante a
    # ml_models/weapons_v1/best.pt (Sección 3, no se toca por script).


if __name__ == "__main__":
    main()  