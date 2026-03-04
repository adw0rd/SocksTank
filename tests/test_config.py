"""Unit tests for configuration persistence helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import server.config as config


class ConfigPersistenceTests(unittest.TestCase):
    def test_persist_and_reload_model_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "inference_state.json"
            model_dir = Path(tmp) / "best_ncnn_model"
            model_dir.mkdir()

            with mock.patch.object(config, "INFERENCE_STATE_PATH", state_path):
                config.persist_model_path(str(model_dir))
                self.assertEqual(config.load_persisted_model_path(), str(model_dir))

    def test_ignores_missing_persisted_model_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "inference_state.json"
            missing_model = Path(tmp) / "missing_model"

            with mock.patch.object(config, "INFERENCE_STATE_PATH", state_path):
                config.persist_model_path(str(missing_model))
                self.assertIsNone(config.load_persisted_model_path())


if __name__ == "__main__":
    unittest.main()
