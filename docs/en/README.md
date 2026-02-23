# SocksTank

<img align="left" width="200px" src="../../assets/SocksTank.jpeg">

**SocksTank** is a Raspberry Pi 4B-based robot tank that hunts for socks around the apartment using computer vision (YOLOv8) and picks them up with a claw.

Built on top of [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi).

<br clear="left">

## What you need

### Hardware

- **Raspberry Pi 4B** (or RPi 5) with power supply and SD card (32 GB+)
- **Freenove Tank Robot Kit** ([GitHub](https://github.com/Freenove/Freenove_Tank_Robot_Kit_for_Raspberry_Pi))
- **ov5647 camera** (OmniVision, included in the Freenove kit)
- **GPU server** for model training (NVIDIA, Apple Silicon, or cloud)

### Software

- Python 3.10+
- [ultralytics](https://github.com/ultralytics/ultralytics) (YOLOv8)
- [Roboflow](https://roboflow.com/) — for dataset annotation (free tier)

## Quick Start

1. **Assemble the tank** — Freenove Tank Robot Kit (instructions included)
2. **Set up RPi** — [rpi.md](rpi.md)
3. **Collect dataset** — [dataset.md](dataset.md)
4. **Train model** — [training.md](training.md)
5. **Run detection** — [inference.md](inference.md)

## Project structure

```
main.py              # CLI entry point (typer): train, bench, detect, shot
camera_detect.py     # Legacy: inference from RPi camera → detect.mp4
camera_shot.py       # Legacy: burst capture for dataset → images/
train.py             # Legacy: YOLOv8 training
bench.py             # Legacy: model benchmark
data.yaml            # Dataset config (1 class: sock, Roboflow v2, 961 images)
best.pt              # Trained YOLOv8n model (mAP50=0.995) [.gitignore]
dataset/             # Private dataset (train/valid/test) [.gitignore]
pyproject.toml       # Project dependencies (uv/pip)
docs/
├── ru/                  # Documentation (Russian)
└── en/                  # Documentation (English)
    ├── infrastructure.md  # Hosts, SSH, GPIO, hardware
    ├── rpi.md             # Raspberry Pi setup
    ├── dataset.md         # Dataset preparation
    ├── training.md        # Model training
    └── inference.md       # Running on the robot
assets/              # Project images
```

## CLI commands (main.py)

```bash
# Train model (on GPU server or dev machine)
./main.py train --device 0 --epochs 100

# Benchmark model
./main.py bench

# Detect socks from RPi camera (requires sudo on RPi)
sudo ./main.py detect --model best.pt --conf 0.5

# Capture photos for dataset (requires sudo on RPi)
sudo ./main.py shot --count 200 --output-dir images
```

## Installation

```bash
# Dev machine (macOS / Linux)
uv venv && uv pip install typer ultralytics opencv-python-headless numpy

# Raspberry Pi (system packages)
sudo pip install ultralytics[extra] --break-system-packages
```

## Documentation

| Section | Description |
|---|---|
| [Raspberry Pi setup](rpi.md) | OS installation, dependencies, camera, autostart |
| [Dataset preparation](dataset.md) | Photo capture, Roboflow, annotation, augmentation |
| [Model training](training.md) | YOLOv8 training, parameters, evaluation, export |
| [Running on the robot](inference.md) | Model deployment, detection, tank integration |
| [Infrastructure](infrastructure.md) | Hosts, SSH, GPIO, hardware |
