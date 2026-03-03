"""Background training worker for user-defined places."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_status(job_dir: Path, payload: dict) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    status_path = job_dir / "status.json"
    status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _read_label(label_path: Path) -> tuple[int, float, float, float, float] | None:
    raw = label_path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    parts = raw.split()
    if len(parts) != 5:
        return None
    class_id = int(parts[0])
    x_center, y_center, width, height = map(float, parts[1:])
    return class_id, x_center, y_center, width, height


def _write_label(label_path: Path, label: tuple[int, float, float, float, float]) -> None:
    class_id, x_center, y_center, width, height = label
    label_path.write_text(
        f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n",
        encoding="utf-8",
    )


def _augment_training_set(dataset: Path) -> None:
    images_dir = dataset / "images" / "train"
    labels_dir = dataset / "labels" / "train"
    source_images = sorted(
        path for path in images_dir.iterdir() if path.is_file() and not path.stem.endswith(("_bright", "_dark", "_flip"))
    )

    for image_path in source_images:
        label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            continue

        label = _read_label(label_path)
        if label is None:
            continue

        payload = np.fromfile(str(image_path), dtype=np.uint8)
        image = cv2.imdecode(payload, cv2.IMREAD_COLOR)
        if image is None:
            continue

        class_id, x_center, y_center, width, height = label

        bright = cv2.convertScaleAbs(image, alpha=1.08, beta=12)
        cv2.imwrite(str(images_dir / f"{image_path.stem}_bright.jpg"), bright)
        _write_label(labels_dir / f"{image_path.stem}_bright.txt", label)

        dark = cv2.convertScaleAbs(image, alpha=0.92, beta=-12)
        cv2.imwrite(str(images_dir / f"{image_path.stem}_dark.jpg"), dark)
        _write_label(labels_dir / f"{image_path.stem}_dark.txt", label)

        flipped = cv2.flip(image, 1)
        cv2.imwrite(str(images_dir / f"{image_path.stem}_flip.jpg"), flipped)
        flipped_label = (class_id, 1.0 - x_center, y_center, width, height)
        _write_label(labels_dir / f"{image_path.stem}_flip.txt", flipped_label)


def run_worker(dataset: Path, job_dir: Path, base_model: str, device: str, epochs: int) -> int:
    _write_status(
        job_dir,
        {
            "status": "training",
            "started_at": _now(),
            "finished_at": None,
            "error": None,
            "result_model_version": None,
            "result_model_path": None,
        },
    )

    try:
        from ultralytics import YOLO

        _augment_training_set(dataset)

        model = YOLO(base_model)
        model.train(
            data=str(dataset / "data.yaml"),
            epochs=epochs,
            imgsz=640,
            batch=8 if device != "cpu" else 4,
            device=device,
            project=str(job_dir),
            name="train",
            exist_ok=True,
        )

        save_dir = Path(model.trainer.save_dir)
        best_path = save_dir / "weights" / "best.pt"
        result_model_path = str(best_path if best_path.exists() else save_dir)
        model_version = f"{job_dir.name}-v1"
        _write_status(
            job_dir,
            {
                "status": "ready",
                "started_at": None,
                "finished_at": _now(),
                "error": None,
                "result_model_version": model_version,
                "result_model_path": result_model_path,
            },
        )
        return 0
    except Exception as exc:  # pragma: no cover - exercised in runtime, not unit tests
        _write_status(
            job_dir,
            {
                "status": "failed",
                "started_at": None,
                "finished_at": _now(),
                "error": str(exc),
                "result_model_version": None,
                "result_model_path": None,
            },
        )
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a place dataset in the background")
    parser.add_argument("--dataset", required=True, help="Path to the prepared YOLO dataset")
    parser.add_argument("--job-dir", required=True, help="Directory for job status and outputs")
    parser.add_argument("--base-model", required=True, help="Base YOLO model path")
    parser.add_argument("--device", default="cpu", help="Training device (for example, 0 or cpu)")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    args = parser.parse_args()

    return run_worker(
        dataset=Path(args.dataset),
        job_dir=Path(args.job_dir),
        base_model=args.base_model,
        device=args.device,
        epochs=args.epochs,
    )


if __name__ == "__main__":
    raise SystemExit(main())
