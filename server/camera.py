"""CameraManager — захват кадров с камеры, YOLO-детекция, JPEG-буфер."""

import threading
import time
import logging

import cv2
import numpy as np

from server.config import settings

log = logging.getLogger(__name__)


class CameraManager:
    """Фоновый захват кадров + YOLO-инференс → JPEG для MJPEG-стрима."""

    def __init__(self, camera, model=None):
        self._camera = camera
        self._model = model
        self._lock = threading.Lock()
        self._frame_jpeg: bytes | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._fps = 0.0
        self._detections: list[dict] = []

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def detections(self) -> list[dict]:
        with self._lock:
            return list(self._detections)

    def start(self):
        """Запускает камеру и фоновый поток обработки."""
        self._camera.start()
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        log.info("CameraManager запущен")

    def stop(self):
        """Останавливает захват."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        try:
            self._camera.stop()
        except Exception:
            pass
        log.info("CameraManager остановлен")

    def get_jpeg(self) -> bytes | None:
        """Возвращает последний JPEG-кадр."""
        with self._lock:
            return self._frame_jpeg

    def _capture_loop(self):
        """Основной цикл: захват → YOLO → рисование bbox → JPEG."""
        while self._running:
            t0 = time.monotonic()
            try:
                frame = self._camera.capture_array()
                detections = self._run_yolo(frame)
                frame = self._draw_detections(frame, detections)
                # picamera2 и mock дают RGB, imencode ожидает BGR
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                _, jpeg = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])

                with self._lock:
                    self._frame_jpeg = jpeg.tobytes()
                    self._detections = detections

                elapsed = time.monotonic() - t0
                self._fps = 1.0 / max(elapsed, 0.001)

                # Ограничение FPS
                target_delay = 1.0 / settings.camera_fps
                sleep_time = target_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                log.error("Ошибка в capture_loop: %s", e)
                time.sleep(0.5)

    def _run_yolo(self, frame: np.ndarray) -> list[dict]:
        """Запускает YOLO-инференс и возвращает список детекций."""
        if self._model is None:
            return []

        results = self._model(frame, conf=settings.confidence, verbose=False)
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

    def _draw_detections(self, frame: np.ndarray, detections: list[dict]) -> np.ndarray:
        """Рисует bounding boxes и подписи на кадре."""
        color = (0, 0, 255)  # BGR: красный
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            label = f'{det["class"]} {det["confidence"]:.2f}'
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Фон для текста
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # FPS в углу
        cv2.putText(frame, f"FPS: {self._fps:.1f}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return frame
