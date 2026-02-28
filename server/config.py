"""SocksTank web server configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = "models/yolo11_best_ncnn_model"
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
