"""CameraManager for capture, YOLO detection, and JPEG buffering."""

import threading
import time
import logging

import cv2
import numpy as np

from server.config import settings

log = logging.getLogger(__name__)


class CameraManager:
    """Background frame capture plus inference for MJPEG streaming."""

    def __init__(self, camera, inference_router=None):
        self._camera = camera
        self._inference = inference_router
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

    @property
    def inference_ms(self) -> float:
        return self._inference.inference_ms if self._inference else 0

    @property
    def inference_backend(self) -> str:
        return self._inference.active_backend if self._inference else "local"

    @property
    def inference_error(self) -> str | None:
        return self._inference.error if self._inference else None

    def start(self):
        """Start the camera and the background processing thread."""
        self._camera.start()
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        log.info("CameraManager started")

    def stop(self):
        """Stop frame capture."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        try:
            self._camera.stop()
        except Exception:
            pass
        log.info("CameraManager stopped")

    def get_jpeg(self) -> bytes | None:
        """Return the latest JPEG frame."""
        with self._lock:
            return self._frame_jpeg

    def _capture_loop(self):
        """Main loop: capture, infer, draw detections, then encode as JPEG."""
        while self._running:
            t0 = time.monotonic()
            try:
                frame = self._camera.capture_array()
                detections = self._run_yolo(frame)
                frame = self._draw_detections(frame, detections)
                # picamera2 and the mock camera return RGB; imencode expects BGR
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                _, jpeg = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])

                with self._lock:
                    self._frame_jpeg = jpeg.tobytes()
                    self._detections = detections

                elapsed = time.monotonic() - t0
                self._fps = 1.0 / max(elapsed, 0.001)

                # Enforce the configured FPS ceiling
                target_delay = 1.0 / settings.camera_fps
                sleep_time = target_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                log.error("capture_loop failed: %s", e)
                time.sleep(0.5)

    def _run_yolo(self, frame: np.ndarray) -> list[dict]:
        """Run inference and return the resulting detections."""
        if self._inference is None:
            return []
        return self._inference.infer(frame, settings.confidence)

    def _draw_detections(self, frame: np.ndarray, detections: list[dict]) -> np.ndarray:
        """Draw bounding boxes and labels onto the frame."""
        color = (0, 0, 255)  # BGR: red
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            label = f'{det["class"]} {det["confidence"]:.2f}'
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Draw a solid background for the label text
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Render FPS in the corner
        cv2.putText(frame, f"FPS: {self._fps:.1f}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return frame
