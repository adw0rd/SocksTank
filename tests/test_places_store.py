"""Unit tests for place storage behavior."""

from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from server.places import PlaceStore
from server.schemas import PlaceAnnotationUpsertRequest, PlaceImageUploadItem


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

        job = self.store.train_place(place.id, "models/yolo11_best.pt")
        self.assertEqual(job.status.value, "ready")
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
            self.store.train_place(place.id, "models/yolo11_best.pt")


if __name__ == "__main__":
    unittest.main()
