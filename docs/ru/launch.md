# Запуск проекта

Как собрать фронтенд, запустить бэкенд и развернуть SocksTank на роботе.

## Разработка на macOS / Linux

### 1. Установка зависимостей

```bash
cd ~/work/SocksTank

# Python (через uv)
uv venv && uv pip install -e .

# Или через pip
pip install typer ultralytics opencv-python-headless numpy \
  fastapi uvicorn pydantic-settings websockets httpx paramiko pyyaml
```

### 2. Сборка фронтенда

```bash
cd frontend
npm install        # один раз
npm run build      # собрать в frontend/dist/
```

### 3. Запуск (mock-режим)

```bash
./main.py serve --mock
```

Открыть: **http://localhost:8080**

Флаг `--mock` заменяет GPIO, камеру и сенсоры на заглушки — можно разрабатывать без RPi.

### Режим разработки с hot-reload

Для работы над фронтендом — два терминала:

```bash
# Терминал 1: бэкенд
./main.py serve --mock

# Терминал 2: Vite dev server (hot-reload)
cd frontend && npm run dev
```

Фронтенд: **http://localhost:5173** (с hot-reload, проксирует API на порт 8080).

## Деплой на Raspberry Pi

### 1. Копирование проекта

```bash
rsync -avz --exclude .venv --exclude frontend/node_modules --exclude __pycache__ --exclude .git \
  ~/work/SocksTank/ rpi5:~/sockstank/
```

### 2. Установка зависимостей на RPi

```bash
ssh rpi5
sudo pip install fastapi uvicorn pydantic-settings websockets typer httpx paramiko --break-system-packages
```

`picamera2` уже предустановлен в Raspberry Pi OS.

### 3. Запуск на RPi

```bash
cd ~/sockstank

# Простой запуск
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5

# С NcnnNativeDetector (12.8–16.0 FPS на RPi 5)
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 --ncnn-cpp --ncnn-threads 4

# В фоне (рекомендуется)
sudo -E nohup python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 > /tmp/sockstank.log 2>&1 &
```

Открыть: **http://rpi5:8080**

Логи: `tail -f /tmp/sockstank.log`

`sudo -E` — `sudo` для доступа к камере и GPIO, `-E` наследует PYTHONPATH.

## Параметры `main.py serve`

| Параметр | По умолчанию | Описание |
|---|---|---|
| `--model` | `models/yolo11_best.pt` | Путь к модели (.pt, .onnx, ncnn директория) |
| `--conf` | `0.5` | Порог уверенности (0.0–1.0) |
| `--host` | `0.0.0.0` | Адрес привязки |
| `--port` | `8080` | HTTP/WebSocket порт |
| `--mock` | `false` | Mock-режим (без GPIO/камеры) |
| `--ncnn-cpp` | `false` | NcnnNativeDetector (pip ncnn + OMP workaround) |
| `--ncnn-threads` | `2` | Количество OMP потоков для ncnn (1–4) |
| `--freenove-path` | `~/Freenove_.../Code/Server` | Путь к модулям Freenove |

Все параметры можно задать через переменные окружения с префиксом `SOCKSTANK_`:

```bash
SOCKSTANK_MODEL_PATH="models/yolo11_best_ncnn_model" SOCKSTANK_MOCK=true python main.py serve
```

## Обновление фронтенда на RPi

После изменений в `frontend/`:

```bash
# На dev-машине
cd frontend && npm run build

# Скопировать на RPi
rsync -avz frontend/dist/ rpi5:~/sockstank/frontend/dist/
```

Перезапустить serve на RPi.

## GPU-инференс (удалённый)

Подробнее: [inference.md — Удалённый инференс](inference.md#удалённый-инференс-gpu-сервер)

```bash
# На GPU-сервере (blackops)
python -m server.inference_server --model models/yolo11_best.pt --port 8090
```

В веб-панели: **Inference → + Add GPU Server** → ввести хост, порт, SSH-ключ → **Save**.

---

[Вернуться к README](README.md)
