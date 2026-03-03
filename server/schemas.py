"""Pydantic models for WebSocket and REST APIs."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


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


class PlaceStatus(str, Enum):
    DRAFT = "draft"
    ANNOTATING = "annotating"
    QUEUED = "queued"
    TRAINING = "training"
    EXPORTING = "exporting"
    DEPLOYING = "deploying"
    READY = "ready"
    FAILED = "failed"


class PlaceJobStatus(str, Enum):
    QUEUED = "queued"
    TRAINING = "training"
    EXPORTING = "exporting"
    DEPLOYING = "deploying"
    READY = "ready"
    FAILED = "failed"


class PlaceSummary(BaseModel):
    id: str
    name: str
    label: str
    status: PlaceStatus
    model_version: str | None = None
    image_count: int = 0
    is_active_target: bool = False
    created_at: datetime
    updated_at: datetime


class PlacesListResponse(BaseModel):
    active_target_place_id: str | None = None
    items: list[PlaceSummary]


class PlaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PlaceUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PlaceImageSummary(BaseModel):
    id: str
    filename: str
    path: str
    width: int
    height: int
    annotated: bool = False
    created_at: datetime


class PlaceImagesListResponse(BaseModel):
    items: list[PlaceImageSummary]


class PlaceImageUploadItem(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1)


class PlaceImagesUploadRequest(BaseModel):
    items: list[PlaceImageUploadItem] = Field(min_length=1)


class PlaceImagesUploadResponse(BaseModel):
    items: list[PlaceImageSummary]


class PlaceAnnotationUpsertRequest(BaseModel):
    x_center: float = Field(ge=0.0, le=1.0)
    y_center: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_box_bounds(self):
        if self.x_center - self.width / 2 < 0:
            raise ValueError("Bounding box exceeds image bounds on the left")
        if self.x_center + self.width / 2 > 1:
            raise ValueError("Bounding box exceeds image bounds on the right")
        if self.y_center - self.height / 2 < 0:
            raise ValueError("Bounding box exceeds image bounds on the top")
        if self.y_center + self.height / 2 > 1:
            raise ValueError("Bounding box exceeds image bounds on the bottom")
        return self


class PlaceAnnotationRecord(BaseModel):
    id: str
    place_image_id: str
    label: str
    x_center: float
    y_center: float
    width: float
    height: float
    created_at: datetime
    updated_at: datetime


class PlaceAnnotationsListResponse(BaseModel):
    items: list[PlaceAnnotationRecord]


class PlaceTrainRequest(BaseModel):
    gpu_host: str | None = None


class PlaceTrainResponse(BaseModel):
    job_id: str
    status: PlaceJobStatus
    executor: str


class PlaceTrainingJob(BaseModel):
    id: str
    place_id: str
    executor: str
    status: PlaceJobStatus
    dataset_path: str | None = None
    remote_dataset_path: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    base_model: str
    result_model_version: str | None = None
    result_model_path: str | None = None
    result_ncnn_path: str | None = None


class PlaceSetActiveRequest(BaseModel):
    place_id: str | None = None


class PlaceSetActiveResponse(BaseModel):
    active_target_place_id: str | None = None


class OkResponse(BaseModel):
    ok: bool = True
