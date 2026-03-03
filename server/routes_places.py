"""REST API for user-defined places and training jobs."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.places import PlaceStore
from server.schemas import (
    OkResponse,
    PlaceAnnotationsListResponse,
    PlaceAnnotationRecord,
    PlaceAnnotationUpsertRequest,
    PlaceCreateRequest,
    PlaceImagesUploadRequest,
    PlaceImagesListResponse,
    PlaceImagesUploadResponse,
    PlaceJobStatus,
    PlacesListResponse,
    PlaceSetActiveRequest,
    PlaceSetActiveResponse,
    PlaceSummary,
    PlaceTrainRequest,
    PlaceTrainResponse,
    PlaceTrainingJob,
    PlaceUpdateRequest,
)

router = APIRouter(prefix="/api/places", tags=["places"])

_store = PlaceStore()
_gpu_manager = None
_local_training_launcher = None


def set_store(store: PlaceStore) -> None:
    """Override the default place store (used in tests)."""
    global _store
    _store = store


def set_dependencies(gpu_manager, local_training_launcher=None) -> None:
    """Inject shared dependencies from app.py."""
    global _gpu_manager, _local_training_launcher
    _gpu_manager = gpu_manager
    if local_training_launcher is not None:
        _local_training_launcher = local_training_launcher


def _select_training_server(preferred_host: str | None):
    if _gpu_manager:
        servers = list(_gpu_manager.servers)
        online_servers = [server for server in servers if server.status == "online"]
        if preferred_host:
            for server in online_servers:
                if preferred_host in {server.host, server.name}:
                    return server
        if online_servers:
            return online_servers[0]
    return None


def _default_local_training_launcher(dataset_path: str, base_model: str) -> dict:
    job_dir = str(Path(dataset_path).parent)
    cmd = [
        sys.executable,
        "-m",
        "server.place_train_worker",
        "--dataset",
        dataset_path,
        "--job-dir",
        job_dir,
        "--base-model",
        base_model,
        "--device",
        "cpu",
    ]
    subprocess.Popen(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"ok": True}


def _load_local_training_status(job) -> dict | None:
    if not job.dataset_path:
        return None
    status_path = Path(job.dataset_path).parent / "status.json"
    if not status_path.exists():
        return None
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sync_job_from_status(job, status_payload: dict):
    status_value = status_payload.get("status")
    if status_value not in PlaceJobStatus._value2member_map_:
        return job
    status = PlaceJobStatus(status_value)
    started_at = status_payload.get("started_at")
    finished_at = status_payload.get("finished_at")
    result_model_version = status_payload.get("result_model_version")
    result_model_path = status_payload.get("result_model_path")
    result_ncnn_path = status_payload.get("result_ncnn_path")
    error = status_payload.get("error")
    updated = _store.update_job(
        job.id,
        status=status,
        started_at=datetime.fromisoformat(started_at) if started_at else None,
        finished_at=datetime.fromisoformat(finished_at) if finished_at else None,
        clear_finished_at=status is PlaceJobStatus.TRAINING and not finished_at,
        result_model_version=result_model_version,
        result_model_path=result_model_path,
        result_ncnn_path=result_ncnn_path,
        error=error,
    )
    return updated or job


def _should_fallback_remote_training(job, status_payload: dict) -> bool:
    if not job.executor.startswith("remote:"):
        return False
    if status_payload.get("status") != PlaceJobStatus.FAILED.value:
        return False
    error = (status_payload.get("error") or "").lower()
    fallback_markers = (
        "cuda-capable device(s) is/are busy or unavailable",
        "cudaerrordevicesunavailable",
        "cuda device busy",
        "device unavailable",
        "invalid cuda 'device=0' requested",
        "torch.cuda.is_available(): false",
    )
    return any(marker in error for marker in fallback_markers)


def _fallback_job_to_local(job, reason: str):
    launcher = _local_training_launcher or _default_local_training_launcher
    launch_result = launcher(job.dataset_path, job.base_model)
    if launch_result.get("ok"):
        updated = _store.update_job(
            job.id,
            executor="local:rpi5",
            status=PlaceJobStatus.TRAINING,
            started_at=datetime.now(UTC),
            clear_finished_at=True,
            finished_at=None,
            error=f"Remote training fallback: {reason}",
        )
    else:
        updated = _store.update_job(
            job.id,
            executor="local:rpi5",
            status=PlaceJobStatus.FAILED,
            finished_at=datetime.now(UTC),
            error=f"Local fallback start failed after remote error: {launch_result.get('error', 'unknown error')}",
        )
    return updated or job


@router.get("", response_model=PlacesListResponse)
async def list_places():
    active_id, places = _store.list_places()
    return PlacesListResponse(active_target_place_id=active_id, items=places)


@router.post("", response_model=PlaceSummary)
async def create_place(body: PlaceCreateRequest):
    return _store.create_place(body.name)


@router.put("/active", response_model=PlaceSetActiveResponse)
async def set_active_place(body: PlaceSetActiveRequest):
    try:
        active_id = _store.set_active_target(body.place_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PlaceSetActiveResponse(active_target_place_id=active_id)


@router.get("/{place_id}", response_model=PlaceSummary)
async def get_place(place_id: str):
    place = _store.get_place(place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.put("/{place_id}", response_model=PlaceSummary)
async def update_place(place_id: str, body: PlaceUpdateRequest):
    place = _store.update_place(place_id, body.name)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.delete("/{place_id}", response_model=OkResponse)
async def delete_place(place_id: str):
    if not _store.delete_place(place_id):
        raise HTTPException(status_code=404, detail="Place not found")
    return OkResponse()


@router.post("/{place_id}/images", response_model=PlaceImagesUploadResponse)
async def upload_place_images(place_id: str, body: PlaceImagesUploadRequest):
    try:
        items = _store.add_images(place_id, body.items)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    return PlaceImagesUploadResponse(items=items)


@router.get("/{place_id}/images", response_model=PlaceImagesListResponse)
async def list_place_images(place_id: str):
    try:
        items = _store.list_images(place_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    return PlaceImagesListResponse(items=items)


@router.get("/{place_id}/images/{image_id}")
async def get_place_image(place_id: str, image_id: str):
    try:
        path = _store.get_image_path(place_id, image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@router.get("/{place_id}/images/{image_id}/thumb")
async def get_place_image_thumbnail(place_id: str, image_id: str):
    try:
        path = _store.get_thumbnail_path(place_id, image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@router.delete("/{place_id}/images/{image_id}", response_model=OkResponse)
async def delete_place_image(place_id: str, image_id: str):
    try:
        deleted = _store.delete_image(place_id, image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found")
    return OkResponse()


@router.put("/{place_id}/images/{image_id}/annotation", response_model=PlaceAnnotationRecord)
async def upsert_place_annotation(place_id: str, image_id: str, body: PlaceAnnotationUpsertRequest):
    try:
        return _store.upsert_annotation(place_id, image_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc


@router.get("/{place_id}/annotations", response_model=PlaceAnnotationsListResponse)
async def list_place_annotations(place_id: str):
    try:
        items = _store.list_annotations(place_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    return PlaceAnnotationsListResponse(items=items)


@router.post("/{place_id}/train", response_model=PlaceTrainResponse)
async def train_place(place_id: str, body: PlaceTrainRequest):
    remote_server = _select_training_server(body.gpu_host)
    executor = f"remote:{remote_server.name or remote_server.host}" if remote_server else "local:rpi5"
    try:
        job = _store.train_place(place_id, base_model="models/yolo11_best.pt", executor=executor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if remote_server and _gpu_manager:
        stage_result = _gpu_manager.stage_place_training_dataset(remote_server.host, job.dataset_path, job.id)
        if stage_result.get("ok"):
            start_result = _gpu_manager.start_place_training(
                remote_server.host,
                job.id,
                stage_result["remote_dataset_path"],
                job.base_model,
            )
            if start_result.get("ok"):
                updated = _store.update_job(
                    job.id,
                    status=PlaceJobStatus.TRAINING,
                    started_at=datetime.now(UTC),
                    remote_dataset_path=stage_result["remote_dataset_path"],
                    remote_host=remote_server.host,
                )
                if updated is not None:
                    job = updated
            else:
                updated = _store.update_job(
                    job.id,
                    executor="local:rpi5",
                    error=f"Remote training start failed: {start_result.get('error', 'unknown error')}",
                )
                if updated is not None:
                    job = updated
        else:
            updated = _store.update_job(
                job.id,
                executor="local:rpi5",
                error=f"Remote dataset staging failed: {stage_result.get('error', 'unknown error')}",
            )
            if updated is not None:
                job = updated
    if job.executor == "local:rpi5":
        launcher = _local_training_launcher or _default_local_training_launcher
        launch_result = launcher(job.dataset_path, job.base_model)
        if launch_result.get("ok"):
            updated = _store.update_job(job.id, status=PlaceJobStatus.TRAINING, started_at=datetime.now(UTC))
            if updated is not None:
                job = updated
        else:
            updated = _store.update_job(
                job.id,
                status=PlaceJobStatus.FAILED,
                finished_at=datetime.now(UTC),
                error=f"Local training start failed: {launch_result.get('error', 'unknown error')}",
            )
            if updated is not None:
                job = updated
    return PlaceTrainResponse(job_id=job.id, status=job.status, executor=job.executor)


@router.get("/jobs/{job_id}", response_model=PlaceTrainingJob)
async def get_place_job(job_id: str):
    job = _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (PlaceJobStatus.READY, PlaceJobStatus.FAILED):
        if job.executor.startswith("remote:") and _gpu_manager and job.remote_host:
            result = _gpu_manager.read_place_training_status(job.remote_host, job.id)
            if result.get("ok"):
                status_payload = result["status"]
                job = _sync_job_from_status(job, status_payload)
                if _should_fallback_remote_training(job, status_payload):
                    job = _fallback_job_to_local(job, status_payload.get("error", "remote training failed"))
        elif job.executor == "local:rpi5":
            status_payload = _load_local_training_status(job)
            if status_payload:
                job = _sync_job_from_status(job, status_payload)
    if (
        job.status is PlaceJobStatus.READY
        and job.executor.startswith("remote:")
        and _gpu_manager
        and job.remote_host
        and job.result_model_path
        and not Path(job.result_model_path).exists()
    ):
        fetch_result = _gpu_manager.fetch_place_training_artifacts(
            job.remote_host,
            remote_model_path=job.result_model_path,
            remote_ncnn_path=job.result_ncnn_path,
            local_job_dir=Path(job.dataset_path).parent if job.dataset_path else Path("user_data/places/jobs") / job.id,
        )
        if fetch_result.get("ok"):
            updated = _store.update_job(
                job.id,
                result_model_path=fetch_result.get("result_model_path"),
                result_ncnn_path=fetch_result.get("result_ncnn_path"),
            )
            if updated is not None:
                job = updated
    return job
