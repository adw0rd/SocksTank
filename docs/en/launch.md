# Running the Project

How to build the frontend, run the backend, and deploy SocksTank on the robot.

## Development on macOS / Linux

### 1. Install dependencies

```bash
cd ~/work/SocksTank

# Python (via uv, recommended)
uv venv && uv pip install -e .

# Or via pip
pip install -e .
```

### 2. Build frontend

```bash
cd frontend
npm install        # once
npm run build      # builds to frontend/dist/
```

### 3. Run (mock mode)

```bash
./main.py serve --mock
```

Open: **http://localhost:8080**

The `--mock` flag replaces GPIO, camera, and sensors with stubs — develop without RPi hardware.

### Development mode with hot-reload

For frontend development — two terminals:

```bash
# Terminal 1: backend
./main.py serve --mock

# Terminal 2: Vite dev server (hot-reload)
cd frontend && npm run dev
```

Frontend: **http://localhost:5173** (with hot-reload, proxies API to port 8080).

## Deploying to Raspberry Pi

### 1. Copy the project

```bash
rsync -avz --exclude .venv --exclude frontend/node_modules --exclude __pycache__ --exclude .git \
  ~/work/SocksTank/ rpi5:~/sockstank/
```

### 2. Install dependencies on RPi

```bash
ssh rpi5
sudo pip install fastapi uvicorn pydantic-settings websockets typer httpx paramiko --break-system-packages
```

`picamera2` is pre-installed in Raspberry Pi OS.

### 3. Run on RPi

```bash
cd ~/sockstank

# Basic run
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5

# With NcnnNativeDetector (12.8–16.0 FPS on RPi 5)
sudo -E python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 --ncnn-cpp --ncnn-threads 4

# In background (recommended)
sudo -E nohup python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 > /tmp/sockstank.log 2>&1 &
```

Open: **http://rpi5:8080**

Logs: `tail -f /tmp/sockstank.log`

`sudo -E` — `sudo` for camera and GPIO access, `-E` inherits PYTHONPATH.

## `main.py serve` Parameters

| Parameter | Default | Description |
|---|---|---|
| `--model` | `models/yolo11_best.pt` | Model path (see below) |
| `--conf` | `0.5` | Confidence threshold (0.0–1.0) |
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `8080` | HTTP/WebSocket port |
| `--mock` | `false` | Mock mode (no GPIO/camera) |
| `--ncnn-cpp` | `false` | NcnnNativeDetector (pip ncnn + OMP workaround) |
| `--ncnn-threads` | `2` | OMP threads for ncnn (1–4) |
| `--pcb-version` | `1` | Freenove PCB version (1 or 2) |

> **Which model to use with `--model`?**
> - **RPi** (production): `models/yolo11_best_ncnn_model` — NCNN [FP32](benchmarks.md#models), 15 FPS
> - **GPU server**: `models/yolo11_best.pt` — PyTorch, 314 FPS on CUDA
> - **macOS / dev**: `models/yolo11_best.pt` — PyTorch (or `--mock` without a model)
>
> The default `.pt` is intended for development. On RPi always specify the ncnn model explicitly.

All parameters can be set via environment variables with `SOCKSTANK_` prefix:

```bash
SOCKSTANK_MODEL_PATH="models/yolo11_best_ncnn_model" SOCKSTANK_MOCK=true python main.py serve
```

## Updating frontend on RPi

After changes to `frontend/`:

```bash
# On dev machine
cd frontend && npm run build

# Copy to RPi
rsync -avz frontend/dist/ rpi5:~/sockstank/frontend/dist/
```

Restart serve on RPi.

## GPU Inference (remote)

Details: [inference.md — Remote Inference](inference.md#remote-inference-gpu-server)

```bash
# On GPU server (blackops)
python -m server.inference_server --model models/yolo11_best.pt --port 8090  # .pt for GPU server
```

In web panel: **Inference → + Add GPU Server** → enter host, port, SSH key → **Save**.

---

[Back to README](README.md)
