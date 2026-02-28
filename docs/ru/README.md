# SocksTank

<img align="left" width="200px" src="../../assets/SocksTank.jpeg">

**SocksTank** — робот-танк на базе Raspberry Pi 5 (ранее RPi 4B, legacy), который ищет носки по квартире с помощью компьютерного зрения (YOLO) и собирает их клешнёй. Включает веб-панель управления с живым видео и телеметрией.

Построен поверх [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi) (PCB Version V1.0, но поддерживается и V2.0).

<br clear="left">

## Что нужно для старта

### Железо

- **Raspberry Pi 5** (рекомендуется) или RPi 4B (legacy), с блоком питания и SD-картой (32 ГБ+)
- **Freenove Tank Robot Kit** ([GitHub](https://github.com/Freenove/Freenove_Tank_Robot_Kit_for_Raspberry_Pi)), PCB Version V1.0
  <br><img width="300" src="https://raw.githubusercontent.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/main/Picture/V1.0.jpg">
- **Камера ov5647** (OmniVision, входит в комплект Freenove)
- **GPU-сервер** для тренировки модели (NVIDIA, или Apple Silicon, или облако)

### Софт

- Python 3.10+
- [ultralytics](https://github.com/ultralytics/ultralytics) (YOLOv8/v11)
- [Roboflow](https://roboflow.com/) — для разметки датасета (бесплатный тариф)

## Quick Start

1. **Собрать танк** — [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi) ([инструкция в комплекте](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/blob/main/Tutorial.pdf))
2. **Настроить RPi 5** — [rpi5.md](rpi5.md) (или [RPi 4, legacy](rpi4.md))
3. **Собрать датасет** — [dataset.md](dataset.md)
4. **Обучить модель** — [training.md](training.md)
5. **Запустить и задеплоить проект** — [launch.md](launch.md)
6. **Запустить детекцию и веб-управление** — [inference.md](inference.md)

## Структура проекта

```
main.py              # CLI точка входа (typer): train, bench, detect, shot, serve
server/              # FastAPI backend (веб-панель управления)
frontend/            # Vite + React + TypeScript (веб-панель)
models/              # Обученные модели YOLO
├── yolo11_best_ncnn_model/  # YOLOv11n NCNN FP32 (RPi продакшен, 14.9 FPS)
├── yolo11_best.pt           # YOLOv11n PyTorch (GPU, разработка)
└── yolo8_best.pt            # YOLOv8n PyTorch (старая модель)
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
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5

# Тренировка модели (на GPU-сервере или dev-машине)
./main.py train --device 0 --epochs 100

# Бенчмарк модели
./main.py bench

# Детекция носков с камеры RPi (legacy)
sudo -E python main.py detect --model models/yolo11_best_ncnn_model --conf 0.5

# Сбор фото для датасета
sudo -E python main.py shot --count 200 --output-dir images
```

## Установка

```bash
# Dev-машина (macOS / Linux)
uv venv && uv pip install -e .
cd frontend && npm install && npm run build

# Raspberry Pi
sudo pip install . --break-system-packages
```

## Документация

* [**Запуск проекта**](launch.md) — сборка фронтенда, запуск бэкенда, деплой на RPi
* **Настройка Raspberry Pi**
    * [Настройка RPi 5 (рекомендуется)](rpi5.md)
    * [Настройка RPi 4 (legacy)](rpi4.md)
    * [Питание RPi 5](rpi5-power.md)
* **Подготовка датасета**
    * [Съёмка фотографий](dataset.md#съёмка-фотографий)
    * [Загрузка в Roboflow и аннотирование](dataset.md#загрузка-в-roboflow)
    * [Аугментация](dataset.md#аугментация)
    * [Экспорт датасета](dataset.md#экспорт-датасета)
* **Тренировка модели**
    * [Тренировка (GPU, Apple Silicon, CPU)](training.md#тренировка)
    * [Оценка результатов](training.md#оценка-результатов)
    * [Экспорт модели (ncnn для RPi)](training.md#экспорт-модели)
* **Инференс и веб-панель**
    * [Веб-панель управления](inference.md#веб-панель-управления-рекомендуемый-способ)
    * [Деплой на RPi](inference.md#деплой-на-rpi)
    * [Удалённый GPU-инференс](inference.md#удалённый-инференс-gpu-сервер)
    * [Интеграция с управлением танком](inference.md#интеграция-с-управлением-танком)
* **Бенчмарки**
    * [Бенчмарки инференса](benchmarks.md)
    * [Бенчмарки диска](disk-benchmarks.md)
* [**Инфраструктура**](infrastructure.md)
