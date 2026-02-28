"""Unit tests for CameraManager behavior."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

import numpy as np

from server.camera import CameraManager


class CameraManagerInferenceTests(unittest.TestCase):
    def test_skips_inference_for_mock_camera(self) -> None:
        camera = Mock()
        camera.is_mock = True
        inference = Mock()
        manager = CameraManager(camera, inference)

        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        detections = manager._run_yolo(frame)

        self.assertEqual(detections, [])
        inference.infer.assert_not_called()

    def test_runs_inference_for_real_camera(self) -> None:
        camera = Mock()
        camera.is_mock = False
        inference = Mock()
        inference.infer.return_value = [{"class": "sock", "confidence": 0.9, "bbox": [1, 1, 5, 5]}]
        manager = CameraManager(camera, inference)

        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        detections = manager._run_yolo(frame)

        self.assertEqual(detections, inference.infer.return_value)
        inference.infer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
