#!/usr/bin/env python3
"""Inference server that runs YOLO on a GPU and accepts JPEG over HTTP."""

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
    """Return the server health status."""
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
    """List available models."""
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
    """Run inference for a JPEG request and return detections."""
    if _model is None:
        return JSONResponse({"error": "model not loaded"}, status_code=503)

    confidence = float(request.headers.get("X-Confidence", "0.5"))
    jpeg_bytes = await request.body()

    # Decode JPEG bytes into a NumPy image
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"error": "invalid JPEG"}, status_code=400)

    # Convert to RGB for YOLO (cv2.imdecode returns BGR)
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
    model: str | None = typer.Option(None, help="Path to the YOLO model (auto-selected if omitted)"),
    host: str = typer.Option("0.0.0.0", help="Host"),
    port: int = typer.Option(8090, help="Port"),
):
    """Start the inference server."""
    import uvicorn
    from ultralytics import YOLO
    from server.config import resolve_model_path

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    global _model, _model_path
    _model_path = resolve_model_path(model, runtime_role="gpu-server")
    log.info("Loading model: %s", _model_path)
    _model = YOLO(_model_path)
    log.info("Model loaded")

    uvicorn.run(api, host=host, port=port)


if __name__ == "__main__":
    app_cli()
