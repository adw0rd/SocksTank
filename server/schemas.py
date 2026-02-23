"""Pydantic-модели для WebSocket и REST API."""

from pydantic import BaseModel


class WsCommand(BaseModel):
    cmd: str
    params: dict = {}


class TelemetryMessage(BaseModel):
    type: str = "telemetry"
    distance_cm: float = 0.0
    ir_sensors: list[int] = [0, 0, 0]
    fps: float = 0.0
    detections: list[dict] = []
    mode: str = "manual"
    cpu_temp: float = 0.0


class ConfigResponse(BaseModel):
    model_path: str
    confidence: float
    resolution_w: int
    resolution_h: int
    camera_fps: int
    mock: bool


class ConfigUpdate(BaseModel):
    confidence: float | None = None
    camera_fps: int | None = None


class StatusResponse(BaseModel):
    fps: float
    mode: str
    mock: bool
    detections: int
    motor_left: int
    motor_right: int
    distance_cm: float
    ir_sensors: list[int]
