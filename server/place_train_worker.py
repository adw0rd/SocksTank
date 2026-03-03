"""Background training worker for user-defined places."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_status(job_dir: Path, payload: dict) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    status_path = job_dir / "status.json"
    status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


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
