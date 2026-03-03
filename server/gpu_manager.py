"""GPUServerManager for remote inference server management."""

import json
import logging
import os
import posixpath
import shlex
import stat
from pathlib import Path
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

    def stage_place_training_dataset(self, host: str, dataset_path: str | Path, job_id: str) -> dict:
        """Upload a prepared dataset bundle to a remote GPU host."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Server {host} not found"}

        local_dataset = Path(dataset_path)
        if not local_dataset.exists():
            return {"ok": False, "error": f"Dataset path does not exist: {local_dataset}"}

        remote_root = self._expand_remote_path(server, f"~/sockstank/user_data/place_jobs/{job_id}")
        remote_dataset = posixpath.join(remote_root, "dataset")
        try:
            ssh = self._ssh_connect(server)
            ssh.exec_command(f"mkdir -p {shlex.quote(remote_root)}")
            ssh.exec_command(f"rm -rf {shlex.quote(remote_dataset)}")
            ssh.exec_command(f"mkdir -p {shlex.quote(remote_dataset)}")

            sftp = ssh.open_sftp()
            self._sftp_upload_dir(sftp, local_dataset, remote_dataset)
            sftp.close()
            ssh.close()
            log.info("Staged place dataset on %s:%s", host, remote_dataset)
            return {"ok": True, "remote_dataset_path": remote_dataset}
        except Exception as e:
            log.error("Failed to stage place dataset on %s: %s", host, e)
            return {"ok": False, "error": str(e)}

    def start_place_training(self, host: str, job_id: str, remote_dataset_path: str, base_model: str) -> dict:
        """Start a background place-training worker on a remote host."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Server {host} not found"}

        remote_job_dir = posixpath.dirname(remote_dataset_path)
        cmd = (
            "cd ~/sockstank && "
            f"nohup python3 -m server.place_train_worker "
            f"--dataset {shlex.quote(remote_dataset_path)} "
            f"--job-dir {shlex.quote(remote_job_dir)} "
            f"--base-model {shlex.quote(base_model)} "
            "--device 0 "
            f"> {shlex.quote(posixpath.join(remote_job_dir, 'worker.log'))} 2>&1 &"
        )
        try:
            ssh = self._ssh_connect(server)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
            ssh.close()
            log.info("Started remote place training on %s for job %s", host, job_id)
            return {"ok": True}
        except Exception as e:
            log.error("Failed to start remote place training on %s: %s", host, e)
            return {"ok": False, "error": str(e)}

    def read_place_training_status(self, host: str, job_id: str) -> dict:
        """Read a remote place-training status.json if it exists."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Server {host} not found"}

        remote_status = self._expand_remote_path(server, f"~/sockstank/user_data/place_jobs/{job_id}/status.json")
        try:
            ssh = self._ssh_connect(server)
            _, stdout, _ = ssh.exec_command(f"cat {shlex.quote(remote_status)} 2>/dev/null || true")
            raw = stdout.read().decode().strip()
            ssh.close()
            if not raw:
                return {"ok": False, "error": "Status file not found"}
            return {"ok": True, "status": json.loads(raw)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def fetch_place_training_artifacts(
        self,
        host: str,
        *,
        remote_model_path: str | None,
        remote_ncnn_path: str | None,
        local_job_dir: str | Path,
    ) -> dict:
        """Download trained artifacts from a remote GPU host into a local job directory."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Server {host} not found"}

        local_root = Path(local_job_dir) / "artifacts"
        local_root.mkdir(parents=True, exist_ok=True)

        try:
            ssh = self._ssh_connect(server)
            sftp = ssh.open_sftp()
            local_model_path = None
            local_ncnn_path = None
            if remote_model_path:
                model_name = Path(remote_model_path).name
                local_model_path = local_root / model_name
                sftp.get(self._expand_remote_path(server, remote_model_path), str(local_model_path))
            if remote_ncnn_path:
                ncnn_name = Path(remote_ncnn_path).name
                local_ncnn_path = local_root / ncnn_name
                self._sftp_download_dir(sftp, self._expand_remote_path(server, remote_ncnn_path), local_ncnn_path)
            sftp.close()
            ssh.close()
            return {
                "ok": True,
                "result_model_path": str(local_model_path) if local_model_path else None,
                "result_ncnn_path": str(local_ncnn_path) if local_ncnn_path else None,
            }
        except Exception as e:
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

    def _sftp_upload_dir(self, sftp: paramiko.SFTPClient, local_dir: Path, remote_dir: str) -> None:
        """Recursively upload a local directory to a remote SFTP path."""
        self._sftp_mkdirs(sftp, remote_dir)
        for entry in local_dir.iterdir():
            remote_path = posixpath.join(remote_dir, entry.name)
            if entry.is_dir():
                self._sftp_upload_dir(sftp, entry, remote_path)
            else:
                sftp.put(str(entry), remote_path)

    def _sftp_mkdirs(self, sftp: paramiko.SFTPClient, remote_dir: str) -> None:
        """Recursively create a remote directory tree if it does not exist."""
        parts = [part for part in remote_dir.split("/") if part and part != "."]
        current = "/" if remote_dir.startswith("/") else ""
        for part in parts:
            current = posixpath.join(current, part) if current else part
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)

    def _sftp_download_dir(self, sftp: paramiko.SFTPClient, remote_dir: str, local_dir: Path) -> None:
        """Recursively download a remote directory tree."""
        local_dir.mkdir(parents=True, exist_ok=True)
        for entry in sftp.listdir_attr(remote_dir):
            remote_path = posixpath.join(remote_dir, entry.filename)
            local_path = local_dir / entry.filename
            if stat.S_ISDIR(entry.st_mode):
                self._sftp_download_dir(sftp, remote_path, local_path)
            else:
                sftp.get(remote_path, str(local_path))

    def _expand_remote_path(self, server: GPUServerSchema, remote_path: str) -> str:
        """Expand ~/ paths for the current remote user."""
        if remote_path.startswith("~/"):
            return remote_path.replace("~", f"/home/{server.username}", 1)
        return remote_path

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
