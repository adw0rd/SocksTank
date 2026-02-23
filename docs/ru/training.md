# Тренировка модели

Обучение модели YOLOv8 для распознавания носков. Тренировка требует GPU — на CPU она займёт слишком много времени.

## Где тренировать

| Устройство | Команда | Время (100 эпох) |
|---|---|---|
| NVIDIA GPU (RTX 4070 Super) | `--device 0` | ~15 мин |
| Apple Silicon (M3 Pro) | `--device mps` | ~20 мин |
| CPU | `--device cpu` | несколько часов |

В проекте используется отдельный GPU-сервер с NVIDIA.

## Подготовка окружения

### GPU-сервер (Ubuntu + NVIDIA)

```bash
ssh gpu-server

# Проверить, что GPU доступен
nvidia-smi

# Установить зависимости
python3 -m venv venv
source venv/bin/activate
pip install ultralytics
```

### Apple Silicon (macOS)

```bash
uv venv && uv pip install ultralytics
```

MPS (Metal Performance Shaders) поддерживается ultralytics из коробки.

## Тренировка

### Через CLI (main.py)

```bash
# Полная тренировка (100 эпох, GPU)
./main.py train --model yolov8n.pt --data data.yaml --epochs 100 --batch 16 --device 0

# Быстрый тест (10 эпох, Apple Silicon)
./main.py train --model yolov8n.pt --data data.yaml --epochs 10 --batch 8 --device mps

# На CPU (медленно, только для проверки)
./main.py train --model yolov8n.pt --data data.yaml --epochs 10 --batch 4 --device cpu
```

### Через yolo CLI

```bash
yolo task=detect mode=train model=yolov8n.pt imgsz=640 data=data.yaml epochs=100 batch=16
```

### Через Python API

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model.train(data="data.yaml", epochs=100, imgsz=640, batch=16, device="0")
```

### Параметры тренировки

| Параметр | Значение | Описание |
|---|---|---|
| `--model` | `yolov8n.pt` | Базовая модель (nano — самая лёгкая, подходит для RPi) |
| `--data` | `data.yaml` | Конфиг датасета |
| `--epochs` | `100` | Количество эпох |
| `--imgsz` | `640` | Размер изображения (px) |
| `--batch` | `16` | Размер батча (уменьшить, если не хватает VRAM) |
| `--device` | `0` / `mps` / `cpu` | Устройство для тренировки |

## Оценка результатов

После тренировки ultralytics сохраняет результаты в папку `runs/detect/train/`:

```
runs/detect/train/
├── weights/
│   ├── best.pt              # Лучшая модель (по mAP50)
│   └── last.pt              # Последняя эпоха
├── results.csv              # Метрики по эпохам
├── confusion_matrix.png     # Матрица ошибок
├── F1_curve.png             # F1-кривая
├── P_curve.png              # Precision-кривая
├── R_curve.png              # Recall-кривая
└── results.png              # Графики метрик
```

### Ключевые метрики

- **mAP50** — средняя точность при IoU=0.5 (основная метрика). Текущий результат: **0.995**
- **mAP50-95** — средняя точность при IoU от 0.5 до 0.95. Текущий результат: **0.885**
- **Precision** — доля верных детекций среди всех детекций
- **Recall** — доля найденных объектов среди всех реальных объектов

### Бенчмарк

Для оценки скорости инференса на разных форматах:

```bash
./main.py bench --model best.pt
```

## Экспорт модели

Для запуска на Raspberry Pi модель можно экспортировать в формат **ncnn** — он оптимизирован для ARM-процессоров:

```bash
yolo export model=best.pt format=ncnn imgsz=640
```

Или через Python:

```python
from ultralytics import YOLO

model = YOLO("best.pt")
model.export(format="ncnn")
```

### Таблица аргументов экспорта

| Аргумент | Тип | По умолчанию | Описание |
|---|---|---|---|
| `format` | str | `torchscript` | Формат экспорта: `onnx`, `torchscript`, `engine` (TensorRT), `ncnn` и др. |
| `imgsz` | int/tuple | `640` | Размер входного изображения |
| `half` | bool | `False` | FP16-квантизация (уменьшает размер, ускоряет инференс) |
| `int8` | bool | `False` | INT8-квантизация (максимальное сжатие, для edge-устройств) |
| `optimize` | bool | `False` | Оптимизация для мобильных устройств (TorchScript). Несовместимо с ncnn и CUDA |
| `dynamic` | bool | `False` | Динамические размеры входа (ONNX, TensorRT, OpenVINO) |
| `simplify` | bool | `True` | Упрощение графа модели (ONNX) |
| `nms` | bool | `False` | Добавить NMS в экспортированную модель |
| `batch` | int | `1` | Размер батча для инференса |
| `device` | str | `None` | Устройство: `0` (GPU), `cpu`, `mps`, `dla:0` (Jetson) |
| `data` | str | `coco8.yaml` | Путь к датасету (для INT8-калибровки) |
| `workspace` | float/None | `None` | Макс. размер workspace (ГиБ) для TensorRT |
| `opset` | int | `None` | Версия ONNX opset |
| `fraction` | float | `1.0` | Доля датасета для INT8-калибровки |

---

Следующий шаг: [Запуск на роботе](inference.md)
