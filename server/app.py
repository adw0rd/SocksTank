"""FastAPI app factory + lifespan."""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.config import settings
from server.camera import CameraManager
from server.hardware import HardwareController
from server.inference import InferenceRouter, _try_load_ncnn_native
from server.gpu_manager import GPUServerManager
from server.freenove_bridge import load_camera
from server.routes_video import router as video_router, set_camera_manager
from server.routes_ws import router as ws_router
from server.routes_ws import set_dependencies as ws_set_deps
from server.routes_api import router as api_router
from server.routes_api import set_dependencies as api_set_deps
from server.routes_gpu import router as gpu_router
from server.routes_gpu import set_dependencies as gpu_set_deps

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация и завершение ресурсов."""
    # Загрузка YOLO-модели
    model = None
    cpp_detector = None
    class_names = None

    if not os.path.exists(settings.model_path):
        log.warning("Модель не найдена: %s — стрим без детекции", settings.model_path)
    elif settings.ncnn_cpp:
        # Попытка загрузить pip ncnn native (приоритет — 16 FPS vs 3.5 FPS ultralytics)
        cpp_detector, class_names = _try_load_ncnn_native(settings.model_path, settings.ncnn_threads)
        if cpp_detector is None:
            log.warning("pip ncnn недоступен — fallback на ultralytics")
            from ultralytics import YOLO

            model = YOLO(settings.model_path)
            log.info("YOLO модель загружена (fallback): %s", settings.model_path)
    else:
        from ultralytics import YOLO

        model = YOLO(settings.model_path)
        log.info("YOLO модель загружена: %s", settings.model_path)

    # Инициализация InferenceRouter
    inference_router = InferenceRouter(model, cpp_detector, class_names)

    # Инициализация GPUServerManager
    gpu_manager = GPUServerManager()
    gpu_manager.load()
    gpu_manager.start_health_loop(inference_router)

    # Плавный старт CPU (предотвращение краша питания на RPi)
    warmup_model = model or cpp_detector
    if warmup_model and not settings.mock and settings.cpu_warmup:
        from server.cpu_warmup import gradual_warmup

        gradual_warmup(warmup_model, settings)

    # Инициализация камеры и менеджера
    camera = load_camera()
    camera_manager = CameraManager(camera, inference_router)
    camera_manager.start()

    # Инициализация управления
    hardware = HardwareController()

    # Установка зависимостей в роутеры
    set_camera_manager(camera_manager)
    ws_set_deps(hardware, camera_manager)
    api_set_deps(hardware, camera_manager)
    gpu_set_deps(inference_router, gpu_manager)

    log.info("SocksTank сервер запущен на %s:%d (mock=%s)", settings.host, settings.port, settings.mock)

    yield

    # Завершение
    camera_manager.stop()
    gpu_manager.stop()
    inference_router.close()
    hardware.close()
    log.info("SocksTank сервер остановлен")


def create_app() -> FastAPI:
    """Создание FastAPI-приложения."""
    app = FastAPI(title="SocksTank", version="0.1.0", lifespan=lifespan)

    app.include_router(video_router)
    app.include_router(ws_router)
    app.include_router(api_router)
    app.include_router(gpu_router)

    # Статика фронтенда (если собран)
    static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
        log.info("Фронтенд подключён: %s", static_dir)

    return app
