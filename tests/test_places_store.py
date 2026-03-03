"""Unit tests for place storage behavior."""

from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from server.places import PlaceStore
from server.schemas import PlaceAnnotationUpsertRequest, PlaceImageUploadItem, PlaceJobStatus


class PlaceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = PlaceStore(Path(self._tmp.name) / "places")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_create_upload_annotate_and_activate_flow(self) -> None:
        place = self.store.create_place("Washing Machine")
        images = self.store.add_images(
            place.id,
            [
                PlaceImageUploadItem(
                    filename="washer.jpg",
                    content_base64=base64.b64encode(b"fake-image-bytes").decode("ascii"),
                )
            ],
        )
        self.assertEqual(len(images), 1)
        self.assertEqual(self.store.get_place(place.id).image_count, 1)

        record = self.store.upsert_annotation(
            place.id,
            images[0].id,
            PlaceAnnotationUpsertRequest(x_center=0.5, y_center=0.5, width=0.4, height=0.4),
        )
        self.assertEqual(record.place_image_id, images[0].id)

        job = self.store.train_place(place.id, "models/yolo11_best.pt", "local:rpi5")
        self.assertEqual(job.status.value, "queued")
        self.assertEqual(job.executor, "local:rpi5")
        self.assertIsNotNone(job.dataset_path)
        dataset_path = Path(job.dataset_path)
        self.assertTrue((dataset_path / "data.yaml").exists())
        self.assertTrue((dataset_path / "images" / "train" / images[0].filename).exists())
        self.assertTrue((dataset_path / "labels" / "train" / f"{Path(images[0].filename).stem}.txt").exists())
        self.assertEqual(self.store.get_place(place.id).status.value, "queued")

        updated = self.store.update_job(
            job.id,
            status=PlaceJobStatus.READY,
            result_model_version=f"{job.id}-v1",
            result_model_path=f"models/{job.id}.pt",
        )
        self.assertIsNotNone(updated)
        self.assertEqual(self.store.get_place(place.id).status.value, "ready")

        active = self.store.set_active_target(place.id)
        self.assertEqual(active, place.id)

    def test_train_requires_all_images_annotated(self) -> None:
        place = self.store.create_place("Laundry Basket")
        self.store.add_images(
            place.id,
            [
                PlaceImageUploadItem(
                    filename="basket.jpg",
                    content_base64=base64.b64encode(b"fake-image-bytes").decode("ascii"),
                )
            ],
        )

        with self.assertRaisesRegex(ValueError, "annotated"):
            self.store.train_place(place.id, "models/yolo11_best.pt", "local:rpi5")

    def test_delete_image_removes_annotation_and_updates_count(self) -> None:
        place = self.store.create_place("Dryer")
        images = self.store.add_images(
            place.id,
            [
                PlaceImageUploadItem(
                    filename="dryer.jpg",
                    content_base64=base64.b64encode(b"fake-image-bytes").decode("ascii"),
                )
            ],
        )
        self.store.upsert_annotation(
            place.id,
            images[0].id,
            PlaceAnnotationUpsertRequest(x_center=0.5, y_center=0.5, width=0.4, height=0.4),
        )

        deleted = self.store.delete_image(place.id, images[0].id)

        self.assertTrue(deleted)
        self.assertEqual(self.store.get_place(place.id).image_count, 0)
        self.assertEqual(self.store.list_images(place.id), [])
        self.assertEqual(self.store.list_annotations(place.id), [])

    def test_thumbnail_generation_creates_cached_file(self) -> None:
        image = np.zeros((60, 120, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)

        place = self.store.create_place("Cabinet")
        images = self.store.add_images(
            place.id,
            [
                PlaceImageUploadItem(
                    filename="cabinet.jpg",
                    content_base64=base64.b64encode(encoded.tobytes()).decode("ascii"),
                )
            ],
        )

        thumb_path = self.store.get_thumbnail_path(place.id, images[0].id, max_side=64)

        self.assertIsNotNone(thumb_path)
        self.assertTrue(thumb_path.exists())


if __name__ == "__main__":
    unittest.main()
