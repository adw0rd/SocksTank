# CLAUDE.md

## Project Overview

SocksTank — a Raspberry Pi 5-based tank robot (formerly RPi 4B, legacy) that searches for socks around the apartment using computer vision (YOLO) and picks them up with a claw. Built on top of [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi) (PCB Version V1.0, but V2.0 is also supported).

## Project Structure

```
main.py            # CLI entry point (typer): train, bench, detect, shot, serve
server/            # FastAPI backend (web control panel)
├── app.py         # FastAPI app factory, lifespan, mount static
├── config.py      # Pydantic Settings
├── camera.py      # CameraManager: picamera2 + YOLO → MJPEG
├── cpu_warmup.py  # Gradual CPU warmup (staged core loading for RPi 5)
├── hardware.py    # HardwareController: Motor/Servo/Led/Ultrasonic/Infrared
├── freenove_bridge.py  # Load drivers (drivers/) or mock fallback
├── mock.py        # Mock classes for macOS
├── drivers/       # Internalized Freenove drivers (PCB v1 + v2)
│   ├── _detect.py     # Auto-detect RPi version
│   ├── motor.py       # Motors (gpiozero)
│   ├── servo.py       # Servos (pigpio/gpiozero/HardwarePWM)
│   ├── ultrasonic.py  # Ultrasonic sensor (gpiozero)
│   ├── infrared.py    # IR sensors (gpiozero)
│   └── led.py         # LED strip (rpi_ws281x/SPI/noop)
├── routes_video.py     # MJPEG stream
├── routes_ws.py        # WebSocket control + telemetry
├── routes_api.py       # REST API (config, status, models)
└── schemas.py          # Pydantic models
frontend/          # Vite + React + TypeScript (web panel)
├── src/
│   ├── App.tsx         # Layout: video + control panel
│   ├── components/     # VideoFeed, MotorControl, ServoControl, LedControl, ...
│   ├── hooks/          # useWebSocket
│   └── lib/types.ts    # TypeScript interfaces
└── dist/               # Built bundle [.gitignore]
models/            # Trained YOLO models
├── yolo11_best_ncnn_model/  # YOLOv11n NCNN FP32 (default, 12.8–16.0 FPS pip ncnn + OMP workaround on RPi 5)
├── yolo11_best.pt           # YOLOv11n PyTorch (GPU and development)
├── yolo11_best.onnx         # YOLOv11n ONNX (universal)
├── yolo11_best_ncnn_int8_model/  # YOLOv11n NCNN INT8 (2.6 MB, quantized)
└── yolo8_best.pt            # YOLOv8n PyTorch (old model)
ncnn_wrapper/      # C++ ncnn wrapper (legacy, not needed — pip ncnn + OMP workaround is faster)
legacy/            # Old scripts (bench, camera_detect, camera_shot, train)
data.yaml          # Dataset config (1 class: sock, Roboflow v2, 961 images)
dataset/           # Private dataset (train/valid/test) [.gitignore]
pyproject.toml     # Project dependencies (uv/pip)
docs/
├── ru/            # Documentation (Russian)
└── en/            # Documentation (English)
assets/            # Project images
```

## Tech Stack

- **Python 3.10+**, package manager: **uv**
- **typer** — CLI interface
- **ultralytics** — YOLO v8/v11 (training and inference)
- **FastAPI + uvicorn** — robot control web server
- **React + TypeScript + Vite** — web panel frontend
- **picamera2 / libcamera** — Raspberry Pi camera (RPi only)
- **gpiozero / pigpio** — motors, servos, sensors (RPi only)
- **OpenCV (cv2)** — image processing, video recording
- **numpy** — array operations

## Setup

```bash
# Dev machine (macOS / Linux)
uv venv && uv pip install -e .

# Frontend (once)
cd frontend && npm install && npm run build

# Raspberry Pi
sudo pip install . --break-system-packages
```

## Running (CLI)

```bash
# Web control panel (macOS, mock mode)
./main.py serve --mock

# Web control panel (RPi, real hardware, gradual warmup by default)
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5

# With NcnnNativeDetector (pip ncnn + OMP workaround, 12.8–16.0 FPS)
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --ncnn-cpp --ncnn-threads 4
# --ncnn-cpp enables NcnnNativeDetector (server/inference.py), NOT C++ wrapper

# Training (on GPU server or dev machine)
./main.py train --device 0 --epochs 100

# Model benchmark
./main.py bench

# Sock detection from RPi camera (requires sudo)
sudo ./main.py detect --model models/yolo11_best_ncnn_model --conf 0.5

# Capture photos for dataset
sudo ./main.py shot --count 200 --output-dir images
```

## Code Style

- **black** — formatting (via pre-commit)
- **flake8** — linting (max-line-length=140, ignore W503)
- Pre-commit hooks: `.pre-commit-config.yaml`
- Check: `pre-commit run --all-files`

## Key Conventions

- Code, comments, log messages, commits — in English
- Documentation — bilingual (docs/ru/ and docs/en/)
- picamera2 is not in pyproject.toml (linux-only, installed manually on RPi)

## Infrastructure

Details: [docs/en/infrastructure.md](docs/en/infrastructure.md), private data: `docs/credentials.md` (not in git).

| Host | Purpose |
|---|---|
| **rpi5** | Main tank robot (RPi 5, Debian 13 trixie 64-bit, Python 3.13) |
| **rpi4** (legacy) | Old tank robot (RPi 4B, Debian 12 bookworm 64-bit, Python 3.11) |
| **blackops** | GPU training server (RTX 4070 SUPER) |

## Training

Training runs on the GPU server (blackops):

```bash
ssh blackops
cd ~/work/test20250807_yolov8
source venv/bin/activate
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').train(data='data.yaml', epochs=100, batch=16, device=0)"
```

Or via CLI locally:
```bash
./main.py train --model yolov8n.pt --data data.yaml --epochs 100 --batch 16 --device 0
```

Devices: `0` (NVIDIA CUDA), `mps` (Apple Silicon), `cpu` (fallback).

## Models

| Model | File | mAP50 | mAP50-95 | Size |
|---|---|---|---|---|
| YOLOv11n | `models/yolo11_best_ncnn_model/` | 0.995 | 0.96 | 9.9 MB | **RPi production (FP32)** |
| YOLOv11n | `models/yolo11_best_ncnn_int8_model/` | ~0.98 | ~0.94 | 2.6 MB | **RPi INT8 (quantized)** |
| YOLOv11n | `models/yolo11_best.pt` | 0.995 | 0.96 | 5.2 MB | GPU, development |
| YOLOv8n | `models/yolo8_best.pt` | 0.995 | 0.885 | 6.0 MB | Old model |

## Deploy to Robot

```bash
# Copy project to RPi
rsync -avz --exclude .venv --exclude frontend/node_modules --exclude __pycache__ --exclude .git \
  ~/work/SocksTank/ rpi5:~/sockstank/

# Run on RPi
ssh rpi5
cd ~/sockstank
sudo -E nohup python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 > /tmp/sockstank.log 2>&1 &
# Open http://rpi5:8080
```
