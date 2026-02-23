# Model Training

Training a YOLOv8 model for sock detection. Training requires a GPU — on CPU it would take too long.

## Where to train

| Device | Flag | Time (100 epochs) |
|---|---|---|
| NVIDIA GPU (RTX 4070 Super) | `--device 0` | ~15 min |
| Apple Silicon (M3 Pro) | `--device mps` | ~20 min |
| CPU | `--device cpu` | several hours |

## Setting up the environment

### GPU server (Ubuntu + NVIDIA)

```bash
ssh gpu-server

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

- **mAP50** — mean average precision at IoU=0.5 (primary metric). Current result: **0.995**
- **mAP50-95** — mean average precision at IoU 0.5 to 0.95. Current result: **0.885**
- **Precision** — fraction of correct detections among all detections
- **Recall** — fraction of found objects among all real objects

### Benchmark

To evaluate inference speed across different formats:

```bash
./main.py bench --model best.pt
```

## Model export

For running on Raspberry Pi you can export the model to **ncnn** format — optimized for ARM processors:

```bash
yolo export model=best.pt format=ncnn imgsz=640
```

Or via Python:

```python
from ultralytics import YOLO

model = YOLO("best.pt")
model.export(format="ncnn")
```

### Export arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `format` | str | `torchscript` | Export format: `onnx`, `torchscript`, `engine` (TensorRT), `ncnn`, etc. |
| `imgsz` | int/tuple | `640` | Input image size |
| `half` | bool | `False` | FP16 quantization (reduces size, speeds up inference) |
| `int8` | bool | `False` | INT8 quantization (maximum compression, for edge devices) |
| `optimize` | bool | `False` | Mobile optimization (TorchScript). Incompatible with ncnn and CUDA |
| `dynamic` | bool | `False` | Dynamic input sizes (ONNX, TensorRT, OpenVINO) |
| `simplify` | bool | `True` | Simplify model graph (ONNX) |
| `nms` | bool | `False` | Add NMS to exported model |
| `batch` | int | `1` | Inference batch size |
| `device` | str | `None` | Device: `0` (GPU), `cpu`, `mps`, `dla:0` (Jetson) |
| `data` | str | `coco8.yaml` | Dataset path (for INT8 calibration) |
| `workspace` | float/None | `None` | Max workspace size (GiB) for TensorRT |
| `opset` | int | `None` | ONNX opset version |
| `fraction` | float | `1.0` | Dataset fraction for INT8 calibration |

---

Next step: [Running on the robot](inference.md)
