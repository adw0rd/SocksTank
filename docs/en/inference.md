# Running on the Robot

Deploying the trained model to Raspberry Pi and running sock detection from the camera.

## Deploying to RPi

The entire project is copied to the robot via rsync:

```bash
rsync -avz --exclude .venv --exclude frontend/node_modules --exclude __pycache__ --exclude .git \
  ~/work/SocksTank/ rpi5:~/sockstank/
```

## Web control panel (recommended)

The main way to interact with the robot is through the web panel:

```bash
ssh rpi5
cd ~/sockstank
sudo -E nohup python main.py serve --model models/yolo11_best_ncnn_model --conf 0.5 > /tmp/sockstank.log 2>&1 &
```

Open in browser: `http://rpi5:8080`

The web panel includes: live video with YOLO detection, motor/servo/LED controls, telemetry (distance, IR sensors, CPU temperature).

`sudo -E` is required for camera and GPIO access (`-E` flag inherits user's PYTHONPATH).

## Running detection (legacy)

Record video with detection to a file:

```bash
ssh rpi5
cd ~/sockstank
sudo -E python main.py detect --model models/yolo11_best_ncnn_model --conf 0.5
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--model` | auto (`.pt` on dev/GPU, `ncnn` on RPi) | Model path (.pt for GPU, ncnn directory for RPi) |
| `--output` | `detect.mp4` | Output video file |
| `--conf` | `0.5` | Confidence threshold (0.0–1.0). Detections below the threshold are ignored |
| `--frames` | `300` | Maximum number of frames to record |
| `--width` | `1280` | Frame width (px) |
| `--height` | `720` | Frame height (px) |
| `--fps` | `3` | Camera frame rate |

### Example with ncnn model

If the model was exported to ncnn (see [training](training.md#model-export)):

```bash
sudo ./main.py detect --model models/yolo11_best_ncnn_model --conf 0.5  # NCNN for RPi
```

## Remote Inference (GPU Server)

Inference can be offloaded to a remote GPU server (e.g., blackops with RTX 4070 SUPER — 314.8 FPS vs 14.9 FPS on RPi 5). The robot sends frames over HTTP, the server returns detections.

### Inference Modes

In the web panel (`http://rpi5:8080`) under the **Inference** section there are three buttons:

| Mode | Description |
|---|---|
| **auto** | Use GPU server if online, otherwise fallback to local |
| **local** | Always use local inference (NCNN on RPi) |
| **remote** | Always use remote inference (error if server is unavailable) |

### Adding a GPU Server via UI

1. Open web panel → **Inference** section in the right column
2. Click **+ Add GPU Server**
3. Fill in the form:
   - **Host** — IP or hostname of the GPU server (e.g. `192.168.0.188`)
   - **Port** — inference server port (default `8090`)
   - **Username** — SSH user
   - **Auth** — `SSH Key` (path to key, default `~/.ssh/id_rsa`) or `Password`
4. Click **Test** to verify connection (shows GPU and model info)
5. Click **Save** to save

The server appears in the list with a status indicator:
- green — online
- orange — starting
- grey — offline

**Start** / **Stop** buttons launch and stop the inference server on the GPU host via SSH. The **×** button removes the server from the list.

Server configuration is saved in `gpu_servers.json` (in `.gitignore`).

### Running via CLI

```bash
# On the GPU server (blackops)
cd ~/work/SocksTank
python -m server.inference_server --port 8090  # auto-selects models/yolo11_best.pt on GPU/dev hosts
```

### API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/inference` | Inference status (mode, backend, ms) |
| PUT | `/api/inference/mode` | Switch mode (`auto`/`local`/`remote`) |
| GET | `/api/gpu/servers` | List GPU servers |
| POST | `/api/gpu/servers` | Add GPU server |
| DELETE | `/api/gpu/servers/{host}` | Remove GPU server |
| POST | `/api/gpu/servers/{host}/test` | Test connection |
| POST | `/api/gpu/servers/{host}/start` | Start inference server |
| POST | `/api/gpu/servers/{host}/stop` | Stop inference server |

## How detection works

1. The ov5647 camera captures frames via **picamera2**
2. Each frame is passed to the **YOLO** model for sock detection
3. Bounding boxes with class labels are drawn around detected socks
4. Processed frames are written to the `detect.mp4` video file

## Viewing results

The `detect.mp4` video file is saved in the current directory on the RPi. Copy it to your computer:

```bash
scp rpi5:~/sockstank/detect.mp4 .
```

Open with any video player (VLC, mpv, etc.).

## Integration with tank controls

The robot is controlled via `car.py` from the Freenove kit. It supports several modes:

- **mode_ultrasonic** — obstacle avoidance: ultrasonic sensor measures distance to objects. If < 45 cm — the robot reverses and turns
- **mode_infrared** — line following: IR sensors track a line on the floor. When an object is detected at 5–12 cm — it's grabbed with the claw
- **mode_clamp** — claw control: raise, lower, grab

The web panel (`main.py serve`) already combines detection with controls — you can drive the robot through the browser while seeing detection results in real time. Fully autonomous mode (find + drive + grab without human input) is the next development stage.

---

[Back to README](README.md)
