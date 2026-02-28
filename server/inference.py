"""InferenceRouter for switching between local and remote inference."""

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
    """Load class names from the metadata.yaml file next to the model."""
    meta_path = os.path.join(model_dir, "metadata.yaml")
    if not os.path.exists(meta_path):
        log.warning("metadata.yaml not found: %s; using default class names", meta_path)
        return {0: "sock"}
    with open(meta_path) as f:
        meta = yaml.safe_load(f)
    names = meta.get("names", {0: "sock"})
    # metadata.yaml stores keys as ints, but normalize them defensively
    return {int(k): v for k, v in names.items()}


def _try_load_ncnn_native(model_dir: str, num_threads: int):
    """Load a model via the pip ncnn API with an OMP workaround."""
    try:
        import ncnn as ncnn_lib  # noqa: F401
    except ImportError:
        log.info("pip ncnn not found; using ultralytics")
        return None, None

    param_path = os.path.join(model_dir, "model.ncnn.param")
    bin_path = os.path.join(model_dir, "model.ncnn.bin")

    if not os.path.exists(param_path) or not os.path.exists(bin_path):
        log.warning("NCNN model files were not found in %s", model_dir)
        return None, None

    detector = NcnnNativeDetector(param_path, bin_path, num_threads)
    class_names = _load_class_names(model_dir)
    log.info("pip ncnn native loaded: %s (%d OMP threads, classes: %s)", model_dir, num_threads, class_names)
    return detector, class_names


