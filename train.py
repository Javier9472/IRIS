# train.py
"""
Entrenamiento IRIS v1.0 — Fase 2, sobre el dataset unificado y limpio
generado por datasets/merge_and_clean.py.

Uso:
    python train.py
"""

from pathlib import Path
from ultralytics import YOLO

# train.py — corrige el mismatch, único cambio en este archivo
DATA_YAML = Path(__file__).resolve().parent / "datasets" / "iris.v1i.yolov11" / "data.yaml"

BASE_MODEL = str(Path(__file__).resolve().parent / "ml_models" / "pretrained" / "yolo11s.pt")

EPOCHS = 100
IMG_SIZE = 640  # antes 960
BATCH = -1      # antes 8; AutoBatch calcula el máximo seguro para tu GPU
RUN_NAME = "iris_v1_yolo11s_640"

# train.py — evita que un futuro run vuelva a anidarse en runs/
PROJECT = str(Path(__file__).resolve().parent / "training_runs")

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