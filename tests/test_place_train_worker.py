"""Unit tests for place training worker preprocessing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from server.place_train_worker import _augment_training_set, _normalize_data_yaml


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

    def test_normalize_data_yaml_sets_dataset_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "dataset"
            dataset.mkdir(parents=True)
            (dataset / "data.yaml").write_text(
                "\n".join(
                    [
                        "path: .",
                        "train: images/train",
                        "val: images/train",
                        "test: images/train",
                        "names:",
                        "  0: place_base1",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            _normalize_data_yaml(dataset)

            payload = (dataset / "data.yaml").read_text(encoding="utf-8")
            self.assertIn(f"path: {dataset.resolve()}", payload)
            self.assertIn("train: images/train", payload)


if __name__ == "__main__":
    unittest.main()
