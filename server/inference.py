"""InferenceRouter — переключение между локальным и удалённым инференсом."""

import os
import time
import logging
import threading

import cv2
import numpy as np
import httpx
import yaml

from server.config import settings

log = logging.getLogger(__name__)


def _load_class_names(model_dir: str) -> dict[int, str]:
    """Загрузить имена классов из metadata.yaml рядом с моделью."""
    meta_path = os.path.join(model_dir, "metadata.yaml")
    if not os.path.exists(meta_path):
        log.warning("metadata.yaml не найден: %s — используем дефолтные имена", meta_path)
        return {0: "sock"}
    with open(meta_path) as f:
        meta = yaml.safe_load(f)
    names = meta.get("names", {0: "sock"})
    # metadata.yaml хранит ключи как int, но на всякий случай
    return {int(k): v for k, v in names.items()}


def _try_load_cpp_detector(model_dir: str, num_threads: int):
    """Попытка загрузить C++ ncnn wrapper. Возвращает (detector, class_names) или (None, None)."""
    try:
        from ncnn_wrapper import NCNNDetector
    except ImportError:
        log.info("C++ ncnn_wrapper не найден — используем ultralytics")
        return None, None

    param_path = os.path.join(model_dir, "model.ncnn.param")
    bin_path = os.path.join(model_dir, "model.ncnn.bin")

    if not os.path.exists(param_path) or not os.path.exists(bin_path):
        log.warning("NCNN файлы модели не найдены в %s", model_dir)
        return None, None

    detector = NCNNDetector()
    if not detector.load(param_path, bin_path, num_threads):
        log.error("Не удалось загрузить C++ ncnn модель из %s", model_dir)
        return None, None

    class_names = _load_class_names(model_dir)
    log.info("C++ ncnn wrapper загружен: %s (%d потоков, классы: %s)", model_dir, num_threads, class_names)
    return detector, class_names


class InferenceRouter:
    """Роутер инференса: local YOLO / C++ ncnn / remote HTTP POST."""

    def __init__(self, model=None, cpp_detector=None, class_names=None):
        self._model = model
        self._cpp_detector = cpp_detector
        self._class_names: dict[int, str] = class_names or {}
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
        """Локальный инференс: C++ ncnn wrapper или ultralytics YOLO."""
        self._error = None

        # C++ ncnn wrapper (приоритет, если доступен)
        if self._cpp_detector is not None:
            return self._infer_cpp(frame, confidence)

        # Fallback: ultralytics YOLO
        return self._infer_ultralytics(frame, confidence)

    def _infer_cpp(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Инференс через C++ ncnn wrapper."""
        self._active_backend = "local:ncnn-cpp"

        # C++ wrapper ожидает RGB uint8 (HWC) — frame уже в RGB от picamera2/mock
        raw_dets = self._cpp_detector.detect(frame, confidence)
        self._inference_ms = self._cpp_detector.last_inference_ms()

        detections = []
        for det in raw_dets:
            cls_id = det["class_id"]
            cls_name = self._class_names.get(cls_id, f"class_{cls_id}")
            bbox = list(det["bbox"])
            detections.append(
                {
                    "class": cls_name,
                    "confidence": round(det["confidence"], 3),
                    "bbox": bbox,
                }
            )
        return detections

    def _infer_ultralytics(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Инференс через ultralytics YOLO."""
        self._active_backend = "local"

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
