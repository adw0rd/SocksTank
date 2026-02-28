"""SocksTank web server configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings

DEFAULT_DEV_MODEL_PATH = "models/yolo11_best.pt"
DEFAULT_RPI_MODEL_PATH = "models/yolo11_best_ncnn_model"


def _is_raspberry_pi() -> bool:
    """Best-effort detection of Raspberry Pi hardware."""
    model_path = Path("/sys/firmware/devicetree/base/model")
    if not model_path.exists():
        return False
    try:
        return "Raspberry Pi" in model_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def resolve_model_path(
    explicit_model: str | None = None,
    configured_model: str | None = None,
    *,
    runtime_role: str = "serve",
    mock: bool = False,
) -> str:
    """Resolve the best model path for the current runtime."""
    if explicit_model:
        return explicit_model
    if configured_model:
        return configured_model
    if runtime_role == "gpu-server":
        return DEFAULT_DEV_MODEL_PATH
    if mock:
        return DEFAULT_DEV_MODEL_PATH
    if _is_raspberry_pi():
        return DEFAULT_RPI_MODEL_PATH
    return DEFAULT_DEV_MODEL_PATH


class Settings(BaseSettings):
    model_path: str | None = None
    confidence: float = 0.5
    resolution_w: int = 640
    resolution_h: int = 480
    camera_fps: int = 10
    pcb_version: int = 1  # PCB Version: 1 (V1.0) or 2 (V2.0)
    mock: bool = False
    host: str = "0.0.0.0"
    port: int = 8080
    telemetry_hz: float = 5.0
    inference_mode: str = "auto"  # "auto" | "local" | "remote"

    # Gradual CPU warmup (prevent power crash on RPi)
    cpu_warmup: bool = True
    cpu_warmup_stages: str = "1,2,3,4"  # Stages (core count)
    cpu_warmup_samples: int = 3  # Iterations per stage
    cpu_warmup_pause_s: float = 2.0  # Pause between stages (seconds)

    # NcnnNativeDetector (pip ncnn + OMP workaround)
    ncnn_cpp: bool = False  # Use NcnnNativeDetector instead of ultralytics
    ncnn_threads: int = 2  # OMP thread count for ncnn

    model_config = {"env_prefix": "SOCKSTANK_"}


settings = Settings()
