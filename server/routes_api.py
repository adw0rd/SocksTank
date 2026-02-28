"""REST API endpoints for configuration and status."""

import os
import logging

from fastapi import APIRouter

from server.config import settings
from server.schemas import ConfigResponse, ConfigUpdate, StatusResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# References injected during application startup
_hardware = None
_camera_manager = None


def set_dependencies(hardware, camera_manager):
    global _hardware, _camera_manager
    _hardware = hardware
    _camera_manager = camera_manager


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Return the current configuration."""
    return ConfigResponse(
        model_path=settings.model_path,
        confidence=settings.confidence,
        resolution_w=settings.resolution_w,
        resolution_h=settings.resolution_h,
        camera_fps=settings.camera_fps,
        mock=settings.mock,
    )


@router.put("/config", response_model=ConfigResponse)
async def update_config(update: ConfigUpdate):
    """Update mutable configuration fields (confidence and FPS)."""
    if update.confidence is not None:
        settings.confidence = max(0.1, min(1.0, update.confidence))
    if update.camera_fps is not None:
        settings.camera_fps = max(1, min(30, update.camera_fps))
    return await get_config()


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Return the current robot status."""
    return StatusResponse(
        fps=_camera_manager.fps if _camera_manager else 0,
        mode=_hardware.mode if _hardware else "manual",
        mock=settings.mock,
        detections=len(_camera_manager.detections) if _camera_manager else 0,
        motor_left=_hardware.motor_left if _hardware else 0,
        motor_right=_hardware.motor_right if _hardware else 0,
        distance_cm=_hardware.get_distance() if _hardware else 0,
        ir_sensors=_hardware.get_infrared() if _hardware else [0, 0, 0],
    )


@router.get("/models")
async def list_models():
    """List available .pt models."""
    models = []
    for f in os.listdir("."):
        if f.endswith(".pt"):
            models.append(f)
    return {"models": sorted(models), "current": settings.model_path}
