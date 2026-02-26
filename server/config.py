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

    # Плавный старт CPU (предотвращение краша питания на RPi)
    cpu_warmup: bool = True
    cpu_warmup_stages: str = "1,2,3,4"  # Стадии (кол-во ядер)
    cpu_warmup_samples: int = 3  # Итераций на стадию
    cpu_warmup_pause_s: float = 2.0  # Пауза между стадиями (секунды)

    # C++ ncnn wrapper (обход OMP бага в Python ncnn)
    ncnn_cpp: bool = False  # Использовать C++ ncnn wrapper вместо ultralytics
    ncnn_threads: int = 2  # Кол-во OMP потоков для C++ ncnn

    model_config = {"env_prefix": "SOCKSTANK_"}


settings = Settings()
