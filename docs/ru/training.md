# Тренировка модели

Обучение модели YOLO для распознавания носков. Тренировка требует GPU — на CPU она займёт слишком много времени.

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
ssh blackops

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

- **mAP50** — средняя точность при IoU=0.5 (основная метрика)
- **mAP50-95** — средняя точность при IoU от 0.5 до 0.95

### Результаты обученных моделей

| Модель | mAP50 | mAP50-95 | Размер | Файл |
|---|---|---|---|---|
| YOLOv8n (100 эпох) | 0.995 | 0.885 | 6.0 MB | `models/yolo8_best.pt` |
| YOLOv11n (100 эпох) | 0.995 | 0.96 | 5.2 MB | `models/yolo11_best.pt` |
- **Precision** — доля верных детекций среди всех детекций
- **Recall** — доля найденных объектов среди всех реальных объектов

### Бенчмарк

Для оценки скорости инференса на разных форматах:

```bash
./main.py bench --model best.pt
```

## Экспорт модели

После тренировки `.pt` модель нужно экспортировать в формат для деплоя на RPi.

### Рекомендуемый формат: NCNN

**NCNN** (Tencent) — оптимизирован для ARM-процессоров. На RPi 5 даёт **15.8 FPS** (чистый инференс) / **14.9 FPS** (с препроцессингом) через pip ncnn + OMP workaround vs 3.5 FPS PyTorch.

| Формат | RPi 5 FPS | Рекомендация |
|---|---|---|
| **pip ncnn native (4 OMP)** | **14.9–15.8** | ✅ Для продакшена на RPi (`NcnnNativeDetector`) |
| NCNN (ultralytics) | 11.2 | Альтернатива (без OMP workaround) |
| ONNX | 3.0 | Медленнее, крашит RPi 4 (legacy) |
| PyTorch (.pt) | 3.5 | Для разработки и GPU |

### Пайплайн: обучение → экспорт → деплой

```bash
# 1. Обучить модель (на GPU-сервере)
ssh blackops
cd ~/work/test20250807_yolov8
python -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
model.train(data='data.yaml', epochs=100, batch=16, device=0)
"
# Результат: runs/detect/train/weights/best.pt

# 2. Экспортировать в NCNN (на dev-машине или GPU-сервере)
python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/train/weights/best.pt')
model.export(format='ncnn')
"
# Результат: runs/detect/train/weights/best_ncnn_model/
#   ├── model.ncnn.param   (граф модели, ~22 KB)
#   ├── model.ncnn.bin     (веса, ~10 MB)
#   └── metadata.yaml      (метаданные ultralytics)

# 3. Скопировать на RPi
scp -r runs/detect/train/weights/best_ncnn_model rpi5:~/sockstank/models/yolo11_best_ncnn_model

# 4. Запустить SocksTank (NCNN — дефолт)
ssh rpi5
cd ~/sockstank
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5
```

### Экспорт через CLI

```bash
# NCNN (рекомендуется для RPi)
yolo export model=best.pt format=ncnn imgsz=640

# ONNX (универсальный)
yolo export model=best.pt format=onnx imgsz=640
```

### Экспорт через Python

```python
from ultralytics import YOLO

model = YOLO("best.pt")

# NCNN
model.export(format="ncnn")  # → best_ncnn_model/

# ONNX
model.export(format="onnx")  # → best.onnx
```

### Аргументы экспорта

| Аргумент | Тип | По умолчанию | Описание |
|---|---|---|---|
| `format` | str | `torchscript` | Формат: `ncnn`, `onnx`, `torchscript`, `engine` (TensorRT) |
| `imgsz` | int/tuple | `640` | Размер входного изображения |
| `half` | bool | `False` | FP16-квантизация |
| `int8` | bool | `False` | INT8-квантизация (для edge-устройств) |
| `simplify` | bool | `True` | Упрощение графа (ONNX) |
| `dynamic` | bool | `False` | Динамические размеры входа (ONNX, TensorRT) |
| `device` | str | `None` | Устройство: `0` (GPU), `cpu`, `mps` |
| `data` | str | `coco8.yaml` | Датасет для INT8-калибровки |

### Текущие модели в проекте

| Модель | Формат | Файл | Размер | Назначение |
|---|---|---|---|---|
| YOLOv11n | PyTorch | `models/yolo11_best.pt` | 5.2 MB | GPU, разработка |
| YOLOv11n | NCNN | `models/yolo11_best_ncnn_model/` | 10.4 MB | **RPi (продакшен)** |
| YOLOv11n | ONNX | `models/yolo11_best.onnx` | 10.1 MB | Универсальный |
| YOLOv8n | PyTorch | `models/yolo8_best.pt` | 6.0 MB | Старая модель |

---

Следующий шаг: [Запуск на роботе](inference.md)
