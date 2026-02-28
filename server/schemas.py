"""Pydantic models for WebSocket and REST APIs."""

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
    inference_mode: str = "auto"
    inference_backend: str = "local"
    inference_ms: float = 0.0
    inference_error: str | None = None
    camera_source: str = "camera"
    ai_state: str = "idle"
    estop: bool = False
    claw_servos_enabled: bool = True
    led_supported: bool = True


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


class GPUServerSchema(BaseModel):
    name: str | None = None
    host: str
    port: int = 8090
    username: str
    auth_type: str = "key"  # "key" | "password"
    password: str | None = None
    key_path: str | None = None
    status: str = "offline"
    gpu: str | None = None


class GPUServerCreate(BaseModel):
    name: str | None = None
    host: str
    port: int = 8090
    username: str
    auth_type: str = "key"
    password: str | None = None
    key_path: str | None = None


class GPUServerUpdate(BaseModel):
    name: str | None = None
    host: str
    port: int = 8090
    username: str
    auth_type: str = "key"
    password: str | None = None
    key_path: str | None = None


class InferenceModeUpdate(BaseModel):
    mode: str  # "auto" | "local" | "remote"
