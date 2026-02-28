"""MJPEG video stream endpoint."""

import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])

# CameraManager reference injected during application startup
_camera_manager = None


def set_camera_manager(cm):
    global _camera_manager
    _camera_manager = cm


async def _mjpeg_generator():
    """Yield MJPEG frames for StreamingResponse."""
    while True:
        if _camera_manager is None:
            await asyncio.sleep(0.1)
            continue

        jpeg = _camera_manager.get_jpeg()
        if jpeg is not None:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

        await asyncio.sleep(0.03)  # About 30 polls per second


@router.get("/stream")
async def video_stream():
    """Serve an MJPEG video stream from the camera."""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
