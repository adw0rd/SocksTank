"""File-backed storage for user-defined places."""

from __future__ import annotations

import json
import re
import base64
import shutil
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from server.schemas import (
    PlaceAnnotationRecord,
    PlaceAnnotationUpsertRequest,
    PlaceImageUploadItem,
    PlaceImageSummary,
    PlaceJobStatus,
    PlaceStatus,
    PlaceSummary,
    PlaceTrainingJob,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        slug = "place"
    return f"place_{slug}"


class PlaceStore:
    """Persist places, images, annotations, and training jobs under user_data/."""

    def __init__(
        self,
        root: str | Path = "user_data/places",
        base_dataset_root: str | Path | None = "dataset",
        base_train_limit: int = 250,
        base_valid_limit: int = 80,
        base_test_limit: int = 80,
        place_train_repeat: int = 6,
    ) -> None:
        self.root = Path(root)
        self.base_dataset_root = Path(base_dataset_root) if base_dataset_root is not None else None
        self.base_train_limit = max(0, int(base_train_limit))
        self.base_valid_limit = max(0, int(base_valid_limit))
        self.base_test_limit = max(0, int(base_test_limit))
        self.place_train_repeat = max(1, int(place_train_repeat))
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            _write_json(self.index_path, {"active_target_place_id": None, "places": []})
        if not self.jobs_path.exists():
            _write_json(self.jobs_path, {"jobs": []})

    @property
    def index_path(self) -> Path:
        return self.root / "index.json"

    @property
    def jobs_path(self) -> Path:
        return self.root / "jobs.json"

    def _load_index(self) -> dict:
        self._ensure_layout()
        return _read_json(self.index_path, {"active_target_place_id": None, "places": []})

    def _save_index(self, data: dict) -> None:
        _write_json(self.index_path, data)

    def _load_jobs(self) -> dict:
        self._ensure_layout()
        return _read_json(self.jobs_path, {"jobs": []})

    def _save_jobs(self, data: dict) -> None:
        _write_json(self.jobs_path, data)

    def _place_dir(self, place_id: str) -> Path:
        return self.root / place_id

    def _images_dir(self, place_id: str) -> Path:
        return self._place_dir(place_id) / "images"

    def _thumbs_dir(self, place_id: str) -> Path:
        return self._place_dir(place_id) / "thumbs"

    def _images_path(self, place_id: str) -> Path:
        return self._place_dir(place_id) / "images.json"

    def _annotations_path(self, place_id: str) -> Path:
        return self._place_dir(place_id) / "annotations.json"

    def _jobs_root(self) -> Path:
        return self.root / "jobs"

    def _job_dir(self, job_id: str) -> Path:
        return self._jobs_root() / job_id

    def list_places(self) -> tuple[str | None, list[PlaceSummary]]:
        data = self._load_index()
        active_id = data.get("active_target_place_id")
        return active_id, [PlaceSummary.model_validate(item) for item in data["places"]]

    def get_place(self, place_id: str) -> PlaceSummary | None:
        _, places = self.list_places()
        for place in places:
            if place.id == place_id:
                return place
        return None

    def get_active_target(self) -> PlaceSummary | None:
        active_id, places = self.list_places()
        if active_id is None:
            return None
        for place in places:
            if place.id == active_id:
                return place
        return None

    def get_active_target_label(self) -> str | None:
        active_place = self.get_active_target()
        if active_place is None:
            return None
        return active_place.label

    def create_place(self, name: str) -> PlaceSummary:
        data = self._load_index()
        place_id = f"place_{uuid4().hex[:8]}"
        now = _now()
        place = PlaceSummary(
            id=place_id,
            name=name.strip(),
            label=_slugify(name),
            status=PlaceStatus.DRAFT,
            model_version=None,
            image_count=0,
            is_active_target=False,
            created_at=now,
            updated_at=now,
        )
        data["places"].append(place.model_dump(mode="json"))
        self._save_index(data)
        _write_json(self._images_path(place_id), {"items": []})
        _write_json(self._annotations_path(place_id), {"items": []})
        self._images_dir(place_id).mkdir(parents=True, exist_ok=True)
        self._thumbs_dir(place_id).mkdir(parents=True, exist_ok=True)
        return place

    def update_place(self, place_id: str, name: str) -> PlaceSummary | None:
        data = self._load_index()
        for item in data["places"]:
            if item["id"] != place_id:
                continue
            item["name"] = name.strip()
            item["updated_at"] = _now().isoformat()
            self._save_index(data)
            return PlaceSummary.model_validate(item)
        return None

    def delete_place(self, place_id: str) -> bool:
        data = self._load_index()
        original_len = len(data["places"])
        data["places"] = [item for item in data["places"] if item["id"] != place_id]
        if len(data["places"]) == original_len:
            return False
        if data.get("active_target_place_id") == place_id:
            data["active_target_place_id"] = None
        self._save_index(data)
        place_dir = self._place_dir(place_id)
        if place_dir.exists():
            for path in sorted(place_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            place_dir.rmdir()
        jobs = self._load_jobs()
        jobs["jobs"] = [job for job in jobs["jobs"] if job["place_id"] != place_id]
        self._save_jobs(jobs)
        return True

    def add_images(self, place_id: str, files: list[PlaceImageUploadItem]) -> list[PlaceImageSummary]:
        if self.get_place(place_id) is None:
            raise KeyError(place_id)
        images_data = _read_json(self._images_path(place_id), {"items": []})
        created: list[PlaceImageSummary] = []
        target_dir = self._images_dir(place_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        for upload in files:
            suffix = Path(upload.filename).suffix.lower() or ".jpg"
            image_id = f"img_{uuid4().hex[:8]}"
            filename = f"{image_id}{suffix}"
            payload = base64.b64decode(upload.content_base64)
            file_path = target_dir / filename
            file_path.write_bytes(payload)
            image = PlaceImageSummary(
                id=image_id,
                filename=filename,
                path=str(Path("user_data") / "places" / place_id / "images" / filename),
                width=0,
                height=0,
                annotated=False,
                created_at=_now(),
            )
            images_data["items"].append(image.model_dump(mode="json"))
            created.append(image)
        _write_json(self._images_path(place_id), images_data)
        self._update_place_counters(place_id)
        return created

    def list_images(self, place_id: str) -> list[PlaceImageSummary]:
        if self.get_place(place_id) is None:
            raise KeyError(place_id)
        data = _read_json(self._images_path(place_id), {"items": []})
        return [PlaceImageSummary.model_validate(item) for item in data["items"]]

    def get_image_path(self, place_id: str, image_id: str) -> Path | None:
        for image in self.list_images(place_id):
            if image.id == image_id:
                return self._images_dir(place_id) / image.filename
        return None

    def get_thumbnail_path(self, place_id: str, image_id: str, max_side: int = 256) -> Path | None:
        image_path = self.get_image_path(place_id, image_id)
        if image_path is None or not image_path.exists():
            return None

        thumb_dir = self._thumbs_dir(place_id)
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{image_id}_{max_side}.jpg"
        if thumb_path.exists():
            return thumb_path

        payload = np.fromfile(str(image_path), dtype=np.uint8)
        image = cv2.imdecode(payload, cv2.IMREAD_COLOR)
        if image is None:
            return None

        height, width = image.shape[:2]
        scale = min(max_side / max(width, 1), max_side / max(height, 1), 1.0)
        target_w = max(1, int(width * scale))
        target_h = max(1, int(height * scale))
        resized = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            return None
        thumb_path.write_bytes(encoded.tobytes())
        return thumb_path

    def delete_image(self, place_id: str, image_id: str) -> bool:
        place = self.get_place(place_id)
        if place is None:
            raise KeyError(place_id)

        images_data = _read_json(self._images_path(place_id), {"items": []})
        image_entry = next((item for item in images_data["items"] if item["id"] == image_id), None)
        if image_entry is None:
            return False

        images_data["items"] = [item for item in images_data["items"] if item["id"] != image_id]
        _write_json(self._images_path(place_id), images_data)

        image_path = self._images_dir(place_id) / image_entry["filename"]
        if image_path.exists():
            image_path.unlink()

        thumbs_dir = self._thumbs_dir(place_id)
        if thumbs_dir.exists():
            for thumb_path in thumbs_dir.glob(f"{image_id}_*.jpg"):
                thumb_path.unlink()

        annotations_data = _read_json(self._annotations_path(place_id), {"items": []})
        annotations_data["items"] = [item for item in annotations_data["items"] if item["place_image_id"] != image_id]
        _write_json(self._annotations_path(place_id), annotations_data)

        self._update_place_counters(place_id)
        return True

    def upsert_annotation(self, place_id: str, image_id: str, body: PlaceAnnotationUpsertRequest) -> PlaceAnnotationRecord:
        place = self.get_place(place_id)
        if place is None:
            raise KeyError(place_id)
        image = next((img for img in self.list_images(place_id) if img.id == image_id), None)
        if image is None:
            raise FileNotFoundError(image_id)
        data = _read_json(self._annotations_path(place_id), {"items": []})
        now = _now()
        record = None
        for item in data["items"]:
            if item["place_image_id"] != image_id:
                continue
            item.update(body.model_dump())
            item["updated_at"] = now.isoformat()
            record = PlaceAnnotationRecord.model_validate(item)
            break
        if record is None:
            record = PlaceAnnotationRecord(
                id=f"ann_{uuid4().hex[:8]}",
                place_image_id=image_id,
                label=place.label,
                x_center=body.x_center,
                y_center=body.y_center,
                width=body.width,
                height=body.height,
                created_at=now,
                updated_at=now,
            )
            data["items"].append(record.model_dump(mode="json"))
        _write_json(self._annotations_path(place_id), data)
        self._set_image_annotated(place_id, image_id, True)
        self._set_place_status(place_id, PlaceStatus.ANNOTATING)
        return record

    def list_annotations(self, place_id: str) -> list[PlaceAnnotationRecord]:
        if self.get_place(place_id) is None:
            raise KeyError(place_id)
        data = _read_json(self._annotations_path(place_id), {"items": []})
        return [PlaceAnnotationRecord.model_validate(item) for item in data["items"]]

    def train_place(self, place_id: str, base_model: str, executor: str) -> PlaceTrainingJob:
        place = self.get_place(place_id)
        if place is None:
            raise KeyError(place_id)
        images = self.list_images(place_id)
        annotations = self.list_annotations(place_id)
        if not images:
            raise ValueError("Place has no images")
        if len(annotations) != len(images):
            raise ValueError("All images must be annotated before training")
        jobs = self._load_jobs()
        now = _now()
        job_id = f"job_{uuid4().hex[:8]}"
        dataset_path = self._build_training_dataset(job_id, place, images, annotations)
        job = PlaceTrainingJob(
            id=job_id,
            place_id=place_id,
            executor=executor,
            status=PlaceJobStatus.QUEUED,
            dataset_path=str(dataset_path),
            remote_dataset_path=None,
            remote_host=None,
            queued_at=now,
            started_at=None,
            finished_at=None,
            error=None,
            base_model=base_model,
            result_model_version=None,
            result_model_path=None,
            result_ncnn_path=None,
        )
        jobs["jobs"].append(job.model_dump(mode="json"))
        self._save_jobs(jobs)
        self._set_place_status(place_id, PlaceStatus.QUEUED)
        return job

    def update_job(
        self,
        job_id: str,
        *,
        executor: str | None = None,
        status: PlaceJobStatus | None = None,
        remote_dataset_path: str | None = None,
        remote_host: str | None = None,
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        clear_finished_at: bool = False,
        result_model_version: str | None = None,
        result_model_path: str | None = None,
        result_ncnn_path: str | None = None,
    ) -> PlaceTrainingJob | None:
        jobs = self._load_jobs()
        updated = None
        for item in jobs["jobs"]:
            if item["id"] != job_id:
                continue
            if executor is not None:
                item["executor"] = executor
            if status is not None:
                item["status"] = status.value
            if remote_dataset_path is not None:
                item["remote_dataset_path"] = remote_dataset_path
            if remote_host is not None:
                item["remote_host"] = remote_host
            if error is not None:
                item["error"] = error
            if started_at is not None:
                item["started_at"] = started_at.isoformat()
            if finished_at is not None:
                item["finished_at"] = finished_at.isoformat()
            elif clear_finished_at:
                item["finished_at"] = None
            if result_model_version is not None:
                item["result_model_version"] = result_model_version
            if result_model_path is not None:
                item["result_model_path"] = result_model_path
            if result_ncnn_path is not None:
                item["result_ncnn_path"] = result_ncnn_path
            updated = PlaceTrainingJob.model_validate(item)
            break
        if updated is None:
            return None
        self._save_jobs(jobs)
        if status is not None:
            if status is PlaceJobStatus.READY:
                self._set_place_ready(updated.place_id, updated.result_model_version or "")
            elif status is PlaceJobStatus.FAILED:
                self._set_place_status(updated.place_id, PlaceStatus.FAILED)
            elif status is PlaceJobStatus.TRAINING:
                self._set_place_status(updated.place_id, PlaceStatus.TRAINING)
            elif status is PlaceJobStatus.QUEUED:
                self._set_place_status(updated.place_id, PlaceStatus.QUEUED)
        return updated

    def _build_training_dataset(
        self,
        job_id: str,
        place: PlaceSummary,
        images: list[PlaceImageSummary],
        annotations: list[PlaceAnnotationRecord],
    ) -> Path:
        job_dir = self._job_dir(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir)

        dataset_dir = job_dir / "dataset"
        for split in ("train", "valid", "test"):
            (dataset_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (dataset_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

        self._copy_base_sock_dataset(dataset_dir)

        annotations_by_image = {record.place_image_id: record for record in annotations}
        for image in images:
            source_path = self._images_dir(place.id) / image.filename
            record = annotations_by_image.get(image.id)
            if record is None:
                raise ValueError(f"Missing annotation for image {image.id}")
            prefixed_name = f"{place.id}_{image.filename}"
            for split in ("train", "valid"):
                repeat = self.place_train_repeat if split == "train" else 1
                for i in range(repeat):
                    stem = Path(prefixed_name).stem
                    suffix = Path(prefixed_name).suffix
                    repeated_name = f"{stem}_p{i}{suffix}" if split == "train" else prefixed_name
                    target_path = dataset_dir / "images" / split / repeated_name
                    shutil.copy2(source_path, target_path)
                    label_path = dataset_dir / "labels" / split / f"{Path(repeated_name).stem}.txt"
                    label_line = f"1 {record.x_center:.6f} {record.y_center:.6f} {record.width:.6f} {record.height:.6f}\n"
                    label_path.write_text(label_line, encoding="utf-8")

        data_yaml = dataset_dir / "data.yaml"
        data_yaml.write_text(
            "\n".join(
                [
                    "path: .",
                    "train: images/train",
                    "val: images/valid",
                    "test: images/test",
                    "names:",
                    "  0: sock",
                    f"  1: {place.label}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return dataset_dir

    def _copy_base_sock_dataset(self, dataset_dir: Path) -> None:
        if self.base_dataset_root is None:
            return
        if not self.base_dataset_root.exists():
            return

        split_limits = {
            "train": self.base_train_limit,
            "valid": self.base_valid_limit,
            "test": self.base_test_limit,
        }

        for source_split, target_split in (("train", "train"), ("valid", "valid"), ("test", "test")):
            source_images = self.base_dataset_root / source_split / "images"
            source_labels = self.base_dataset_root / source_split / "labels"
            if not source_images.exists() or not source_labels.exists():
                continue

            target_images = dataset_dir / "images" / target_split
            target_labels = dataset_dir / "labels" / target_split

            image_paths = [p for p in sorted(source_images.iterdir()) if p.is_file()]
            label_paths = [p for p in sorted(source_labels.iterdir()) if p.is_file()]
            limit = split_limits.get(source_split, 0)
            if limit > 0:
                image_paths = image_paths[:limit]
                label_paths = label_paths[:limit]

            for image_path in image_paths:
                if not image_path.is_file():
                    continue
                shutil.copy2(image_path, target_images / image_path.name)

            for label_path in label_paths:
                if not label_path.is_file():
                    continue
                shutil.copy2(label_path, target_labels / label_path.name)

    def get_job(self, job_id: str) -> PlaceTrainingJob | None:
        jobs = self._load_jobs()
        for item in jobs["jobs"]:
            if item["id"] == job_id:
                return PlaceTrainingJob.model_validate(item)
        return None

    def set_active_target(self, place_id: str | None) -> str | None:
        data = self._load_index()
        if place_id is not None:
            target = next((item for item in data["places"] if item["id"] == place_id), None)
            if target is None:
                raise KeyError(place_id)
            if target["status"] != PlaceStatus.READY.value:
                raise ValueError("Only ready places can be selected as active targets")
        data["active_target_place_id"] = place_id
        for item in data["places"]:
            item["is_active_target"] = item["id"] == place_id
            if item["id"] == place_id:
                item["updated_at"] = _now().isoformat()
        self._save_index(data)
        return place_id

    def _update_place_counters(self, place_id: str) -> None:
        data = self._load_index()
        count = len(_read_json(self._images_path(place_id), {"items": []})["items"])
        for item in data["places"]:
            if item["id"] != place_id:
                continue
            item["image_count"] = count
            item["updated_at"] = _now().isoformat()
            if item["status"] == PlaceStatus.DRAFT.value and count:
                item["status"] = PlaceStatus.ANNOTATING.value
        self._save_index(data)

    def _set_image_annotated(self, place_id: str, image_id: str, value: bool) -> None:
        data = _read_json(self._images_path(place_id), {"items": []})
        for item in data["items"]:
            if item["id"] == image_id:
                item["annotated"] = value
        _write_json(self._images_path(place_id), data)

    def _set_place_status(self, place_id: str, status: PlaceStatus) -> None:
        data = self._load_index()
        for item in data["places"]:
            if item["id"] == place_id:
                item["status"] = status.value
                item["updated_at"] = _now().isoformat()
        self._save_index(data)

    def _set_place_ready(self, place_id: str, model_version: str) -> None:
        data = self._load_index()
        for item in data["places"]:
            if item["id"] == place_id:
                item["status"] = PlaceStatus.READY.value
                if model_version:
                    item["model_version"] = model_version
                item["updated_at"] = _now().isoformat()
        self._save_index(data)
