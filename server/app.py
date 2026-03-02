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
from server.routes_places import router as places_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and shut down application resources."""
    # Load the YOLO model
    model = None
    cpp_detector = None
    class_names = None

    if not os.path.exists(settings.model_path):
        log.warning("Model not found: %s; streaming without detection", settings.model_path)
    elif settings.ncnn_cpp:
        # Try pip ncnn native first (roughly 16 FPS vs 3.5 FPS with ultralytics)
        cpp_detector, class_names = _try_load_ncnn_native(settings.model_path, settings.ncnn_threads)
        if cpp_detector is None:
            log.warning("pip ncnn is unavailable; falling back to ultralytics")
            from ultralytics import YOLO

            model = YOLO(settings.model_path)
            log.info("YOLO model loaded (fallback): %s", settings.model_path)
    else:
        from ultralytics import YOLO

        model = YOLO(settings.model_path)
        log.info("YOLO model loaded: %s", settings.model_path)

    # Initialize the InferenceRouter
    inference_router = InferenceRouter(model, cpp_detector, class_names)

    # Initialize the GPUServerManager
    gpu_manager = GPUServerManager()
    gpu_manager.load()
    gpu_manager.start_health_loop(inference_router)

    # Gradual CPU warm-up to avoid power spikes on Raspberry Pi
    warmup_model = model or cpp_detector
    if warmup_model and not settings.mock and settings.cpu_warmup:
        from server.cpu_warmup import gradual_warmup

        gradual_warmup(warmup_model, settings)

    # Initialize hardware control
    hardware = HardwareController()

    # Initialize the camera and manager
    camera = load_camera()
    camera_manager = CameraManager(camera, inference_router)
    camera_manager.set_hardware(hardware)
    camera_manager.start()

    # Wire shared dependencies into the routers
    set_camera_manager(camera_manager)
    ws_set_deps(hardware, camera_manager)
    api_set_deps(hardware, camera_manager)
    gpu_set_deps(inference_router, gpu_manager)

    log.info("SocksTank server started on %s:%d (mock=%s)", settings.host, settings.port, settings.mock)

    yield

    # Shutdown
    camera_manager.stop()
    gpu_manager.stop()
    inference_router.close()
    hardware.close()
    log.info("SocksTank server stopped")


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="SocksTank", version="0.1.0", lifespan=lifespan)

    app.include_router(video_router)
    app.include_router(ws_router)
    app.include_router(api_router)
    app.include_router(gpu_router)
    app.include_router(places_router)

    # Mount frontend static files when the build is available
    static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
        log.info("Frontend mounted: %s", static_dir)

    return app
