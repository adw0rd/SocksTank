"""Unit tests for GPU server health loop behavior."""

from __future__ import annotations

import unittest
from unittest.mock import Mock
from pathlib import Path
import tempfile

from server.gpu_manager import GPUServerManager
from server.schemas import GPUServerSchema


class GPUServerManagerHealthTests(unittest.TestCase):
    def test_check_servers_reactivates_offline_server(self) -> None:
        manager = GPUServerManager()
        router = Mock()
        manager._inference_router = router
        server = GPUServerSchema(name="GPU Box", host="gpu-box", port=8090, username="user", status="offline")
        manager._servers = [server]

        response = Mock()
        response.status_code = 200
        response.json.return_value = {"gpu": "RTX Test"}
        manager._client = Mock()
        manager._client.get.return_value = response

        manager._check_servers()

        self.assertEqual(server.status, "online")
        self.assertEqual(server.gpu, "RTX Test")
        router.set_remote_url.assert_called_once_with("http://gpu-box:8090")

    def test_stage_place_training_dataset_expands_remote_home_for_sftp(self) -> None:
        manager = GPUServerManager()
        server = GPUServerSchema(name="GPU Box", host="gpu-box", username="user", status="online")
        manager._servers = [server]

        with tempfile.TemporaryDirectory() as tmp:
            dataset_root = Path(tmp) / "dataset"
            (dataset_root / "images" / "train").mkdir(parents=True)
            sample = dataset_root / "images" / "train" / "sample.jpg"
            sample.write_bytes(b"jpg")

            ssh = Mock()
            sftp = Mock()
            ssh.open_sftp.return_value = sftp
            manager._ssh_connect = Mock(return_value=ssh)
            manager._sftp_upload_dir = Mock()

            result = manager.stage_place_training_dataset("gpu-box", dataset_root, "job_123")

        self.assertTrue(result["ok"])
        self.assertEqual(result["remote_dataset_path"], "/home/user/sockstank/user_data/place_jobs/job_123/dataset")
        manager._sftp_upload_dir.assert_called_once_with(
            sftp,
            dataset_root,
            "/home/user/sockstank/user_data/place_jobs/job_123/dataset",
        )

    def test_read_place_training_status_expands_remote_home(self) -> None:
        manager = GPUServerManager()
        server = GPUServerSchema(name="GPU Box", host="gpu-box", username="user", status="online")
        manager._servers = [server]

        stdout = Mock()
        stdout.read.return_value = b'{"status":"ready"}'
        ssh = Mock()
        ssh.exec_command.return_value = (None, stdout, None)
        manager._ssh_connect = Mock(return_value=ssh)

        result = manager.read_place_training_status("gpu-box", "job_123")

        self.assertTrue(result["ok"])
        ssh.exec_command.assert_called_once_with("cat /home/user/sockstank/user_data/place_jobs/job_123/status.json 2>/dev/null || true")


if __name__ == "__main__":
    unittest.main()
