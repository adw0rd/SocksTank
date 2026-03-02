"""REST API for user-defined places and training jobs."""

from __future__ import annotations

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


def set_store(store: PlaceStore) -> None:
    """Override the default place store (used in tests)."""
    global _store
    _store = store


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
    del body
    try:
        job = _store.train_place(place_id, base_model="models/yolo11_best.pt")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlaceTrainResponse(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=PlaceTrainingJob)
async def get_place_job(job_id: str):
    job = _store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
