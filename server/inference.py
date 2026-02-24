"""InferenceRouter — переключение между локальным и удалённым инференсом."""

import time
import logging
import threading

import cv2
import numpy as np
import httpx

from server.config import settings

log = logging.getLogger(__name__)


class InferenceRouter:
    """Роутер инференса: local YOLO или remote HTTP POST."""

    def __init__(self, model=None):
        self._model = model
        self._mode = settings.inference_mode  # "auto" | "local" | "remote"
        self._remote_url: str | None = None  # "http://host:port"
        self._active_backend = "local"
        self._inference_ms = 0.0
        self._error: str | None = None
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0))

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        if value not in ("auto", "local", "remote"):
            raise ValueError(f"Invalid mode: {value}")
        self._mode = value
        settings.inference_mode = value
        log.info("Inference mode: %s", value)

    @property
    def active_backend(self) -> str:
        return self._active_backend

    @property
    def inference_ms(self) -> float:
        return self._inference_ms

    @property
    def error(self) -> str | None:
        return self._error

    def set_remote_url(self, url: str | None):
        """Установить URL удалённого сервера."""
        with self._lock:
            self._remote_url = url
            if url:
                log.info("Remote inference URL: %s", url)

    def infer(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Выполнить инференс (local или remote)."""
        use_remote = self._should_use_remote()

        if use_remote:
            return self._infer_remote(frame, confidence)
        return self._infer_local(frame, confidence)

    def _should_use_remote(self) -> bool:
        """Определить, использовать ли remote."""
        if self._mode == "local":
            return False
        if self._mode == "remote":
            return True
        # mode == "auto": remote если URL установлен
        return self._remote_url is not None

    def _infer_local(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Локальный YOLO-инференс."""
        self._active_backend = "local"
        self._error = None

        if self._model is None:
            self._inference_ms = 0
            return []

        t0 = time.monotonic()
        results = self._model(frame, conf=confidence, verbose=False)
        self._inference_ms = (time.monotonic() - t0) * 1000

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
        return detections

    def _infer_remote(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Удалённый инференс через HTTP POST."""
        if not self._remote_url:
            self._error = "No remote URL"
            if self._mode == "auto":
                return self._infer_local(frame, confidence)
            return []

        try:
            # Кодируем frame в JPEG (frame приходит в RGB)
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            _, jpeg = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])

            t0 = time.monotonic()
            resp = self._client.post(
                f"{self._remote_url}/infer",
                content=jpeg.tobytes(),
                headers={
                    "Content-Type": "image/jpeg",
                    "X-Confidence": str(confidence),
                },
            )
            total_ms = (time.monotonic() - t0) * 1000

            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            self._inference_ms = data.get("inference_ms", total_ms)
            self._active_backend = f"remote:{self._remote_url.split('//')[1]}"
            self._error = None
            return data.get("detections", [])

        except Exception as e:
            log.warning("Remote inference error: %s", e)
            self._error = str(e)
            # Auto-режим: fallback на local
            if self._mode == "auto":
                log.info("Fallback на локальный инференс")
                return self._infer_local(frame, confidence)
            return []

    def close(self):
        """Закрыть HTTP-клиент."""
        self._client.close()
