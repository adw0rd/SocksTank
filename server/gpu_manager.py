"""GPUServerManager for remote inference server management."""

import json
import logging
import os
import threading
import time

import httpx
import paramiko

from server.schemas import GPUServerSchema

log = logging.getLogger(__name__)

GPU_SERVERS_FILE = "gpu_servers.json"


class GPUServerManager:
    """Store, health-check, and auto-start remote GPU servers over SSH."""

    def __init__(self):
        self._servers: list[GPUServerSchema] = []
        self._lock = threading.Lock()
        self._health_thread: threading.Thread | None = None
        self._running = False
        self._inference_router = None
        self._client = httpx.Client(timeout=httpx.Timeout(connect=2.0, read=3.0, write=3.0, pool=3.0))

    @property
    def servers(self) -> list[GPUServerSchema]:
        with self._lock:
            return list(self._servers)

    def load(self):
        """Load the server list from gpu_servers.json."""
        if not os.path.exists(GPU_SERVERS_FILE):
            log.info("File %s not found; GPU server list is empty", GPU_SERVERS_FILE)
            return
        try:
            with open(GPU_SERVERS_FILE) as f:
                data = json.load(f)
            self._servers = [GPUServerSchema(**s) for s in data]
            log.info("Loaded %d GPU servers", len(self._servers))
        except Exception as e:
            log.error("Failed to load %s: %s", GPU_SERVERS_FILE, e)

    def save(self):
        """Save the server list to gpu_servers.json."""
        with self._lock:
            data = [s.model_dump(exclude_none=True) for s in self._servers]
        try:
            with open(GPU_SERVERS_FILE, "w") as f:
                json.dump(data, f, indent=2)
            log.info("Saved %d GPU servers", len(data))
        except Exception as e:
            log.error("Failed to save %s: %s", GPU_SERVERS_FILE, e)

    def add_server(
        self,
        host: str,
        port: int,
        username: str,
        auth_type: str = "key",
        password: str | None = None,
        key_path: str | None = None,
        name: str | None = None,
    ) -> GPUServerSchema:
        """Add a GPU server."""
        server = GPUServerSchema(
            name=name.strip() if name else None,
            host=host,
            port=port,
            username=username,
            auth_type=auth_type,
            password=password,
            key_path=key_path,
        )
        with self._lock:
            # Replace an existing entry for the same host
            self._servers = [s for s in self._servers if s.host != host]
            self._servers.append(server)
        self.save()
        log.info("Added GPU server: %s:%d", host, port)
        return server

    def update_server(
        self,
        current_host: str,
        *,
        host: str,
        port: int,
        username: str,
        auth_type: str = "key",
        password: str | None = None,
        key_path: str | None = None,
        name: str | None = None,
    ) -> GPUServerSchema | None:
        """Update an existing GPU server."""
        existing = self.get_server(current_host)
        if not existing:
            return None

        updated = GPUServerSchema(
            name=name.strip() if name else None,
            host=host,
            port=port,
            username=username,
            auth_type=auth_type,
            password=password,
            key_path=key_path,
            status="offline",
            gpu=None,
        )
        with self._lock:
            self._servers = [s for s in self._servers if s.host not in {current_host, host}]
            self._servers.append(updated)
        self.save()
        log.info("Updated GPU server: %s -> %s:%d", current_host, host, port)
        return updated

    def remove_server(self, host: str) -> bool:
        """Remove a GPU server."""
        with self._lock:
            before = len(self._servers)
            self._servers = [s for s in self._servers if s.host != host]
            removed = len(self._servers) < before
        if removed:
            self.save()
            log.info("Removed GPU server: %s", host)
        return removed

    def get_server(self, host: str) -> GPUServerSchema | None:
        """Find a server by host."""
        with self._lock:
            for s in self._servers:
                if s.host == host:
                    return s
        return None

    def test_connection(self, host: str) -> dict:
        """Test connectivity to a server using GET /health."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Server {host} not found"}

        url = f"http://{server.host}:{server.port}/health"
        try:
            resp = self._client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                with self._lock:
                    server.status = "online"
                    server.gpu = data.get("gpu")
                return {"ok": True, **data}
            return {"ok": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def start_remote(self, host: str) -> dict:
        """Start inference_server on a remote host over SSH."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Server {host} not found"}

        with self._lock:
            server.status = "starting"

        try:
            ssh = self._ssh_connect(server)
            # Kill the previous process if it exists
            ssh.exec_command("pkill -f 'server.inference_server' 2>/dev/null || true")
            time.sleep(0.5)

            # Start inference_server
            cmd = "cd ~/sockstank && " "nohup python3 -m server.inference_server " f"--port {server.port} " "> /tmp/inference.log 2>&1 &"
            log.info("Starting remote inference server on %s with command: %s", host, cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()

            # Wait for startup (up to 30 seconds)
            url = f"http://{server.host}:{server.port}/health"
            for _ in range(30):
                time.sleep(1)
                try:
                    resp = self._client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        with self._lock:
                            server.status = "online"
                            server.gpu = data.get("gpu")
                        ssh.close()
                        log.info("Inference server started on %s:%d", host, server.port)
                        return {"ok": True, **data}
                except Exception:
                    continue

            with self._lock:
                server.status = "offline"
            try:
                _stdin, log_stdout, _stderr = ssh.exec_command("tail -n 20 /tmp/inference.log 2>/dev/null || true")
                startup_log = log_stdout.read().decode().strip()
            except Exception:
                startup_log = ""
            finally:
                ssh.close()

            hint = "Use python3 on the remote host; many Linux systems do not provide a 'python' binary."
            if startup_log:
                log.warning("Remote inference server on %s failed to start. Last log lines: %s", host, startup_log)
                return {"ok": False, "error": f"Startup timed out (30 seconds). {hint} Last log: {startup_log}"}
            log.warning("Remote inference server on %s failed to start. %s", host, hint)
            return {"ok": False, "error": f"Startup timed out (30 seconds). {hint}"}

        except Exception as e:
            with self._lock:
                server.status = "offline"
            log.error("SSH start failed on %s: %s", host, e)
            return {"ok": False, "error": str(e)}

    def stop_remote(self, host: str) -> dict:
        """Stop inference_server on a remote host."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Server {host} not found"}

        try:
            ssh = self._ssh_connect(server)
            ssh.exec_command("pkill -f 'server.inference_server' 2>/dev/null || true")
            ssh.close()
            with self._lock:
                server.status = "offline"
            log.info("Inference server stopped on %s", host)
            return {"ok": True}
        except Exception as e:
            log.error("SSH stop failed on %s: %s", host, e)
            return {"ok": False, "error": str(e)}

    def _ssh_connect(self, server: GPUServerSchema) -> paramiko.SSHClient:
        """Create an SSH connection."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs = {"hostname": server.host, "username": server.username}
        if server.auth_type == "password" and server.password:
            kwargs["password"] = server.password
        elif server.key_path:
            kwargs["key_filename"] = os.path.expanduser(server.key_path)
        # Otherwise use the default SSH key (~/.ssh/id_rsa)

        ssh.connect(**kwargs)
        return ssh

    def start_health_loop(self, inference_router):
        """Start the background health-check loop."""
        self._inference_router = inference_router
        self._running = True
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()
        log.info("Health check loop started")

    def stop(self):
        """Stop the background health-check loop."""
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=3)
        self._client.close()
        log.info("GPUServerManager stopped")

    def _health_loop(self):
        """Background thread that checks /health on active servers every 5 seconds."""
        while self._running:
            try:
                self._check_servers()
            except Exception as e:
                log.error("Health loop failed: %s", e)
            time.sleep(5)

    def _check_servers(self):
        """Refresh server statuses and update the InferenceRouter."""
        active_url = None
        for server in self.servers:
            if server.status in ("online", "starting"):
                url = f"http://{server.host}:{server.port}/health"
                try:
                    resp = self._client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        with self._lock:
                            server.status = "online"
                            server.gpu = data.get("gpu")
                        if active_url is None:
                            active_url = f"http://{server.host}:{server.port}"
                    else:
                        with self._lock:
                            server.status = "offline"
                except Exception:
                    with self._lock:
                        server.status = "offline"

        # Update the InferenceRouter
        if self._inference_router:
            self._inference_router.set_remote_url(active_url)
