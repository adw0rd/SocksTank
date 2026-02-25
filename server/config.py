"""Конфигурация веб-сервера SocksTank."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = "models/yolo11_best_ncnn_model"
    confidence: float = 0.5
    resolution_w: int = 640
    resolution_h: int = 480
    camera_fps: int = 10
    freenove_path: str = "~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server"
    mock: bool = False
    host: str = "0.0.0.0"
    port: int = 8080
    telemetry_hz: float = 5.0
    inference_mode: str = "auto"  # "auto" | "local" | "remote"

    model_config = {"env_prefix": "SOCKSTANK_"}


settings = Settings()
