#!/usr/bin/env python3
"""Inference Server — YOLO на GPU, принимает JPEG по HTTP."""

import time
import logging

import cv2
import numpy as np
import typer
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

app_cli = typer.Typer()
api = FastAPI(title="SocksTank Inference Server")

_model = None
_model_path = ""


@api.get("/health")
async def health():
    """Проверка доступности сервера."""
    gpu_name = "CPU"
    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    return {"status": "ok", "gpu": gpu_name, "model": _model_path}


@api.get("/models")
async def list_models():
    """Список доступных моделей."""
    import os

    models = []
    models_dir = "models"
    if os.path.isdir(models_dir):
        for f in os.listdir(models_dir):
            if f.endswith(".pt"):
                models.append(f)
    return {"models": sorted(models)}


@api.post("/infer")
async def infer(request: Request):
    """Инференс: JPEG -> детекции."""
    if _model is None:
        return JSONResponse({"error": "model not loaded"}, status_code=503)

    confidence = float(request.headers.get("X-Confidence", "0.5"))
    jpeg_bytes = await request.body()

    # Декодируем JPEG -> numpy
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"error": "invalid JPEG"}, status_code=400)

    # RGB для YOLO (cv2.imdecode даёт BGR)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    t0 = time.monotonic()
    results = _model(frame_rgb, conf=confidence, verbose=False)
    inference_ms = (time.monotonic() - t0) * 1000

    result = results[0]
    detections = []
    names = result.names
    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int).tolist()
        detections.append(
            {
                "class": names[cls_id],
                "confidence": round(conf, 3),
                "bbox": [x1, y1, x2, y2],
            }
        )

    return {"detections": detections, "inference_ms": round(inference_ms, 1)}


@app_cli.command()
def main(
    model: str | None = typer.Option(None, help="Путь к модели YOLO (если не указан — выбирается автоматически)"),
    host: str = typer.Option("0.0.0.0", help="Хост"),
    port: int = typer.Option(8090, help="Порт"),
):
    """Запуск inference-сервера."""
    import uvicorn
    from ultralytics import YOLO
    from server.config import resolve_model_path

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    global _model, _model_path
    _model_path = resolve_model_path(model, runtime_role="gpu-server")
    log.info("Загрузка модели: %s", _model_path)
    _model = YOLO(_model_path)
    log.info("Модель загружена")

    uvicorn.run(api, host=host, port=port)


if __name__ == "__main__":
    app_cli()
