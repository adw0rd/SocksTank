# Remote Inference — дизайн

Переключаемый инференс: локальный (RPi CPU) или удалённый (GPU-сервер по HTTP).

## Архитектура

```
┌─────────────────────────────────────────────────┐
│                  RPi 5 (робот)                  │
│                                                 │
│  Camera → CameraManager → InferenceRouter       │
│                              ├─ LocalInference   │
│                              └─ RemoteInference  │
│                                                 │
│  GPUServerManager ← gpu_servers.json            │
│    ├─ health check (GET /health каждые 5с)      │
│    ├─ auto-failover → local при недоступности   │
│    └─ SSH auto-start inference server           │
│                                                 │
│  Web UI: переключатель local/remote + список    │
│          GPU серверов с кнопкой "добавить"       │
└────────────────────┬────────────────────────────┘
                     │ HTTP POST /infer (JPEG → JSON)
                     ▼
┌─────────────────────────────────────────────────┐
│            GPU Machine (blackops и др.)          │
│                                                 │
│  inference_server.py (FastAPI, порт 8090)       │
│    POST /infer  ← JPEG body → JSON detections   │
│    GET  /health ← → {"status":"ok","gpu":"..."}  │
│    GET  /models ← → список доступных моделей     │
└─────────────────────────────────────────────────┘
```

## Inference Server (GPU)

Новый файл `inference_server.py` в корне проекта. FastAPI-сервер:

- `POST /infer` — принимает JPEG bytes в body, `X-Confidence` в заголовке. Возвращает `{"detections": [...], "inference_ms": 2.3}`
- `GET /health` — `{"status": "ok", "gpu": "NVIDIA RTX 4070 SUPER", "model": "yolo11_best.pt"}`
- `GET /models` — `{"models": ["yolo11_best.pt", "yolo8_best.pt"]}`

YOLO модель грузится один раз при старте. JPEG декодируется через `cv2.imdecode`.

Запуск: `python inference_server.py --model models/yolo11_best.pt --port 8090`

## InferenceRouter (RPi)

Новый файл `server/inference.py`. Заменяет прямой вызов `self._model()` в `CameraManager._run_yolo`.

```
InferenceRouter
├── mode: "auto" | "local" | "remote"
├── infer(frame, confidence) → list[dict]
│     remote: cv2.imencode → POST /infer → JSON
│     local:  self._model(frame, conf=...)
└── active_backend: str → "local" | "remote:192.168.0.188"
```

## GPUServerManager (RPi)

Новый файл `server/gpu_manager.py`.

```
GPUServerManager
├── servers: list[GPUServer]     ← из gpu_servers.json
│     GPUServer: host, port, username, auth_type, password/key_path, status
├── add_server / remove_server
├── test_connection(host) → bool
├── start_remote(server) → bool  ← SSH → запуск inference_server
├── health_loop()                ← фоновый поток, каждые 5 сек
└── save() / load()              ← gpu_servers.json
```

`gpu_servers.json`:
```json
[
  {
    "host": "192.168.0.188",
    "port": 8090,
    "username": "zeus",
    "auth_type": "key",
    "key_path": "~/.ssh/id_rsa"
  }
]
```

## REST API (RPi, новые эндпоинты)

Новый роутер `server/routes_gpu.py`:

| Метод | Путь | Описание |
|---|---|---|
| GET | /api/inference | Текущий режим, активный backend, inference_ms |
| PUT | /api/inference/mode | Переключить режим (auto/local/remote) |
| GET | /api/gpu/servers | Список GPU серверов |
| POST | /api/gpu/servers | Добавить GPU сервер |
| DELETE | /api/gpu/servers/{host} | Удалить GPU сервер |
| POST | /api/gpu/servers/{host}/test | Проверить подключение |
| POST | /api/gpu/servers/{host}/start | Запустить inference_server по SSH |
| POST | /api/gpu/servers/{host}/stop | Остановить inference_server по SSH |

## Телеметрия (изменения)

Новые поля в `TelemetryMessage`:

```python
inference_mode: str          # "auto" | "local" | "remote"
inference_backend: str       # "local" | "remote:192.168.0.188"
inference_ms: float          # время последнего инференса
inference_error: str | None  # "GPU unavailable" и т.п.
```

## Failover

### mode = "auto"
- Старт: попробовать первый GPU → SSH запуск → ждать /health до 30 сек → если нет, fallback на local
- GPU пропал → local, GPU вернулся → remote

### mode = "local"
- Health check работает, но не переключает. Только обновляет статус в UI.

### mode = "remote"
- GPU пропал → НЕ переключать. Пустые детекции + ошибка в телеметрии.

### Таймауты HTTP POST /infer
- connect: 2 сек, read: 5 сек. Таймаут = GPU offline.

## Фронтенд

### InferencePanel
Новый компонент в правой панели:
- 3 кнопки режима: Auto / Local / Remote
- Статус: бэкенд, latency, FPS
- Список GPU серверов со статусами
- Кнопка "Добавить GPU сервер" → модалка

### AddGpuServerModal
Модалка: хост, порт, пользователь, авторизация (SSH-ключ/пароль), кнопки "Проверить" и "Сохранить".

### Новые файлы
- `frontend/src/components/InferencePanel.tsx`
- `frontend/src/components/AddGpuServerModal.tsx`

### Изменения
- `types.ts` — новые поля в Telemetry
- `App.tsx` — добавить InferencePanel

## Изменения в существующих файлах

| Файл | Изменение |
|---|---|
| `server/camera.py` | `_run_yolo` вызывает `InferenceRouter.infer()` вместо `self._model()` |
| `server/config.py` | Новое поле `inference_mode: str = "auto"` |
| `server/app.py` | Lifespan: создать GPUServerManager → InferenceRouter → передать в CameraManager |
| `server/schemas.py` | Новые поля в TelemetryMessage |
| `server/routes_ws.py` | Передавать inference-поля в телеметрию |
