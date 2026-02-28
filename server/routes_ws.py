"""WebSocket endpoint for control commands and telemetry."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.schemas import TelemetryMessage

log = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# References injected during application startup
_hardware = None
_camera_manager = None


def set_dependencies(hardware, camera_manager):
    global _hardware, _camera_manager
    _hardware = hardware
    _camera_manager = camera_manager


def _handle_command(data: dict):
    """Handle a command received from the client."""
    cmd = data.get("cmd", "")
    params = data.get("params", {})

    if cmd == "motor":
        _hardware.set_motor(params.get("left", 0), params.get("right", 0))
    elif cmd == "servo":
        _hardware.set_servo(params.get("channel", 0), params.get("angle", 90))
    elif cmd == "led":
        if "effect" in params:
            _hardware.led_effect(params["effect"])
        else:
            _hardware.set_led(params.get("r", 0), params.get("g", 0), params.get("b", 0))
    elif cmd == "stop":
        active = params.get("active")
        if active is None:
            active = not _hardware.estop
        if active:
            _hardware.stop_all()
        else:
            _hardware.release_stop()
    elif cmd == "mode":
        try:
            _hardware.mode = params.get("mode", "manual")
        except ValueError as exc:
            log.warning("Invalid mode command: %s", exc)
    else:
        log.warning("Unknown command: %s", cmd)


def _get_telemetry() -> str:
    """Build the telemetry payload as JSON."""
    from server.config import settings

    msg = TelemetryMessage(
        distance_cm=_hardware.get_distance(),
        ir_sensors=_hardware.get_infrared(),
        fps=_camera_manager.fps if _camera_manager else 0,
        detections=_camera_manager.detections if _camera_manager else [],
        mode=_hardware.mode,
        cpu_temp=_hardware.get_cpu_temp(),
        inference_mode=settings.inference_mode,
        inference_backend=_camera_manager.inference_backend if _camera_manager else "local",
        inference_ms=_camera_manager.inference_ms if _camera_manager else 0,
        inference_error=_camera_manager.inference_error if _camera_manager else None,
        camera_source=_camera_manager.camera_source if _camera_manager else "camera",
        ai_state=_camera_manager.ai_state if _camera_manager else "idle",
        estop=_hardware.estop if _hardware else False,
    )
    return msg.model_dump_json()


@router.websocket("/ws/control")
async def websocket_control(ws: WebSocket):
    """WebSocket endpoint for client commands and server telemetry."""
    await ws.accept()
    log.info("WebSocket client connected")

    async def send_telemetry():
        """Send telemetry every 200 ms."""
        try:
            while True:
                await ws.send_text(_get_telemetry())
                await asyncio.sleep(0.2)
        except (WebSocketDisconnect, RuntimeError):
            pass

    telemetry_task = asyncio.create_task(send_telemetry())

    try:
        while True:
            text = await ws.receive_text()
            try:
                data = json.loads(text)
                _handle_command(data)
            except (json.JSONDecodeError, Exception) as e:
                log.warning("Command handling failed: %s", e)
    except WebSocketDisconnect:
        log.info("WebSocket client disconnected")
    finally:
        telemetry_task.cancel()
