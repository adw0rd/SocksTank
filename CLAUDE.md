# CLAUDE.md

## Project Overview

SocksTank — робот-танк на базе Raspberry Pi 4B, который ищет носки по квартире с помощью компьютерного зрения (YOLO) и собирает их клешнёй. Построен поверх [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi).

## Project Structure

```
main.py            # CLI точка входа (typer): train, bench, detect, shot, serve
server/            # FastAPI backend (веб-панель управления)
├── app.py         # FastAPI app factory, lifespan, mount static
├── config.py      # Pydantic Settings
├── camera.py      # CameraManager: picamera2 + YOLO → MJPEG
├── hardware.py    # HardwareController: Motor/Servo/Led/Ultrasonic/Infrared
├── freenove_bridge.py  # Импорт Freenove модулей + mock fallback
├── mock.py        # Mock-классы для macOS
├── routes_video.py     # MJPEG стрим
├── routes_ws.py        # WebSocket управление + телеметрия
├── routes_api.py       # REST API (config, status, models)
└── schemas.py          # Pydantic модели
frontend/          # Vite + React + TypeScript (веб-панель)
├── src/
│   ├── App.tsx         # Layout: видео + панель управления
│   ├── components/     # VideoFeed, MotorControl, ServoControl, LedControl, ...
│   ├── hooks/          # useWebSocket
│   └── lib/types.ts    # TypeScript интерфейсы
└── dist/               # Собранный бандл [.gitignore]
models/            # Обученные модели YOLO
├── yolo11_best_ncnn_model/  # YOLOv11n NCNN (дефолт для RPi, 14.6 FPS на RPi 5)
├── yolo11_best.pt           # YOLOv11n PyTorch (для GPU и разработки)
├── yolo11_best.onnx         # YOLOv11n ONNX (универсальный)
└── yolo8_best.pt            # YOLOv8n PyTorch (старая модель)
legacy/            # Старые скрипты (bench, camera_detect, camera_shot, train)
data.yaml          # Конфиг датасета (1 класс: sock, Roboflow v2, 961 изображение)
dataset/           # Приватный датасет (train/valid/test) [.gitignore]
pyproject.toml     # Зависимости проекта (uv/pip)
docs/
├── ru/            # Документация (на русском)
└── en/            # Documentation (English)
assets/            # Изображения проекта
```

## Tech Stack

- **Python 3.10+**, менеджер пакетов: **uv**
- **typer** — CLI-интерфейс
- **ultralytics** — YOLO v8/v11 (тренировка и инференс)
- **FastAPI + uvicorn** — веб-сервер управления роботом
- **React + TypeScript + Vite** — фронтенд веб-панели
- **picamera2 / libcamera** — камера Raspberry Pi (ставится только на RPi)
- **gpiozero / pigpio** — моторы, сервоприводы, сенсоры (только RPi)
- **OpenCV (cv2)** — обработка изображений, запись видео
- **numpy** — работа с массивами

## Setup

```bash
# Dev-машина (macOS)
uv venv && uv pip install typer ultralytics opencv-python-headless numpy fastapi uvicorn pydantic-settings websockets

# Frontend (один раз)
cd frontend && npm install && npm run build

# Raspberry Pi
sudo pip install fastapi uvicorn pydantic-settings websockets typer --break-system-packages
```

## Running (CLI)

```bash
# Веб-панель управления (macOS, mock-режим)
./main.py serve --mock

# Веб-панель управления (RPi, реальное железо)
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5

# Тренировка (на GPU-сервере или dev-машине)
./main.py train --device 0 --epochs 100

# Бенчмарк модели
./main.py bench

# Детекция носков с камеры RPi (требует sudo)
sudo ./main.py detect --model models/yolo11_best_ncnn_model --conf 0.5

# Сбор фото для датасета
sudo ./main.py shot --count 200 --output-dir images
```

## Code Style

- **black** — форматирование (через pre-commit)
- **flake8** — линтинг (max-line-length=140, ignore W503)
- Pre-commit хуки: `.pre-commit-config.yaml`
- Проверка: `pre-commit run --all-files`

## Key Conventions

- Комментарии и логи в коде — на русском языке
- Документация — на русском
- picamera2 не в pyproject.toml (linux-only, ставится вручную на RPi)

## Infrastructure

Подробности: [docs/ru/infrastructure.md](docs/ru/infrastructure.md), приватные данные: `docs/credentials.md` (не в git).

| Хост | Назначение |
|---|---|
| **rpi4** | Робот-танк legacy (RPi 4B, Debian bookworm) |
| **rpi5** | Робот-танк основной (RPi 5, Debian trixie 64-bit) |
| **blackops** | GPU-сервер для тренировки (RTX 4070 SUPER) |
| **rpi5** | Raspberry Pi 5 |

## Training

Тренировка выполняется на GPU-сервере (blackops):

```bash
ssh blackops
cd ~/work/test20250807_yolov8
source venv/bin/activate
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').train(data='data.yaml', epochs=100, batch=16, device=0)"
```

Или через CLI локально:
```bash
./main.py train --model yolov8n.pt --data data.yaml --epochs 100 --batch 16 --device 0
```

Устройства: `0` (NVIDIA CUDA), `mps` (Apple Silicon), `cpu` (фоллбэк).

## Модели

| Модель | Файл | mAP50 | mAP50-95 | Размер |
|---|---|---|---|---|
| YOLOv11n | `models/yolo11_best_ncnn_model/` | 0.995 | 0.96 | 10.4 MB | **RPi (продакшен)** |
| YOLOv11n | `models/yolo11_best.pt` | 0.995 | 0.96 | 5.2 MB | GPU, разработка |
| YOLOv8n | `models/yolo8_best.pt` | 0.995 | 0.885 | 6.0 MB | Старая модель |

## Deploy на робот

```bash
# Копировать проект на RPi
rsync -avz --exclude .venv --exclude frontend/node_modules --exclude __pycache__ --exclude .git \
  ~/work/SocksTank/ rpi5:~/sockstank/

# Запуск на RPi
ssh rpi5
cd ~/sockstank
sudo -E nohup python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 > /tmp/sockstank.log 2>&1 &
# Открыть http://rpi5:8080
```
