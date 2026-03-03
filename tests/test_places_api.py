"""API tests for the places MVP routes."""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from datetime import UTC, datetime

import cv2
import numpy as np

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.places import PlaceStore
from server.routes_places import router, set_dependencies, set_store
from server.schemas import GPUServerSchema


class PlacesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = PlaceStore(Path(self._tmp.name) / "places")
        set_store(self.store)

        def fake_local_launcher(dataset_path: str, base_model: str):
            job_dir = Path(dataset_path).parent
            (job_dir / "status.json").write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "started_at": datetime.now(UTC).isoformat(),
                        "finished_at": datetime.now(UTC).isoformat(),
                        "error": None,
                        "result_model_version": f"{job_dir.name}-v1",
                        "result_model_path": str(job_dir / "train" / "weights" / "best.pt"),
                    }
                ),
                encoding="utf-8",
            )
            return {"ok": True}

        set_dependencies(None, local_training_launcher=fake_local_launcher)
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()

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

        job = self.client.get(f"/api/places/jobs/{train_payload['job_id']}")
        self.assertEqual(job.status_code, 200)
        self.assertEqual(job.json()["status"], "ready")
        self.assertTrue(job.json()["dataset_path"].endswith("/dataset"))

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

    def test_activate_requires_ready_place(self) -> None:
        create = self.client.post("/api/places", json={"name": "Dryer"})
        place_id = create.json()["id"]

        activate = self.client.put("/api/places/active", json={"place_id": place_id})
        self.assertEqual(activate.status_code, 409)


if __name__ == "__main__":
    unittest.main()