class NcnnNativeDetector:
    """Wrapper around pip ncnn with OMP, preprocess, and postprocess workarounds.

    On aarch64, pip ncnn reports get_omp_num_threads() as 1.
    Calling set_omp_num_threads(N) before each inference still works.
    Result: about 16 FPS on 4 threads vs 8.5 FPS on 1 thread.
    """

    INPUT_SIZE = 640

    def __init__(self, param_path: str, bin_path: str, num_threads: int = 2):
        import ncnn as ncnn_lib

        self._ncnn = ncnn_lib
        self._num_threads = num_threads
        self._inference_ms = 0.0

        self._net = ncnn_lib.Net()
        self._net.opt.num_threads = num_threads
        self._net.opt.use_vulkan_compute = False
        self._net.opt.use_fp16_packed = True
        self._net.opt.use_fp16_storage = True
        self._net.load_param(param_path)
        self._net.load_model(bin_path)

    def detect(self, frame: np.ndarray, conf_threshold: float = 0.5, nms_threshold: float = 0.45) -> list[dict]:
        """Run detection on an RGB uint8 frame with shape (H, W, 3)."""
        h, w = frame.shape[:2]
        mat_in, scale, pad_w, pad_h = self._preprocess(frame)

        # OMP workaround: set the thread count before each inference
        self._ncnn.set_omp_num_threads(self._num_threads)

        t0 = time.monotonic()
        ex = self._net.create_extractor()
        ex.input("in0", mat_in)
        _, out = ex.extract("out0")
        self._inference_ms = (time.monotonic() - t0) * 1000

        return self._postprocess(out, scale, pad_w, pad_h, w, h, conf_threshold, nms_threshold)

    def last_inference_ms(self) -> float:
        return self._inference_ms

    def set_num_threads(self, n: int):
        self._num_threads = n
        self._net.opt.num_threads = n

    def _preprocess(self, frame: np.ndarray):
        """Apply letterbox resize and normalization for ncnn."""
        h, w = frame.shape[:2]
        scale = min(self.INPUT_SIZE / w, self.INPUT_SIZE / h)
        new_w = int(round(w * scale))
        new_h = int(round(h * scale))
        pad_w = (self.INPUT_SIZE - new_w) // 2
        pad_h = (self.INPUT_SIZE - new_h) // 2

        # Use OpenCV for letterbox padding; it is faster than ncnn copy_make_border
        resized = cv2.resize(frame, (new_w, new_h))
        padded = np.full((self.INPUT_SIZE, self.INPUT_SIZE, 3), 114, dtype=np.uint8)
        padded[pad_h : pad_h + new_h, pad_w : pad_w + new_w] = resized  # noqa: E203

        mat = self._ncnn.Mat.from_pixels(padded, self._ncnn.Mat.PixelType.PIXEL_RGB, self.INPUT_SIZE, self.INPUT_SIZE)
        norm_vals = [1.0 / 255.0, 1.0 / 255.0, 1.0 / 255.0]
        mat.substract_mean_normalize([], norm_vals)

        return mat, scale, pad_w, pad_h

    def _postprocess(self, out, scale, pad_w, pad_h, orig_w, orig_h, conf_thresh, nms_thresh):
        """Decode YOLO ncnn output [5, 8400] into a list of detections."""
        data = np.array(out)
        if data.shape[0] == 5:
            data = data.T  # (5, 8400) → (8400, 5)

        # Vectorized confidence filtering: ~0.02 ms instead of a ~13 ms Python loop
        scores = data[:, 4]
        mask = scores >= conf_thresh
        filtered = data[mask]

        if len(filtered) == 0:
            return []

        cx, cy, bw, bh, sc = filtered[:, 0], filtered[:, 1], filtered[:, 2], filtered[:, 3], filtered[:, 4]
        x1 = np.clip(((cx - bw / 2 - pad_w) / scale).astype(np.int32), 0, orig_w)
        y1 = np.clip(((cy - bh / 2 - pad_h) / scale).astype(np.int32), 0, orig_h)
        x2 = np.clip(((cx + bw / 2 - pad_w) / scale).astype(np.int32), 0, orig_w)
        y2 = np.clip(((cy + bh / 2 - pad_h) / scale).astype(np.int32), 0, orig_h)

        dets = [
            {"class_id": 0, "confidence": float(sc[i]), "bbox": (int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i]))}
            for i in range(len(filtered))
        ]

        if len(dets) > 1:
            dets = self._nms(dets, nms_thresh)
        return dets

    @staticmethod
    def _nms(dets: list[dict], threshold: float) -> list[dict]:
        """Non-maximum suppression."""
        dets.sort(key=lambda d: d["confidence"], reverse=True)
        keep = []
        suppressed = [False] * len(dets)
        for i in range(len(dets)):
            if suppressed[i]:
                continue
            keep.append(dets[i])
            for j in range(i + 1, len(dets)):
                if suppressed[j]:
                    continue
                if NcnnNativeDetector._iou(dets[i]["bbox"], dets[j]["bbox"]) > threshold:
                    suppressed[j] = True
        return keep

    @staticmethod
    def _iou(a, b) -> float:
        ix1 = max(a[0], b[0])
        iy1 = max(a[1], b[1])
        ix2 = min(a[2], b[2])
        iy2 = min(a[3], b[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0


class InferenceRouter:
    """Inference router for local YOLO, ncnn native, or remote HTTP inference."""

    def __init__(self, model=None, cpp_detector=None, class_names=None):
        self._model = model
        # cpp_detector may be either NcnnNativeDetector (pip ncnn) or NCNNDetector (C++ wrapper)
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
        """Set the remote inference server URL."""
        with self._lock:
            self._remote_url = url
            if url:
                log.info("Remote inference URL: %s", url)

    def infer(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Run inference using the active backend."""
        use_remote = self._should_use_remote()

        if use_remote:
            return self._infer_remote(frame, confidence)
        return self._infer_local(frame, confidence)

    def _should_use_remote(self) -> bool:
        """Decide whether remote inference should be used."""
        if self._mode == "local":
            return False
        if self._mode == "remote":
            return True
        # In auto mode, use remote inference when a URL is configured
        return self._remote_url is not None

    def _infer_local(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Run local inference via ncnn or ultralytics YOLO."""
        self._error = None

        # Prefer the ncnn-based detector when available
        if self._cpp_detector is not None:
            return self._infer_cpp(frame, confidence)

        # Fallback: ultralytics YOLO
        return self._infer_ultralytics(frame, confidence)

    def _infer_cpp(self, frame: np.ndarray, confidence: float) -> list[dict]:
        """Run inference through ncnn native (pip ncnn or C++ wrapper)."""
        self._active_backend = "local:ncnn-native"

        # The detector expects RGB uint8 (HWC); the frame is already RGB from picamera2/mock
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
        """Run inference through ultralytics YOLO."""
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
        """Run remote inference via HTTP POST."""
        if not self._remote_url:
            self._error = "No remote URL"
            if self._mode == "auto":
                return self._infer_local(frame, confidence)
            return []

        try:
            # Encode the RGB frame as JPEG
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
            # In auto mode, fall back to local inference
            if self._mode == "auto":
                log.info("Falling back to local inference")
                return self._infer_local(frame, confidence)
            return []

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()
