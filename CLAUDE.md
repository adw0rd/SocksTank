# CLAUDE.md

## Project Overview

SocksTank — робот-танк на базе Raspberry Pi 4B, который ищет носки по квартире с помощью компьютерного зрения (YOLO) и собирает их клешнёй. Построен поверх [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi).

## Project Structure

```
main.py            # CLI точка входа (typer): train, bench, detect, shot
camera_detect.py   # Legacy: инференс с камеры RPi → detect.mp4
camera_shot.py     # Legacy: серийная съёмка для датасета → images/
train.py           # Legacy: тренировка YOLOv8
bench.py           # Legacy: бенчмарк модели
data.yaml          # Конфиг датасета (1 класс: sock, Roboflow v2, 961 изображение)
best.pt            # Обученная модель YOLOv8n (100 эпох, mAP50=0.995) [.gitignore]
dataset/           # Приватный датасет (train/valid/test) [.gitignore]
pyproject.toml     # Зависимости проекта (uv/pip)
docs/
├── ru/                # Документация (на русском)
│   └── infrastructure.md  # Хосты, SSH, GPIO, аппаратная часть
└── en/                # Documentation (English)
assets/            # Изображения проекта
```

## Tech Stack

- **Python 3.10+**, менеджер пакетов: **uv**
- **typer** — CLI-интерфейс
- **ultralytics** — YOLO v8/v11 (тренировка и инференс)
- **picamera2 / libcamera** — камера Raspberry Pi (ставится только на RPi)
- **gpiozero / pigpio** — моторы, сервоприводы, сенсоры (только RPi)
- **OpenCV (cv2)** — обработка изображений, запись видео
- **numpy** — работа с массивами

## Setup

```bash
# Dev-машина (macOS)
uv venv && uv pip install typer ultralytics opencv-python-headless numpy

# Raspberry Pi (всё уже установлено системно)
sudo pip install picamera2 ultralytics --break-system-packages
```

## Running (CLI)

```bash
# Тренировка (на GPU-сервере или dev-машине)
./main.py train --device 0 --epochs 100

# Бенчмарк модели
./main.py bench

# Детекция носков с камеры RPi (требует sudo)
sudo ./main.py detect --model best.pt --conf 0.5

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
| **rpi4** | Робот-танк (RPi 4B, Debian bookworm) |
| **GPU-сервер** | Тренировка моделей YOLO (NVIDIA GPU) |
| **rpi5** | Raspberry Pi 5 |

## Training

Тренировка выполняется на GPU-сервере:

```bash
ssh gpu-server
cd ~/work/test20250807_yolov8
python train.py  # 100 эпох, YOLOv8n, data.yaml
```

Или через CLI локально:
```bash
./main.py train --model yolov8n.pt --data data.yaml --epochs 100 --batch 16 --device 0
```

Устройства: `0` (NVIDIA CUDA), `mps` (Apple Silicon), `cpu` (фоллбэк).

## Deploy на робот

```bash
scp best.pt rpi:~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/
ssh rpi "cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server && sudo python camera_detect.py"
```
