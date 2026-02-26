# SocksTank

<img align="left" width="200px" src="../../assets/SocksTank.jpeg">

**SocksTank** — робот-танк на базе Raspberry Pi 5 (ранее RPi 4B, legacy), который ищет носки по квартире с помощью компьютерного зрения (YOLO) и собирает их клешнёй. Включает веб-панель управления с живым видео и телеметрией.

Построен поверх [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi).

<br clear="left">

## Что нужно для старта

### Железо

- **Raspberry Pi 5** (рекомендуется) или RPi 4B (legacy), с блоком питания и SD-картой (32 ГБ+)
- **Freenove Tank Robot Kit** ([GitHub](https://github.com/Freenove/Freenove_Tank_Robot_Kit_for_Raspberry_Pi))
- **Камера ov5647** (OmniVision, входит в комплект Freenove)
- **GPU-сервер** для тренировки модели (NVIDIA, или Apple Silicon, или облако)

### Софт

- Python 3.10+
- [ultralytics](https://github.com/ultralytics/ultralytics) (YOLOv8/v11)
- [Roboflow](https://roboflow.com/) — для разметки датасета (бесплатный тариф)

## Quick Start

1. **Собрать танк** — Freenove Tank Robot Kit (инструкция в комплекте)
2. **Настроить RPi** — [rpi4.md (legacy)](rpi4.md)
3. **Собрать датасет** — [dataset.md](dataset.md)
4. **Обучить модель** — [training.md](training.md)
5. **Запустить детекцию** — [inference.md](inference.md)

## Структура проекта

```
main.py              # CLI точка входа (typer): train, bench, detect, shot, serve
server/              # FastAPI backend (веб-панель управления)
frontend/            # Vite + React + TypeScript (веб-панель)
models/              # Обученные модели YOLO
├── yolo8_best.pt    # YOLOv8n (mAP50=0.995, mAP50-95=0.885)
└── yolo11_best.pt   # YOLOv11n (mAP50=0.995, mAP50-95=0.96)
legacy/              # Старые скрипты (bench, camera_detect, camera_shot, train)
data.yaml            # Конфиг датасета (1 класс: sock, Roboflow v2, 961 изображение)
dataset/             # Приватный датасет (train/valid/test) [.gitignore]
pyproject.toml       # Зависимости проекта (uv/pip)
docs/
├── ru/              # Документация (на русском)
└── en/              # Documentation (English)
assets/              # Изображения проекта
```

## CLI-команды (main.py)

```bash
# Веб-панель управления (macOS, mock-режим)
./main.py serve --mock

# Веб-панель управления (RPi, реальное железо)
sudo -E python main.py serve --model models/yolo11_best.pt --conf 0.5

# Тренировка модели (на GPU-сервере или dev-машине)
./main.py train --device 0 --epochs 100

# Бенчмарк модели
./main.py bench

# Детекция носков с камеры RPi (legacy)
sudo -E python main.py detect --model models/yolo8_best.pt --conf 0.5

# Сбор фото для датасета
sudo -E python main.py shot --count 200 --output-dir images
```

## Установка

```bash
# Dev-машина (macOS / Linux)
uv venv && uv pip install typer ultralytics opencv-python-headless numpy fastapi uvicorn pydantic-settings websockets
cd frontend && npm install && npm run build

# Raspberry Pi
sudo pip install fastapi uvicorn pydantic-settings websockets typer --break-system-packages
```

## Документация

| Раздел | Описание |
|---|---|
| [Настройка RPi 4 (legacy)](rpi4.md) | Установка ОС, зависимости, камера, автозапуск |
| [Настройка RPi 5](rpi5.md) | Характеристики, питание, отличия от RPi 4 (legacy) |
| [Подготовка датасета](dataset.md) | Съёмка фото, Roboflow, аннотации, аугментация |
| [Тренировка модели](training.md) | Обучение YOLO, параметры, оценка, экспорт |
| [Запуск на роботе](inference.md) | Веб-панель, деплой, детекция, интеграция с танком |
| [Инфраструктура](infrastructure.md) | Хосты, SSH, GPIO, аппаратная часть |
