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

    AI_CENTER_TOLERANCE = 0.12
    AI_CLOSE_ENOUGH_RATIO = 0.12
    AI_FORWARD_SPEED = 1500
    AI_TURN_SPEED = 1100
    AI_SEARCH_SPEED = 900
    AI_GRIP_OPEN = 90
    AI_GRIP_CLOSED = 150
    AI_LIFT_UP = 140
    AI_LIFT_DOWN = 105

    def __init__(self, camera, inference_router=None):
        self._camera = camera
        self._inference = inference_router
        self._mock_camera = bool(getattr(camera, "is_mock", False))
        self._hardware = None
        self._place_store = None
        self._lock = threading.Lock()
        self._frame_jpeg: bytes | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._fps = 0.0
        self._detections: list[dict] = []
        self._ai_state = "idle"
        self._ai_has_payload = False
        self._ai_stage = "search"
        self._ai_stage_until = 0.0
        self._ai_stage_started = False
        self._ai_search_dir = 1
        self._ai_next_search_update = 0.0
        self._last_motor: tuple[int, int] | None = None

    @property
    def camera_source(self) -> str:
        return str(getattr(self._camera, "camera_source", "mock" if self._mock_camera else "camera"))

    @property
    def ai_state(self) -> str:
        return self._ai_state

    @property
    def ai_target_label(self) -> str | None:
        if self._place_store is None:
            return None
        try:
            return self._place_store.get_active_target_label()
        except Exception:
            return None

    def set_hardware(self, hardware):
        """Attach the hardware controller for AI behavior."""
        self._hardware = hardware

    def set_place_store(self, place_store):
        """Attach the place store for AI delivery targeting."""
        self._place_store = place_store

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
                self._run_ai(frame, detections)
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
        if self._inference is None or self._mock_camera:
            return []
        return self._inference.infer(frame, settings.confidence)

    def _run_ai(self, frame: np.ndarray, detections: list[dict]):
        """Drive a simple autonomous loop in AI mode."""
        if self._hardware is None:
            self._ai_state = "idle"
            return

        if self._hardware.estop:
            self._ai_state = "stopped"
            self._last_motor = None
            return

        if self._hardware.mode != "ai":
            self._reset_ai()
            return

        if self._mock_camera:
            self._ai_state = "waiting-for-camera"
            self._set_motor_once(0, 0)
            return

        now = time.monotonic()
        if self._ai_stage == "grab":
            self._tick_grab(now)
            return
        if self._ai_stage == "return":
            self._tick_return(frame, detections, now)
            return
        if self._ai_stage == "drop":
            self._tick_drop(now)
            return

        target = self._select_target(detections)
        if target is None:
            if self._ai_has_payload and not self.ai_target_label:
                self._ai_state = "awaiting-target"
                self._set_motor_once(0, 0)
                return
            self._ai_state = "searching"
            self._search_for_target(now)
            return

        self._track_target(frame, target)

    def _reset_ai(self):
        """Return AI internals to a safe idle state."""
        if self._ai_state != "idle":
            self._set_motor_once(0, 0)
        self._ai_state = "idle"
        self._ai_has_payload = False
        self._ai_stage = "search"
        self._ai_stage_until = 0.0
        self._ai_stage_started = False
        self._ai_next_search_update = 0.0
        self._last_motor = None

    def _select_target(self, detections: list[dict]) -> dict | None:
        """Pick a sock before grab and the active place target after grab."""
        if self._ai_has_payload:
            target_label = self.ai_target_label
            if not target_label:
                return None
            targets = [det for det in detections if det.get("class") == target_label]
            if not targets:
                return None
            return max(targets, key=lambda det: det.get("confidence", 0.0))

        socks = [det for det in detections if "sock" in det.get("class", "").lower()]
        if not socks:
            return None
        return max(socks, key=lambda det: det.get("confidence", 0.0))

    def _search_for_target(self, now: float):
        """Rotate in place and sweep the camera while looking for the current target."""
        if self._hardware is None:
            return
        if now < self._ai_next_search_update:
            return
        self._ai_next_search_update = now + 0.45
        self._set_motor_once(self.AI_SEARCH_SPEED * self._ai_search_dir, -self.AI_SEARCH_SPEED * self._ai_search_dir)
        pan_angle = 120 if self._ai_search_dir > 0 else 60
        try:
            self._hardware.set_servo(2, pan_angle)
        except Exception:
            pass
        self._ai_search_dir *= -1

    def _track_target(self, frame: np.ndarray, target: dict):
        """Align with the target and approach until a grab routine can start."""
        x1, y1, x2, y2 = target["bbox"]
        frame_h, frame_w = frame.shape[:2]
        target_x = (x1 + x2) / 2
        offset = (target_x - frame_w / 2) / max(frame_w / 2, 1)
        bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
        bbox_ratio = bbox_area / max(frame_w * frame_h, 1)

        if abs(offset) > self.AI_CENTER_TOLERANCE:
            self._ai_state = "aligning"
            if offset < 0:
                self._set_motor_once(-self.AI_TURN_SPEED, self.AI_TURN_SPEED)
                self._hardware.set_servo(2, 105)
            else:
                self._set_motor_once(self.AI_TURN_SPEED, -self.AI_TURN_SPEED)
                self._hardware.set_servo(2, 75)
            return

        if bbox_ratio < self.AI_CLOSE_ENOUGH_RATIO:
            self._ai_state = "approaching"
            self._hardware.set_servo(2, 90)
            self._set_motor_once(self.AI_FORWARD_SPEED, self.AI_FORWARD_SPEED)
            return

        self._ai_state = "grabbing"
        self._set_motor_once(0, 0)
        self._ai_stage = "grab"
        self._ai_stage_started = False
        self._ai_stage_until = 0.0

    def _tick_grab(self, now: float):
        """Run the scripted grab sequence."""
        if self._hardware is None:
            return
        if not self._ai_stage_started:
            self._hardware.set_servo(1, self.AI_LIFT_DOWN)
            self._hardware.set_servo(0, self.AI_GRIP_OPEN)
            self._ai_stage_until = now + 0.35
            self._ai_stage_started = True
            return
        if now < self._ai_stage_until:
            return
        if not self._ai_has_payload:
            self._hardware.set_servo(0, self.AI_GRIP_CLOSED)
            self._hardware.set_servo(1, self.AI_LIFT_UP)
            self._ai_has_payload = True
            self._ai_state = "secured"
            self._ai_stage = "return"
            self._ai_stage_started = False
            self._ai_stage_until = 0.0

    def _tick_return(self, frame: np.ndarray, detections: list[dict], now: float):
        """Seek the active place target and fall back to a simple reverse retreat."""
        if self._hardware is None:
            return
        target_label = self.ai_target_label
        if target_label:
            target = self._select_target(detections)
            if target is None:
                self._ai_state = "searching-for-target"
                self._search_for_target(now)
                return

            x1, y1, x2, y2 = target["bbox"]
            frame_h, frame_w = frame.shape[:2]
            target_x = (x1 + x2) / 2
            offset = (target_x - frame_w / 2) / max(frame_w / 2, 1)
            bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
            bbox_ratio = bbox_area / max(frame_w * frame_h, 1)

            if abs(offset) > self.AI_CENTER_TOLERANCE:
                self._ai_state = "aligning-to-target"
                if offset < 0:
                    self._set_motor_once(-self.AI_TURN_SPEED, self.AI_TURN_SPEED)
                    self._hardware.set_servo(2, 105)
                else:
                    self._set_motor_once(self.AI_TURN_SPEED, -self.AI_TURN_SPEED)
                    self._hardware.set_servo(2, 75)
                return

            if bbox_ratio < self.AI_CLOSE_ENOUGH_RATIO:
                self._ai_state = "delivering"
                self._hardware.set_servo(2, 90)
                self._set_motor_once(self.AI_FORWARD_SPEED, self.AI_FORWARD_SPEED)
                return

            self._set_motor_once(0, 0)
            self._ai_stage = "drop"
            self._ai_stage_started = False
            self._ai_stage_until = 0.0
            return

        if not self._ai_stage_started:
            self._ai_state = "returning"
            self._set_motor_once(-self.AI_FORWARD_SPEED, -self.AI_FORWARD_SPEED)
            self._ai_stage_until = now + 1.2
            self._ai_stage_started = True
            return
        if now < self._ai_stage_until:
            return
        self._set_motor_once(0, 0)
        self._ai_stage = "drop"
        self._ai_stage_started = False
        self._ai_stage_until = 0.0

    def _tick_drop(self, now: float):
        """Release the payload and resume searching."""
        if self._hardware is None:
            return
        if not self._ai_stage_started:
            self._ai_state = "dropping"
            self._hardware.set_servo(1, self.AI_LIFT_DOWN)
            self._hardware.set_servo(0, self.AI_GRIP_OPEN)
            self._ai_stage_until = now + 0.35
            self._ai_stage_started = True
            return
        if now < self._ai_stage_until:
            return
        self._hardware.set_servo(1, self.AI_LIFT_UP)
        self._ai_has_payload = False
        self._ai_state = "searching"
        self._ai_stage = "search"
        self._ai_stage_started = False
        self._ai_stage_until = 0.0

    def _set_motor_once(self, left: int, right: int):
        """Avoid spamming the same motor command every frame."""
        if self._hardware is None:
            return
        command = (left, right)
        if self._last_motor == command:
            return
        self._last_motor = command
        self._hardware.set_motor(left, right)

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
        if self._hardware and self._hardware.mode == "ai":
            cv2.putText(frame, f"AI: {self._ai_state}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        return frame
