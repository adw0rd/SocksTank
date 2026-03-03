"""Unit tests for place training worker preprocessing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from server.place_train_worker import _augment_training_set


class PlaceTrainWorkerTests(unittest.TestCase):
    def test_augment_training_set_creates_augmented_images_and_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "dataset"
            images_dir = dataset / "images" / "train"
            labels_dir = dataset / "labels" / "train"
            images_dir.mkdir(parents=True)
            labels_dir.mkdir(parents=True)

            image = np.zeros((40, 60, 3), dtype=np.uint8)
            ok, encoded = cv2.imencode(".jpg", image)
            self.assertTrue(ok)
            (images_dir / "sample.jpg").write_bytes(encoded.tobytes())
            (labels_dir / "sample.txt").write_text("0 0.250000 0.500000 0.300000 0.400000\n", encoding="utf-8")

            _augment_training_set(dataset)

            self.assertTrue((images_dir / "sample_bright.jpg").exists())
            self.assertTrue((images_dir / "sample_dark.jpg").exists())
            self.assertTrue((images_dir / "sample_flip.jpg").exists())
            self.assertTrue((labels_dir / "sample_bright.txt").exists())
            self.assertTrue((labels_dir / "sample_dark.txt").exists())
            self.assertTrue((labels_dir / "sample_flip.txt").exists())
            self.assertEqual(
                (labels_dir / "sample_flip.txt").read_text(encoding="utf-8").strip(),
                "0 0.750000 0.500000 0.300000 0.400000",
            )


if __name__ == "__main__":
    unittest.main()
