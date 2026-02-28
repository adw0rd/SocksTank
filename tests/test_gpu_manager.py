"""Unit tests for GPU server health loop behavior."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

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


if __name__ == "__main__":
    unittest.main()
