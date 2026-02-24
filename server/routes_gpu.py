"""REST API для управления инференсом и GPU-серверами."""

import logging
import threading

from fastapi import APIRouter

from server.config import settings
from server.schemas import GPUServerCreate, InferenceModeUpdate

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["gpu"])

_inference_router = None
_gpu_manager = None


def set_dependencies(inference_router, gpu_manager):
    """Установить зависимости (вызывается из app.py)."""
    global _inference_router, _gpu_manager
    _inference_router = inference_router
    _gpu_manager = gpu_manager


@router.get("/inference")
async def get_inference_status():
    """Статус инференса."""
    return {
        "mode": _inference_router.mode if _inference_router else settings.inference_mode,
        "active_backend": _inference_router.active_backend if _inference_router else "local",
        "inference_ms": _inference_router.inference_ms if _inference_router else 0,
        "error": _inference_router.error if _inference_router else None,
    }


@router.put("/inference/mode")
async def update_inference_mode(body: InferenceModeUpdate):
    """Обновить режим инференса."""
    if body.mode not in ("auto", "local", "remote"):
        return {"error": f"Invalid mode: {body.mode}"}
    if _inference_router:
        _inference_router.mode = body.mode
    return {"mode": body.mode}


@router.get("/gpu/servers")
async def list_gpu_servers():
    """Список GPU-серверов."""
    if not _gpu_manager:
        return {"servers": []}
    servers = _gpu_manager.servers
    return {"servers": [s.model_dump(exclude_none=True) for s in servers]}


@router.post("/gpu/servers")
async def add_gpu_server(body: GPUServerCreate):
    """Добавить GPU-сервер."""
    if not _gpu_manager:
        return {"error": "GPU manager не инициализирован"}
    server = _gpu_manager.add_server(
        host=body.host,
        port=body.port,
        username=body.username,
        auth_type=body.auth_type,
        password=body.password,
        key_path=body.key_path,
    )
    return server.model_dump(exclude_none=True)


@router.delete("/gpu/servers/{host}")
async def remove_gpu_server(host: str):
    """Удалить GPU-сервер."""
    if not _gpu_manager:
        return {"error": "GPU manager не инициализирован"}
    removed = _gpu_manager.remove_server(host)
    return {"ok": removed}


@router.post("/gpu/servers/{host}/test")
async def test_gpu_server(host: str):
    """Проверить подключение к GPU-серверу."""
    if not _gpu_manager:
        return {"error": "GPU manager не инициализирован"}
    return _gpu_manager.test_connection(host)


@router.post("/gpu/servers/{host}/start")
async def start_gpu_server(host: str):
    """Запустить inference-сервер на GPU (в фоне)."""
    if not _gpu_manager:
        return {"error": "GPU manager не инициализирован"}

    def _do_start():
        _gpu_manager.start_remote(host)

    thread = threading.Thread(target=_do_start, daemon=True)
    thread.start()
    return {"ok": True, "message": f"Запуск inference-сервера на {host}..."}


@router.post("/gpu/servers/{host}/stop")
async def stop_gpu_server(host: str):
    """Остановить inference-сервер на GPU."""
    if not _gpu_manager:
        return {"error": "GPU manager не инициализирован"}
    return _gpu_manager.stop_remote(host)
