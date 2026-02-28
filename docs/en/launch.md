# Running the Project

🇷🇺 [Русская версия](../ru/launch.md)

How to build the frontend, run the backend, and deploy SocksTank on the robot.

## Development on macOS / Linux

### 1. Install dependencies

```bash
cd ~/work/SocksTank

# Python (via uv, recommended)
uv venv
source .venv/bin/activate
uv pip install -e .

# Or via pip
python3 -m venv .venv
source .venv/bin/activate
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

### Recommended: `main.py deploy`

The easiest deployment flow is the built-in deploy command:

```bash
./main.py deploy rpi5

# Equivalent explicit form
./main.py deploy --host rpi5
```

Use this path unless you are debugging deployment itself or intentionally doing a one-off manual install.

What it does:
- builds the frontend locally (unless `--skip-build`)
- syncs the project to `~/sockstank` via `rsync`
- installs runtime dependencies on RPi (`uv` if available, otherwise `pip`)
- restarts `sockstank.service` (via [systemd](#optional-install-the-systemd-unit-once)) if present, otherwise falls back to `nohup python3 main.py serve ...`
- waits for `/api/status` health check on port `8080`

Useful flags:
- `--skip-build`
- `--skip-install`
- `--skip-restart`
- `--dry-run`

Related operational commands:

```bash
# Restart the remote server only
./main.py restart rpi5

# Show the latest logs
./main.py logs rpi5 --lines 100
```

### Optional: install the systemd unit once

If you want `deploy` and `restart` to use `systemctl` instead of the fallback `nohup` path, install the bundled unit once:

```bash
./main.py install-service rpi5
```

Requirements:
- the SSH user must be allowed to run `sudo` non-interactively (`sudo -n`)[^passwordless-sudo]
- the project should already exist on the host (for example after `./main.py deploy rpi5`)

Under the hood, the command renders `scripts/sockstank.service` for the current SSH user, copies it to `/etc/systemd/system/`, runs `daemon-reload`, and enables the service. The web server then runs under that user instead of `root`.

After that, these commands become available:

```bash
./main.py restart rpi5
./main.py logs rpi5
```

[^passwordless-sudo]: Example on the RPi: run `sudo visudo -f /etc/sudoers.d/sockstank`, then add a rule like `zeus ALL=(ALL) NOPASSWD: /bin/cp, /bin/systemctl`. Replace `zeus` with your SSH user. This keeps passwordless sudo limited to the commands needed for service installation and restart.

### Manual deployment (fallback)

Use this only when you need to debug the deployment process step by step or when the built-in deploy command is temporarily unavailable.

#### 1. Copy the project

```bash
rsync -avz --exclude .venv --exclude frontend/node_modules --exclude __pycache__ --exclude .git \
  ~/work/SocksTank/ rpi5:~/sockstank/
```

#### 2. Install dependencies on RPi

```bash
ssh rpi5

# Preferred (if uv is installed)
uv pip install --system "typer>=0.9" ultralytics opencv-python-headless numpy "fastapi>=0.104" "uvicorn[standard]>=0.24" "pydantic-settings>=2.0" "websockets>=12.0" "httpx>=0.25" "paramiko>=3.0" "pyyaml>=6.0"

# Fallback (no uv)
python3 -m pip install "typer>=0.9" ultralytics opencv-python-headless numpy "fastapi>=0.104" "uvicorn[standard]>=0.24" "pydantic-settings>=2.0" "websockets>=12.0" "httpx>=0.25" "paramiko>=3.0" "pyyaml>=6.0" --break-system-packages
```

`picamera2` is pre-installed in Raspberry Pi OS.

#### 3. Run on RPi

```bash
cd ~/sockstank

# Basic run
sudo -E python3 main.py serve --model models/yolo11_best_ncnn_model --conf 0.5

# With NcnnNativeDetector (14.9–15.8 FPS on RPi 5)
sudo -E python3 main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 --ncnn-cpp --ncnn-threads 4

# In background (recommended)
sudo -E nohup python3 main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 > /tmp/sockstank.log 2>&1 &
```

Open: **http://rpi5:8080**

Logs: `tail -f /tmp/sockstank.log`

`sudo -E` — `sudo` for camera and GPIO access, `-E` inherits PYTHONPATH.

## `main.py serve` Parameters

| Parameter | Default | Description |
|---|---|---|
| `--model` | auto (`.pt` on dev/GPU, `ncnn` on RPi) | Model path (see below) |
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
> If `--model` is omitted, SocksTank chooses automatically: `.pt` on dev/GPU hosts, `models/yolo11_best_ncnn_model` on Raspberry Pi. You can still override it explicitly.

All parameters can be set via environment variables with `SOCKSTANK_` prefix:

```bash
SOCKSTANK_MODEL_PATH="models/yolo11_best_ncnn_model" SOCKSTANK_MOCK=true python3 main.py serve
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
python3 -m server.inference_server --port 8090  # use python3 on Linux; auto-selects models/yolo11_best.pt on GPU/dev hosts
```

In web panel: **Inference → + Add GPU Server** → enter host, port, SSH key → **Save**.

---

| ← Previous | README | Next → |
|---|---|---|
| [Model Training](training.md) | [Back to README](README.md) | [Running on the Robot](inference.md) |
