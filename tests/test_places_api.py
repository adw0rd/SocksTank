"""API tests for the places MVP routes."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from datetime import UTC, datetime
from unittest import mock

import cv2
import numpy as np

from fastapi import FastAPI
from fastapi.testclient import TestClient

import server.routes_places as routes_places
from server.places import PlaceStore
from server.routes_places import router, set_dependencies, set_store
from server.schemas import (
    GPUServerSchema,
    PlaceQuickCheckClassSummary,
    PlaceQuickCheckImageResult,
    PlaceQuickCheckResponse,
)


class PlacesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = PlaceStore(Path(self._tmp.name) / "places", base_dataset_root=None)
        set_store(self.store)
        self.inference_router = type(
            "FakeInferenceRouter",
            (),
            {
                "__init__": lambda self: setattr(self, "reloaded_paths", []),
                "reload_local_model": lambda self, path: self.reloaded_paths.append(path) or True,
            },
        )()

        def fake_local_launcher(dataset_path: str, base_model: str):
            job_dir = Path(dataset_path).parent
            weights_dir = job_dir / "train" / "weights"
            weights_dir.mkdir(parents=True, exist_ok=True)
            (weights_dir / "best.pt").write_text("pt", encoding="utf-8")
            (weights_dir / "best_ncnn_model").mkdir(exist_ok=True)
            (job_dir / "status.json").write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "started_at": datetime.now(UTC).isoformat(),
                        "finished_at": datetime.now(UTC).isoformat(),
                        "error": None,
                        "result_model_version": f"{job_dir.name}-v1",
                        "result_model_path": str(job_dir / "train" / "weights" / "best.pt"),
                        "result_ncnn_path": str(job_dir / "train" / "weights" / "best_ncnn_model"),
                    }
                ),
                encoding="utf-8",
            )
            return {"ok": True}

        set_dependencies(None, local_training_launcher=fake_local_launcher, inference_router=self.inference_router)
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _ok_quick_check(self, place_id: str, label: str) -> PlaceQuickCheckResponse:
        return PlaceQuickCheckResponse(
            model_path="/tmp/best.pt",
            model_version="test-v1",
            place_id=place_id,
            place_label=label,
            place=PlaceQuickCheckClassSummary(hits=5, total=5),
            sock=PlaceQuickCheckClassSummary(hits=5, total=5),
            place_images=[PlaceQuickCheckImageResult(filename="p.jpg", ok=True)],
            sock_images=[PlaceQuickCheckImageResult(filename="s.jpg", ok=True)],
        )

    def _create_annotated_place(self, name: str = "Place") -> tuple[str, dict]:
        image = np.zeros((32, 32, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)
        jpeg_bytes = encoded.tobytes()

        create = self.client.post("/api/places", json={"name": name})
        self.assertEqual(create.status_code, 200)
        place = create.json()
        place_id = place["id"]
        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": f"{name.lower()}.jpg",
                        "content_base64": base64.b64encode(jpeg_bytes).decode("ascii"),
                    }
                ]
            },
        )
        self.assertEqual(upload.status_code, 200)
        image_id = upload.json()["items"][0]["id"]
        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={"x_center": 0.5, "y_center": 0.5, "width": 0.4, "height": 0.4},
        )
        self.assertEqual(annotate.status_code, 200)
        return place_id, place

    def test_full_place_flow(self) -> None:
        image = np.zeros((40, 60, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)
        jpeg_bytes = encoded.tobytes()

        create = self.client.post("/api/places", json={"name": "Washing Machine"})
        self.assertEqual(create.status_code, 200)
        place = create.json()
        place_id = place["id"]
        self.assertEqual(place["label"], "place_washing_machine")

        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "washer.jpg",
                        "content_base64": base64.b64encode(jpeg_bytes).decode("ascii"),
                    }
                ]
            },
        )
        self.assertEqual(upload.status_code, 200)
        image = upload.json()["items"][0]
        image_id = image["id"]

        image_fetch = self.client.get(f"/api/places/{place_id}/images/{image_id}")
        self.assertEqual(image_fetch.status_code, 200)
        self.assertEqual(image_fetch.content, jpeg_bytes)

        thumb_fetch = self.client.get(f"/api/places/{place_id}/images/{image_id}/thumb")
        self.assertEqual(thumb_fetch.status_code, 200)

        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={
                "x_center": 0.5,
                "y_center": 0.5,
                "width": 0.4,
                "height": 0.4,
            },
        )
        self.assertEqual(annotate.status_code, 200)
        self.assertEqual(annotate.json()["place_image_id"], image_id)

        delete = self.client.delete(f"/api/places/{place_id}/images/{image_id}")
        self.assertEqual(delete.status_code, 200)

        images_after_delete = self.client.get(f"/api/places/{place_id}/images")
        self.assertEqual(images_after_delete.status_code, 200)
        self.assertEqual(images_after_delete.json()["items"], [])

        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "washer.jpg",
                        "content_base64": base64.b64encode(jpeg_bytes).decode("ascii"),
                    }
                ]
            },
        )
        self.assertEqual(upload.status_code, 200)
        image_id = upload.json()["items"][0]["id"]

        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={
                "x_center": 0.5,
                "y_center": 0.5,
                "width": 0.4,
                "height": 0.4,
            },
        )
        self.assertEqual(annotate.status_code, 200)

        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        train_payload = train.json()
        self.assertEqual(train_payload["status"], "training")
        self.assertEqual(train_payload["executor"], "local:rpi5")

        with mock.patch.object(routes_places, "_run_quick_check", return_value=self._ok_quick_check(place_id, place["label"])):
            job = self.client.get(f"/api/places/jobs/{train_payload['job_id']}")
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["status"], "ready")
        self.assertTrue(job.json()["dataset_path"].endswith("/dataset"))
        self.assertTrue(job.json()["result_ncnn_path"].endswith("/best_ncnn_model"))
        self.assertTrue(self.inference_router.reloaded_paths)
        self.assertEqual(self.inference_router.reloaded_paths[-1], job.json()["result_ncnn_path"])

        activate = self.client.put("/api/places/active", json={"place_id": place_id})
        self.assertEqual(activate.status_code, 200)
        self.assertEqual(activate.json()["active_target_place_id"], place_id)

        listing = self.client.get("/api/places")
        self.assertEqual(listing.status_code, 200)
        payload = listing.json()
        self.assertEqual(payload["active_target_place_id"], place_id)
        self.assertEqual(payload["items"][0]["status"], "ready")
        self.assertTrue(payload["items"][0]["is_active_target"])

    def test_training_prefers_online_gpu_server(self) -> None:
        class FakeGpuManager:
            def __init__(self):
                self.servers = [
                    GPUServerSchema(
                        name="blackops",
                        host="192.168.0.124",
                        username="user",
                        status="online",
                        gpu="RTX",
                    )
                ]

            def stage_place_training_dataset(self, host: str, dataset_path: str, job_id: str):
                self.last_stage = (host, dataset_path, job_id)
                return {"ok": True, "remote_dataset_path": f"/remote/{job_id}/dataset"}

            def start_place_training(self, host: str, job_id: str, remote_dataset_path: str, base_model: str):
                self.remote_status = {
                    "status": "ready",
                    "started_at": datetime.now(UTC).isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": None,
                    "result_model_version": f"{job_id}-v1",
                    "result_model_path": f"/remote/{job_id}/weights/best.pt",
                }
                return {"ok": True}

            def read_place_training_status(self, host: str, job_id: str):
                return {"ok": True, "status": self.remote_status}

            def fetch_place_training_artifacts(
                self,
                host: str,
                *,
                remote_model_path: str | None,
                remote_ncnn_path: str | None,
                local_job_dir,
            ):
                local_root = Path(local_job_dir) / "artifacts"
                local_root.mkdir(parents=True, exist_ok=True)
                model_path = local_root / "best.pt"
                ncnn_path = local_root / "best_ncnn_model"
                model_path.write_text("pt", encoding="utf-8")
                ncnn_path.mkdir(exist_ok=True)
                return {
                    "ok": True,
                    "result_model_path": str(model_path),
                    "result_ncnn_path": str(ncnn_path),
                }

        set_dependencies(FakeGpuManager())

        image = np.zeros((20, 20, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)

        create = self.client.post("/api/places", json={"name": "Washer"})
        place_id = create.json()["id"]
        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "washer.jpg",
                        "content_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
                    }
                ]
            },
        )
        image_id = upload.json()["items"][0]["id"]
        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={"x_center": 0.5, "y_center": 0.5, "width": 0.4, "height": 0.4},
        )
        self.assertEqual(annotate.status_code, 200)

        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        self.assertEqual(train.json()["executor"], "remote:blackops")
        self.assertEqual(train.json()["status"], "training")

        job = self.client.get(f"/api/places/jobs/{train.json()['job_id']}")
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["remote_dataset_path"], f"/remote/{train.json()['job_id']}/dataset")
        self.assertEqual(job.json()["status"], "ready")
        self.assertTrue(job.json()["result_model_path"].endswith("/artifacts/best.pt"))
        self.assertTrue(job.json()["result_ncnn_path"].endswith("/artifacts/best_ncnn_model"))

    def test_training_falls_back_to_local_when_remote_staging_fails(self) -> None:
        class FakeGpuManager:
            def __init__(self):
                self.servers = [
                    GPUServerSchema(
                        name="blackops",
                        host="192.168.0.124",
                        username="user",
                        status="online",
                        gpu="RTX",
                    )
                ]

            def stage_place_training_dataset(self, host: str, dataset_path: str, job_id: str):
                return {"ok": False, "error": "SSH failed"}

        set_dependencies(FakeGpuManager())

        image = np.zeros((20, 20, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)

        create = self.client.post("/api/places", json={"name": "Dryer"})
        place_id = create.json()["id"]
        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "dryer.jpg",
                        "content_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
                    }
                ]
            },
        )
        image_id = upload.json()["items"][0]["id"]
        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={"x_center": 0.5, "y_center": 0.5, "width": 0.4, "height": 0.4},
        )
        self.assertEqual(annotate.status_code, 200)

        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        self.assertEqual(train.json()["executor"], "local:rpi5")

        job = self.client.get(f"/api/places/jobs/{train.json()['job_id']}")
        self.assertEqual(job.status_code, 200)
        self.assertIsNone(job.json()["remote_dataset_path"])
        self.assertIn("Remote dataset staging failed", job.json()["error"])

    def test_training_falls_back_to_local_when_remote_gpu_is_busy(self) -> None:
        class FakeGpuManager:
            def __init__(self):
                self.servers = [
                    GPUServerSchema(
                        name="blackops",
                        host="192.168.0.124",
                        username="user",
                        status="online",
                        gpu="RTX",
                    )
                ]

            def stage_place_training_dataset(self, host: str, dataset_path: str, job_id: str):
                return {"ok": True, "remote_dataset_path": f"/remote/{job_id}/dataset"}

            def start_place_training(self, host: str, job_id: str, remote_dataset_path: str, base_model: str):
                return {"ok": True}

            def read_place_training_status(self, host: str, job_id: str):
                return {
                    "ok": True,
                    "status": {
                        "status": "failed",
                        "started_at": datetime.now(UTC).isoformat(),
                        "finished_at": datetime.now(UTC).isoformat(),
                        "error": "CUDA-capable device(s) is/are busy or unavailable",
                        "result_model_version": None,
                        "result_model_path": None,
                        "result_ncnn_path": None,
                    },
                }

            def fetch_place_training_artifacts(
                self,
                host: str,
                *,
                remote_model_path: str | None,
                remote_ncnn_path: str | None,
                local_job_dir,
            ):
                return {"ok": False, "error": "not used"}

        set_dependencies(FakeGpuManager())

        image = np.zeros((20, 20, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)

        create = self.client.post("/api/places", json={"name": "Washer"})
        place_id = create.json()["id"]
        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "washer.jpg",
                        "content_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
                    }
                ]
            },
        )
        image_id = upload.json()["items"][0]["id"]
        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={"x_center": 0.5, "y_center": 0.5, "width": 0.4, "height": 0.4},
        )
        self.assertEqual(annotate.status_code, 200)

        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        self.assertEqual(train.json()["executor"], "remote:blackops")

        job = self.client.get(f"/api/places/jobs/{train.json()['job_id']}")
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["executor"], "local:rpi5")
        self.assertEqual(job.json()["status"], "training")
        self.assertIn("Remote training fallback", job.json()["error"])

    def test_training_requires_annotations(self) -> None:
        create = self.client.post("/api/places", json={"name": "Laundry Basket"})
        place_id = create.json()["id"]
        self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "basket.jpg",
                        "content_base64": base64.b64encode(b"fake-image-bytes").decode("ascii"),
                    }
                ]
            },
        )

        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 400)
        self.assertIn("annotated", train.json()["detail"])

    def test_quick_check_uses_selected_place_id(self) -> None:
        image = np.zeros((24, 24, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)
        jpeg_bytes = encoded.tobytes()

        create = self.client.post("/api/places", json={"name": "Base1"})
        self.assertEqual(create.status_code, 200)
        place_id = create.json()["id"]
        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "base1.jpg",
                        "content_base64": base64.b64encode(jpeg_bytes).decode("ascii"),
                    }
                ]
            },
        )
        self.assertEqual(upload.status_code, 200)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_path = tmp_path / "best.pt"
            model_path.write_text("fake", encoding="utf-8")
            sock_dir = tmp_path / "dataset" / "train" / "images"
            sock_dir.mkdir(parents=True, exist_ok=True)
            (sock_dir / "sock.jpg").write_bytes(jpeg_bytes)

            class _FakeList:
                def __init__(self, values):
                    self._values = values

                def tolist(self):
                    return self._values

            class _FakeBoxes:
                def __init__(self, cls_values):
                    self.cls = _FakeList(cls_values)

                def __len__(self):
                    return len(self.cls.tolist())

            class _FakeResult:
                def __init__(self, cls_values):
                    self.boxes = _FakeBoxes(cls_values)

            class FakeYOLO:
                def __init__(self, _model_path):
                    self.names = {0: "sock", 1: "place_base1"}

                def predict(self, source: str, **_kwargs):
                    normalized = source.replace("\\", "/")
                    if "/places/" in normalized:
                        return [_FakeResult([1])]
                    return [_FakeResult([0])]

            prev_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                with mock.patch("ultralytics.YOLO", FakeYOLO):
                    response = self.client.post(
                        "/api/places/quick-check",
                        json={
                            "place_id": place_id,
                            "samples": 1,
                            "model_path": str(model_path),
                            "sock_split": "train",
                        },
                    )
            finally:
                os.chdir(prev_cwd)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["place"]["hits"], 1)
        self.assertEqual(payload["place"]["total"], 1)
        self.assertEqual(payload["sock"]["hits"], 1)
        self.assertEqual(payload["sock"]["total"], 1)

    def test_list_place_jobs_returns_policy_and_recent_jobs(self) -> None:
        image = np.zeros((24, 24, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)
        jpeg_bytes = encoded.tobytes()

        create = self.client.post("/api/places", json={"name": "History"})
        place_id = create.json()["id"]
        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "history.jpg",
                        "content_base64": base64.b64encode(jpeg_bytes).decode("ascii"),
                    }
                ]
            },
        )
        image_id = upload.json()["items"][0]["id"]
        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={"x_center": 0.5, "y_center": 0.5, "width": 0.4, "height": 0.4},
        )
        self.assertEqual(annotate.status_code, 200)

        train = self.client.post(f"/api/places/{place_id}/train", json={})
        job_id = train.json()["job_id"]
        with mock.patch.object(routes_places, "_run_quick_check", return_value=self._ok_quick_check(place_id, "place_history")):
            self.client.get(f"/api/places/jobs/{job_id}")

        response = self.client.get(f"/api/places/{place_id}/jobs?limit=10")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["auto_accept_enabled"])
        self.assertEqual(payload["auto_accept_quick_check_samples"], 5)
        self.assertEqual(payload["items"][0]["id"], job_id)

    def test_activate_requires_ready_place(self) -> None:
        create = self.client.post("/api/places", json={"name": "Dryer"})
        place_id = create.json()["id"]

        activate = self.client.put("/api/places/active", json={"place_id": place_id})
        self.assertEqual(activate.status_code, 409)

    def test_ready_job_does_not_auto_activate_when_quick_check_below_threshold(self) -> None:
        image = np.zeros((32, 32, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)
        jpeg_bytes = encoded.tobytes()

        create = self.client.post("/api/places", json={"name": "Washer"})
        place = create.json()
        place_id = place["id"]
        upload = self.client.post(
            f"/api/places/{place_id}/images",
            json={
                "items": [
                    {
                        "filename": "washer.jpg",
                        "content_base64": base64.b64encode(jpeg_bytes).decode("ascii"),
                    }
                ]
            },
        )
        image_id = upload.json()["items"][0]["id"]
        annotate = self.client.put(
            f"/api/places/{place_id}/images/{image_id}/annotation",
            json={"x_center": 0.5, "y_center": 0.5, "width": 0.4, "height": 0.4},
        )
        self.assertEqual(annotate.status_code, 200)

        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        job_id = train.json()["job_id"]
        low_score = PlaceQuickCheckResponse(
            model_path="/tmp/best.pt",
            model_version="test-v1",
            place_id=place_id,
            place_label=place["label"],
            place=PlaceQuickCheckClassSummary(hits=3, total=5),
            sock=PlaceQuickCheckClassSummary(hits=5, total=5),
            place_images=[PlaceQuickCheckImageResult(filename="p.jpg", ok=True)],
            sock_images=[PlaceQuickCheckImageResult(filename="s.jpg", ok=True)],
        )
        with mock.patch.object(routes_places, "_run_quick_check", return_value=low_score):
            job = self.client.get(f"/api/places/jobs/{job_id}")
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["status"], "ready")
        self.assertEqual(self.inference_router.reloaded_paths, [])

    def test_backfills_passes_threshold_for_legacy_quick_check_payload(self) -> None:
        place_id, place = self._create_annotated_place("Legacy")
        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        job_id = train.json()["job_id"]

        with mock.patch.object(routes_places, "_run_quick_check", return_value=self._ok_quick_check(place_id, place["label"])):
            self.client.get(f"/api/places/jobs/{job_id}")

        # Simulate old payload written before passes_threshold was introduced.
        stripped_quick_check = {
            "status": "ok",
            "place": {"hits": 5, "total": 5},
            "sock": {"hits": 5, "total": 5},
        }
        self.store.update_job(job_id, quick_check=stripped_quick_check)

        listing = self.client.get(f"/api/places/{place_id}/jobs?limit=10")
        self.assertEqual(listing.status_code, 200)
        item = listing.json()["items"][0]
        self.assertTrue(item["quick_check"]["passes_threshold"])

    def test_list_place_jobs_respects_limit_and_sorting(self) -> None:
        place_id, place = self._create_annotated_place("Sorter")

        train1 = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train1.status_code, 200)
        with mock.patch.object(routes_places, "_run_quick_check", return_value=self._ok_quick_check(place_id, place["label"])):
            self.client.get(f"/api/places/jobs/{train1.json()['job_id']}")

        train2 = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train2.status_code, 200)
        with mock.patch.object(routes_places, "_run_quick_check", return_value=self._ok_quick_check(place_id, place["label"])):
            self.client.get(f"/api/places/jobs/{train2.json()['job_id']}")

        listing = self.client.get(f"/api/places/{place_id}/jobs?limit=1")
        self.assertEqual(listing.status_code, 200)
        items = listing.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], train2.json()["job_id"])

    def test_quick_check_failure_stored_and_blocks_auto_activation(self) -> None:
        place_id, _place = self._create_annotated_place("FailQC")
        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        job_id = train.json()["job_id"]

        with mock.patch.object(routes_places, "_run_quick_check", side_effect=RuntimeError("boom")):
            job = self.client.get(f"/api/places/jobs/{job_id}")
        self.assertEqual(job.status_code, 200)
        payload = job.json()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["quick_check"]["status"], "failed")
        self.assertEqual(payload["quick_check"]["passes_threshold"], False)
        self.assertEqual(self.inference_router.reloaded_paths, [])

    def test_auto_quick_check_handles_low_sample_count_with_strict_false(self) -> None:
        place_id, place = self._create_annotated_place("TinySet")
        train = self.client.post(f"/api/places/{place_id}/train", json={})
        self.assertEqual(train.status_code, 200)
        job_id = train.json()["job_id"]

        tiny_result = PlaceQuickCheckResponse(
            model_path="/tmp/best.pt",
            model_version="tiny-v1",
            place_id=place_id,
            place_label=place["label"],
            place=PlaceQuickCheckClassSummary(hits=1, total=1),
            sock=PlaceQuickCheckClassSummary(hits=1, total=1),
            place_images=[PlaceQuickCheckImageResult(filename="p.jpg", ok=True)],
            sock_images=[PlaceQuickCheckImageResult(filename="s.jpg", ok=True)],
        )

        with (
            mock.patch.object(routes_places.settings, "auto_accept_quick_check_samples", 5),
            mock.patch.object(routes_places, "_run_quick_check", return_value=tiny_result) as run_qc,
        ):
            job = self.client.get(f"/api/places/jobs/{job_id}")
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["quick_check"]["status"], "ok")
        self.assertEqual(job.json()["quick_check"]["samples_used"]["place"], 1)
        self.assertFalse(job.json()["quick_check"]["passes_threshold"])
        self.assertEqual(self.inference_router.reloaded_paths, [])
        kwargs = run_qc.call_args.kwargs
        self.assertFalse(kwargs["strict"])

    def test_default_local_training_launcher_writes_worker_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset_path = Path(tmp) / "job" / "dataset"
            dataset_path.mkdir(parents=True)
            worker_log = dataset_path.parent / "worker.log"

            with mock.patch.object(routes_places.subprocess, "Popen") as popen:
                result = routes_places._default_local_training_launcher(str(dataset_path), "models/yolo11_best.pt")

            self.assertTrue(result["ok"])
            self.assertTrue(worker_log.exists())
            _, kwargs = popen.call_args
            self.assertIsNotNone(kwargs["stdout"])
            self.assertIs(kwargs["stdout"], kwargs["stderr"])


if __name__ == "__main__":
    unittest.main()
