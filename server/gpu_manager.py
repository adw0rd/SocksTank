"""GPUServerManager — управление GPU-серверами для удалённого инференса."""

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
    """Хранение, health check, SSH auto-start GPU-серверов."""

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
        """Загрузить список серверов из gpu_servers.json."""
        if not os.path.exists(GPU_SERVERS_FILE):
            log.info("Файл %s не найден, список серверов пуст", GPU_SERVERS_FILE)
            return
        try:
            with open(GPU_SERVERS_FILE) as f:
                data = json.load(f)
            self._servers = [GPUServerSchema(**s) for s in data]
            log.info("Загружено %d GPU-серверов", len(self._servers))
        except Exception as e:
            log.error("Ошибка загрузки %s: %s", GPU_SERVERS_FILE, e)

    def save(self):
        """Сохранить список серверов в gpu_servers.json."""
        with self._lock:
            data = [s.model_dump(exclude_none=True) for s in self._servers]
        try:
            with open(GPU_SERVERS_FILE, "w") as f:
                json.dump(data, f, indent=2)
            log.info("Сохранено %d GPU-серверов", len(data))
        except Exception as e:
            log.error("Ошибка сохранения %s: %s", GPU_SERVERS_FILE, e)

    def add_server(
        self, host: str, port: int, username: str, auth_type: str = "key", password: str | None = None, key_path: str | None = None
    ) -> GPUServerSchema:
        """Добавить GPU-сервер."""
        server = GPUServerSchema(
            host=host,
            port=port,
            username=username,
            auth_type=auth_type,
            password=password,
            key_path=key_path,
        )
        with self._lock:
            # Удалить существующий с тем же host
            self._servers = [s for s in self._servers if s.host != host]
            self._servers.append(server)
        self.save()
        log.info("Добавлен GPU-сервер: %s:%d", host, port)
        return server

    def remove_server(self, host: str) -> bool:
        """Удалить GPU-сервер."""
        with self._lock:
            before = len(self._servers)
            self._servers = [s for s in self._servers if s.host != host]
            removed = len(self._servers) < before
        if removed:
            self.save()
            log.info("Удалён GPU-сервер: %s", host)
        return removed

    def get_server(self, host: str) -> GPUServerSchema | None:
        """Найти сервер по хосту."""
        with self._lock:
            for s in self._servers:
                if s.host == host:
                    return s
        return None

    def test_connection(self, host: str) -> dict:
        """Проверить подключение к серверу (GET /health)."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Сервер {host} не найден"}

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
        """Запустить inference_server на удалённом сервере через SSH."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Сервер {host} не найден"}

        with self._lock:
            server.status = "starting"

        try:
            ssh = self._ssh_connect(server)
            # Убить старый процесс, если есть
            ssh.exec_command("pkill -f 'server.inference_server' 2>/dev/null || true")
            time.sleep(0.5)

            # Запустить inference_server
            cmd = (
                f"cd ~/sockstank && "
                f"nohup python -m server.inference_server "
                f"--model models/yolo11_best.pt --port {server.port} "
                f"> /tmp/inference.log 2>&1 &"
            )
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
            ssh.close()

            # Ожидание запуска (до 30 сек)
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
                        log.info("Inference-сервер запущен на %s:%d", host, server.port)
                        return {"ok": True, **data}
                except Exception:
                    continue

            with self._lock:
                server.status = "offline"
            return {"ok": False, "error": "Таймаут запуска (30 сек)"}

        except Exception as e:
            with self._lock:
                server.status = "offline"
            log.error("Ошибка SSH-запуска на %s: %s", host, e)
            return {"ok": False, "error": str(e)}

    def stop_remote(self, host: str) -> dict:
        """Остановить inference_server на удалённом сервере."""
        server = self.get_server(host)
        if not server:
            return {"ok": False, "error": f"Сервер {host} не найден"}

        try:
            ssh = self._ssh_connect(server)
            ssh.exec_command("pkill -f 'server.inference_server' 2>/dev/null || true")
            ssh.close()
            with self._lock:
                server.status = "offline"
            log.info("Inference-сервер остановлен на %s", host)
            return {"ok": True}
        except Exception as e:
            log.error("Ошибка SSH-остановки на %s: %s", host, e)
            return {"ok": False, "error": str(e)}

    def _ssh_connect(self, server: GPUServerSchema) -> paramiko.SSHClient:
        """Создать SSH-подключение."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs = {"hostname": server.host, "username": server.username}
        if server.auth_type == "password" and server.password:
            kwargs["password"] = server.password
        elif server.key_path:
            kwargs["key_filename"] = os.path.expanduser(server.key_path)
        # Иначе — дефолтный SSH-ключ (~/.ssh/id_rsa)

        ssh.connect(**kwargs)
        return ssh

    def start_health_loop(self, inference_router):
        """Запустить фоновый health check loop."""
        self._inference_router = inference_router
        self._running = True
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()
        log.info("Health check loop запущен")

    def stop(self):
        """Остановить health check loop."""
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=3)
        self._client.close()
        log.info("GPUServerManager остановлен")

    def _health_loop(self):
        """Фоновый поток: каждые 5 сек проверяет /health активного сервера."""
        while self._running:
            try:
                self._check_servers()
            except Exception as e:
                log.error("Ошибка в health loop: %s", e)
            time.sleep(5)

    def _check_servers(self):
        """Проверить статус всех серверов и обновить InferenceRouter."""
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

        # Обновить InferenceRouter
        if self._inference_router:
            self._inference_router.set_remote_url(active_url)
