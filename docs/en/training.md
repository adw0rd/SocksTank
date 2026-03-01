# Model Training

🇷🇺 [Русская версия](../ru/training.md)

Training a YOLO model for sock detection. Training requires a GPU — on CPU it would take too long.

## Where to train

| Device | Flag | Time (100 epochs) |
|---|---|---|
| NVIDIA GPU (RTX 4070 Super) | `--device 0` | ~15 min |
| Apple Silicon (M3 Pro) | `--device mps` | ~20 min |
| CPU | `--device cpu` | several hours |

This project uses a dedicated NVIDIA GPU server for training.

Before using `ssh blackops` in the examples below, make sure this host alias is configured in `~/.ssh/config` (and optionally in `/etc/hosts`). See: [infrastructure.md](infrastructure.md#networking)

## Setting up the environment

### GPU server (Ubuntu + NVIDIA)

```bash
ssh blackops

# Verify GPU is available
nvidia-smi

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install ultralytics
```

### Apple Silicon (macOS)

```bash
uv venv && uv pip install ultralytics
```

MPS (Metal Performance Shaders) is supported by ultralytics out of the box.

## Training

### Via CLI (main.py)

```bash
# Full training (100 epochs, GPU)
./main.py train --model yolov8n.pt --data data.yaml --epochs 100 --batch 16 --device 0

# Quick test (10 epochs, Apple Silicon)
./main.py train --model yolov8n.pt --data data.yaml --epochs 10 --batch 8 --device mps

# On CPU (slow, for verification only)
./main.py train --model yolov8n.pt --data data.yaml --epochs 10 --batch 4 --device cpu
```

### Via yolo CLI

```bash
yolo task=detect mode=train model=yolov8n.pt imgsz=640 data=data.yaml epochs=100 batch=16
```

### Via Python API

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model.train(data="data.yaml", epochs=100, imgsz=640, batch=16, device="0")
```

### Training parameters

| Parameter | Value | Description |
|---|---|---|
| `--model` | `yolov8n.pt` | Base model (nano — lightest, suitable for RPi) |
| `--data` | `data.yaml` | Dataset config |
| `--epochs` | `100` | Number of epochs |
| `--imgsz` | `640` | Image size (px) |
| `--batch` | `16` | Batch size (reduce if not enough VRAM) |
| `--device` | `0` / `mps` / `cpu` | Training device |

## Evaluating results

After training, ultralytics saves results to `runs/detect/train/`:

```
runs/detect/train/
├── weights/
│   ├── best.pt              # Best model (by mAP50)
│   └── last.pt              # Last epoch
├── results.csv              # Metrics per epoch
├── confusion_matrix.png     # Confusion matrix
├── F1_curve.png             # F1 curve
├── P_curve.png              # Precision curve
├── R_curve.png              # Recall curve
└── results.png              # Metric plots
```

### Key metrics

- **Precision** — fraction of correct detections among all detections
- **Recall** — fraction of found objects among all real objects
- **mAP50** — mean average precision at IoU=0.5 (primary metric)
- **mAP50-95** — mean average precision at IoU 0.5 to 0.95

In practice: use **mAP50** as the main quick quality signal, and **mAP50-95** as the stricter metric that better reflects box quality across different IoU thresholds.

### Trained model results

| Model | mAP50 | mAP50-95 | Size | File |
|---|---|---|---|---|
| YOLOv8n (100 epochs) | 0.995 | 0.885 | 6.0 MB | `models/yolo8_best.pt` |
| YOLOv11n (100 epochs) | 0.995 | 0.96 | 5.2 MB | `models/yolo11_best.pt` |

### Benchmark

To evaluate inference speed across different formats:

```bash
./main.py bench --model best.pt
```

## Model export

After training, the `.pt` model should be exported to a deployment format for RPi.

### Recommended format: NCNN

**NCNN** (Tencent) is optimized for ARM processors. On RPi 5 it delivers **15.8 FPS** (pure inference) / **14.9 FPS** (with preprocessing) via pip ncnn + OMP workaround, vs 3.5 FPS for PyTorch.

| Format | RPi 5 FPS | Recommendation |
|---|---|---|
| **pip ncnn native (4 OMP)** | **14.9–15.8** | ✅ Production on RPi (`NcnnNativeDetector`) |
| NCNN (ultralytics) | 11.2 | Alternative (without OMP workaround) |
| ONNX | 3.0 | Slower, crashes on RPi 4 (legacy) |
| PyTorch (.pt) | 3.5 | Development and GPU only |

Quick rule of thumb:
- use **NCNN** for deployment on Raspberry Pi;
- keep **`.pt`** for training, debugging, and GPU hosts;
- use **ONNX** only if you specifically need cross-framework compatibility.

### Pipeline: train → export → deploy

```bash
# 1. Train the model (on the GPU server)
ssh blackops
cd ~/work/test20250807_yolov8
python -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
model.train(data='data.yaml', epochs=100, batch=16, device=0)
"
# Result: runs/detect/train/weights/best.pt

# 2. Export to NCNN (on dev machine or GPU server)
python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/train/weights/best.pt')
model.export(format='ncnn')
"
# Result: runs/detect/train/weights/best_ncnn_model/
#   ├── model.ncnn.param   (model graph, ~22 KB)
#   ├── model.ncnn.bin     (weights, ~10 MB)
#   └── metadata.yaml      (ultralytics metadata)

# 3. Copy to RPi
scp -r runs/detect/train/weights/best_ncnn_model rpi5:~/sockstank/models/yolo11_best_ncnn_model

# 4. Run SocksTank on RPi
ssh rpi5
cd ~/sockstank
sudo -E python3 main.py serve --model models/yolo11_best_ncnn_model --conf 0.5
```

### Export via CLI

```bash
# NCNN (recommended for RPi)
yolo export model=best.pt format=ncnn imgsz=640

# ONNX (generic)
yolo export model=best.pt format=onnx imgsz=640
```

### Export via Python

```python
from ultralytics import YOLO

model = YOLO("best.pt")

# NCNN
model.export(format="ncnn")  # -> best_ncnn_model/

# ONNX
model.export(format="onnx")  # -> best.onnx
```

### Export arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `format` | str | `torchscript` | Export format: `ncnn`, `onnx`, `torchscript`, `engine` (TensorRT) |
| `imgsz` | int/tuple | `640` | Input image size |
| `half` | bool | `False` | FP16 quantization |
| `int8` | bool | `False` | INT8 quantization (for edge devices) |
| `simplify` | bool | `True` | Simplify model graph (ONNX) |
| `dynamic` | bool | `False` | Dynamic input sizes (ONNX, TensorRT) |
| `device` | str | `None` | Device: `0` (GPU), `cpu`, `mps` |
| `data` | str | `coco8.yaml` | Dataset path for INT8 calibration |

### Current models in the project

| Model | Format | File | Size | Purpose |
|---|---|---|---|---|
| YOLOv11n | PyTorch | `models/yolo11_best.pt` | 5.2 MB | GPU, development |
| YOLOv11n | NCNN | `models/yolo11_best_ncnn_model/` | 10.4 MB | **RPi production** |
| YOLOv11n | ONNX | `models/yolo11_best.onnx` | 10.1 MB | Generic |
| YOLOv8n | PyTorch | `models/yolo8_best.pt` | 6.0 MB | Older model |

---

| ← Previous | README | Next → |
|---|---|---|
| [Dataset Preparation](dataset.md) | [Back to README](README.md) | [Running the Project](launch.md) |
