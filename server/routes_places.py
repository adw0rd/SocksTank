"""REST API for user-defined places and training jobs."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.config import settings
from server.places import PlaceStore
from server.schemas import (
    OkResponse,
    PlaceAnnotationsListResponse,
    PlaceAnnotationRecord,
    PlaceAnnotationUpsertRequest,
    PlaceQuickCheckRequest,
    PlaceQuickCheckResponse,
    PlaceQuickCheckClassSummary,
    PlaceQuickCheckImageResult,
    PlaceTrainingJobsResponse,
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
_inference_router = None


def set_store(store: PlaceStore) -> None:
    """Override the default place store (used in tests)."""
    global _store
    _store = store


def get_store() -> PlaceStore:
    """Expose the shared place store to other modules."""
    return _store


def set_dependencies(gpu_manager, local_training_launcher=None, inference_router=None) -> None:
    """Inject shared dependencies from app.py."""
    global _gpu_manager, _local_training_launcher, _inference_router
    _gpu_manager = gpu_manager
    if local_training_launcher is not None:
        _local_training_launcher = local_training_launcher
    if inference_router is not None:
        _inference_router = inference_router


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
    job_dir_path = Path(dataset_path).parent
    job_dir = str(job_dir_path)
    log_path = job_dir_path / "worker.log"
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
        "--epochs",
        "5",
    ]
    with log_path.open("ab") as log_file:
        subprocess.Popen(
            cmd,
            cwd=Path(__file__).resolve().parents[1],
            stdout=log_file,
            stderr=log_file,
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


def _local_artifact_path(job) -> str | None:
    candidates = [job.result_ncnn_path, job.result_model_path]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _maybe_activate_trained_model(job) -> None:
    if job.status is not PlaceJobStatus.READY or _inference_router is None:
        return
    if not settings.auto_accept_enabled:
        return
    if not _quick_check_passes_threshold(job.quick_check):
        return
    target_path = _local_artifact_path(job)
    if target_path is None or settings.model_path == target_path:
        return
    _inference_router.reload_local_model(target_path)


def _quick_check_passes_threshold(quick_check: dict | None) -> bool:
    if not settings.auto_accept_enabled:
        return False
    if not quick_check or quick_check.get("status") != "ok":
        return False
    place_result = quick_check.get("place") or {}
    sock_result = quick_check.get("sock") or {}
    place_hits = int(place_result.get("hits", 0))
    place_total = int(place_result.get("total", 0))
    sock_hits = int(sock_result.get("hits", 0))
    sock_total = int(sock_result.get("total", 0))
    min_samples = max(1, int(settings.auto_accept_quick_check_samples))
    if place_total < min_samples or sock_total < min_samples:
        return False
    if place_hits < int(settings.auto_accept_place_min_hits):
        return False
    if sock_hits < int(settings.auto_accept_sock_min_hits):
        return False
    return True


def _resolve_quick_check_model(place_id: str, explicit_model_path: str | None):
    if explicit_model_path:
        model_path = Path(explicit_model_path)
        if not model_path.is_absolute():
            model_path = Path.cwd() / model_path
        if model_path.exists():
            return str(model_path), None
        raise HTTPException(status_code=400, detail=f"Model not found: {model_path}")

    current_model = settings.model_path
    if current_model:
        current_path = Path(current_model)
        if not current_path.is_absolute():
            current_path = Path.cwd() / current_path
        if current_path.exists() and current_path.suffix.lower() == ".pt":
            return str(current_path), None

    latest_job = _store.get_latest_ready_job(place_id=place_id) or _store.get_latest_ready_job(place_id=None)
    if latest_job is None or not latest_job.result_model_path:
        raise HTTPException(status_code=400, detail="No ready place model found")
    model_path = Path(latest_job.result_model_path)
    if not model_path.is_absolute():
        model_path = Path.cwd() / model_path
    if not model_path.exists():
        raise HTTPException(status_code=400, detail=f"Model not found: {model_path}")
    return str(model_path), latest_job.result_model_version


def _run_quick_check(
    *,
    place_id: str,
    samples: int,
    sock_split: str,
    confidence: float,
    imgsz: int,
    model_path_override: str | None = None,
    strict: bool = True,
) -> PlaceQuickCheckResponse:
    place = _store.get_place(place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    model_path, model_version = _resolve_quick_check_model(place_id, model_path_override)
    place_images = _store.list_images(place_id)
    place_sample_size = samples if strict else min(samples, len(place_images))
    if place_sample_size <= 0:
        raise HTTPException(status_code=400, detail="No place images available for quick check")
    if strict and len(place_images) < samples:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough place images for quick check: found {len(place_images)}, need {samples}",
        )

    place_paths: list[Path] = []
    for image in place_images[:place_sample_size]:
        path = _store.get_image_path(place_id, image.id)
        if path and path.exists():
            place_paths.append(path)
    if strict and len(place_paths) < place_sample_size:
        raise HTTPException(
            status_code=400,
            detail=f"Missing place image files: found {len(place_paths)}, need {place_sample_size}",
        )
    if not strict and not place_paths:
        raise HTTPException(status_code=400, detail="No readable place image files for quick check")

    sock_root = Path("dataset") / sock_split / "images"
    if not sock_root.exists():
        raise HTTPException(status_code=400, detail=f"Sock dataset split not found: {sock_root}")
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    sock_paths = [path for path in sorted(sock_root.iterdir()) if path.is_file() and path.suffix.lower() in allowed]
    sock_sample_size = samples if strict else min(samples, len(sock_paths))
    if strict and len(sock_paths) < samples:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough sock images in {sock_root}: found {len(sock_paths)}, need {samples}",
        )
    if sock_sample_size <= 0:
        raise HTTPException(status_code=400, detail=f"No sock images available in {sock_root}")
    sock_paths = sock_paths[:sock_sample_size]

    from ultralytics import YOLO

    yolo = YOLO(model_path)
    classes = yolo.names if isinstance(yolo.names, dict) else {index: name for index, name in enumerate(yolo.names)}
    sock_class = next((int(k) for k, v in classes.items() if str(v) == "sock"), None)
    place_class = next((int(k) for k, v in classes.items() if str(v).startswith("place")), None)
    if sock_class is None or place_class is None:
        raise HTTPException(status_code=400, detail=f"Unexpected model classes: {classes}")

    def _detect(image_path: Path, target_class: int) -> bool:
        result = yolo.predict(
            source=str(image_path),
            conf=confidence,
            iou=0.45,
            imgsz=imgsz,
            max_det=20,
            verbose=False,
        )[0]
        if result.boxes is None or len(result.boxes) == 0:
            return False
        predicted_classes = [int(value) for value in result.boxes.cls.tolist()]
        return target_class in predicted_classes

    place_results: list[PlaceQuickCheckImageResult] = []
    sock_results: list[PlaceQuickCheckImageResult] = []
    place_hits = 0
    sock_hits = 0

    for image_path in place_paths:
        ok = _detect(image_path, place_class)
        place_hits += int(ok)
        place_results.append(PlaceQuickCheckImageResult(filename=image_path.name, ok=ok))

    for image_path in sock_paths:
        ok = _detect(image_path, sock_class)
        sock_hits += int(ok)
        sock_results.append(PlaceQuickCheckImageResult(filename=image_path.name, ok=ok))

    return PlaceQuickCheckResponse(
        model_path=model_path,
        model_version=model_version,
        place_id=place.id,
        place_label=place.label,
        place=PlaceQuickCheckClassSummary(hits=place_hits, total=len(place_paths)),
        sock=PlaceQuickCheckClassSummary(hits=sock_hits, total=len(sock_paths)),
        place_images=place_results,
        sock_images=sock_results,
    )


def _maybe_store_quick_check(job: PlaceTrainingJob) -> PlaceTrainingJob:
    if job.status is not PlaceJobStatus.READY or job.quick_check is not None:
        return job
    try:
        result = _run_quick_check(
            place_id=job.place_id,
            samples=max(1, int(settings.auto_accept_quick_check_samples)),
            sock_split="train",
            confidence=0.25,
            imgsz=640,
            model_path_override=job.result_model_path,
            strict=False,
        )
        payload = {
            "status": "ok",
            "checked_at": datetime.now(UTC).isoformat(),
            "place_id": result.place_id,
            "place_label": result.place_label,
            "model_path": result.model_path,
            "model_version": result.model_version,
            "place": result.place.model_dump(),
            "sock": result.sock.model_dump(),
            "samples_used": {
                "place": result.place.total,
                "sock": result.sock.total,
            },
        }
        payload["passes_threshold"] = _quick_check_passes_threshold(payload)
    except Exception as exc:
        payload = {
            "status": "failed",
            "checked_at": datetime.now(UTC).isoformat(),
            "error": str(exc),
            "passes_threshold": False,
        }
    updated = _store.update_job(job.id, quick_check=payload)
    return updated or job


def _maybe_backfill_quick_check_threshold(job: PlaceTrainingJob) -> PlaceTrainingJob:
    quick_check = job.quick_check or {}
    if quick_check.get("status") != "ok":
        return job
    if quick_check.get("passes_threshold") is not None:
        return job
    payload = dict(quick_check)
    payload["passes_threshold"] = _quick_check_passes_threshold(payload)
    updated = _store.update_job(job.id, quick_check=payload)
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


@router.get("/{place_id}/jobs", response_model=PlaceTrainingJobsResponse)
async def list_place_jobs(place_id: str, limit: int = 10):
    if _store.get_place(place_id) is None:
        raise HTTPException(status_code=404, detail="Place not found")
    safe_limit = max(1, min(limit, 100))
    jobs = _store.list_jobs(place_id=place_id, limit=safe_limit)
    jobs = [_maybe_backfill_quick_check_threshold(job) for job in jobs]
    return PlaceTrainingJobsResponse(
        items=jobs,
        auto_accept_enabled=settings.auto_accept_enabled,
        auto_accept_quick_check_samples=settings.auto_accept_quick_check_samples,
        auto_accept_place_min_hits=settings.auto_accept_place_min_hits,
        auto_accept_sock_min_hits=settings.auto_accept_sock_min_hits,
    )


@router.post("/quick-check", response_model=PlaceQuickCheckResponse)
async def quick_check_place(body: PlaceQuickCheckRequest):
    return _run_quick_check(
        place_id=body.place_id,
        samples=body.samples,
        sock_split=body.sock_split,
        confidence=body.confidence,
        imgsz=body.imgsz,
        model_path_override=body.model_path,
        strict=True,
    )


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
    job = _maybe_store_quick_check(job)
    job = _maybe_backfill_quick_check_threshold(job)
    _maybe_activate_trained_model(job)
    return job
