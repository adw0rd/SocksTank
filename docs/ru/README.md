# SocksTank

<img align="left" width="200px" src="../../assets/SocksTank.jpeg">

**SocksTank** — робот-танк на базе Raspberry Pi 4B, который ищет носки по квартире с помощью компьютерного зрения (YOLOv8) и собирает их клешнёй.

Построен поверх [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi).

<br clear="left">

## Что нужно для старта

### Железо

- **Raspberry Pi 4B** (или RPi 5) с блоком питания и SD-картой (32 ГБ+)
- **Freenove Tank Robot Kit** ([GitHub](https://github.com/Freenove/Freenove_Tank_Robot_Kit_for_Raspberry_Pi))
- **Камера ov5647** (OmniVision, входит в комплект Freenove)
- **GPU-сервер** для тренировки модели (NVIDIA, или Apple Silicon, или облако)

### Софт

- Python 3.10+
- [ultralytics](https://github.com/ultralytics/ultralytics) (YOLOv8)
- [Roboflow](https://roboflow.com/) — для разметки датасета (бесплатный тариф)

## Quick Start

1. **Собрать танк** — Freenove Tank Robot Kit (инструкция в комплекте)
2. **Настроить RPi** — [rpi.md](rpi.md)
3. **Собрать датасет** — [dataset.md](dataset.md)
4. **Обучить модель** — [training.md](training.md)
5. **Запустить детекцию** — [inference.md](inference.md)

## Структура проекта

```
main.py              # CLI точка входа (typer): train, bench, detect, shot
camera_detect.py     # Legacy: инференс с камеры RPi → detect.mp4
camera_shot.py       # Legacy: серийная съёмка для датасета → images/
train.py             # Legacy: тренировка YOLOv8
bench.py             # Legacy: бенчмарк модели
data.yaml            # Конфиг датасета (1 класс: sock, Roboflow v2, 961 изображение)
best.pt              # Обученная модель YOLOv8n (mAP50=0.995) [.gitignore]
dataset/             # Приватный датасет (train/valid/test) [.gitignore]
pyproject.toml       # Зависимости проекта (uv/pip)
docs/
├── ru/                  # Документация (на русском)
│   ├── infrastructure.md  # Хосты, SSH, GPIO, аппаратная часть
│   ├── rpi.md             # Настройка Raspberry Pi
│   ├── dataset.md         # Подготовка датасета
│   ├── training.md        # Тренировка модели
│   └── inference.md       # Запуск на роботе
└── en/                  # Documentation (English)
    ├── infrastructure.md  # Hosts, SSH, GPIO, hardware
    ├── rpi.md             # Raspberry Pi setup
    ├── dataset.md         # Dataset preparation
    ├── training.md        # Model training
    └── inference.md       # Running on the robot
assets/              # Изображения проекта
```

## CLI-команды (main.py)

```bash
# Тренировка модели (на GPU-сервере или dev-машине)
./main.py train --device 0 --epochs 100

# Бенчмарк модели
./main.py bench

# Детекция носков с камеры RPi (требует sudo на RPi)
sudo ./main.py detect --model best.pt --conf 0.5

# Сбор фото для датасета (требует sudo на RPi)
sudo ./main.py shot --count 200 --output-dir images
```

## Установка

```bash
# Dev-машина (macOS / Linux)
uv venv && uv pip install typer ultralytics opencv-python-headless numpy

# Raspberry Pi (системные пакеты)
sudo pip install ultralytics[extra] --break-system-packages
```

## Документация

| Раздел | Описание |
|---|---|
| [Настройка Raspberry Pi](rpi.md) | Установка ОС, зависимости, камера, автозапуск |
| [Подготовка датасета](dataset.md) | Съёмка фото, Roboflow, аннотации, аугментация |
| [Тренировка модели](training.md) | Обучение YOLOv8, параметры, оценка, экспорт |
| [Запуск на роботе](inference.md) | Деплой модели, детекция, интеграция с танком |
| [Инфраструктура](infrastructure.md) | Хосты, SSH, GPIO, аппаратная часть |
