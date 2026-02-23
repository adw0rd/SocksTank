# SocksTank Infrastructure

## Hosts

### rpi4 (robot)

- **Purpose**: robot tank (Raspberry Pi 4B)
- **OS**: Debian 12 (bookworm), aarch64
- **Connection**: WiFi

**Key packages**:
- ultralytics, torch, torchvision
- picamera2, opencv-python
- gpiozero, pigpio, rpi_hardware_pwm
- rpi-ws281x (LED), rpi-lgpio

**File structure**:
```
~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/
└── Code/Server/              # Main robot code
    ├── main.py                # Freenove server (TCP, client control)
    ├── car.py                 # Tank control (motors + servos + sensors)
    ├── motor.py               # Motors (gpiozero, GPIO 23/24, 5/6)
    ├── servo.py               # Servos (pigpio/gpiozero/hardware PWM, GPIO 7/8/25)
    ├── camera.py              # Camera class (preview, stream, video)
    ├── camera_detect.py       # Sock detection (our script)
    ├── camera_shot.py         # Burst capture (our script)
    ├── best.pt                # Trained model (copied to robot)
    ├── ultrasonic.py          # Ultrasonic sensor (GPIO 27/22, gpiozero)
    ├── infrared.py            # IR line sensors (GPIO 16/20|26/21)
    ├── led.py                 # LED control
    ├── server.py              # TCP server
    ├── tcp_server.py          # TCP server (low-level)
    ├── parameter.py           # Parameter manager (PCB/RPi version)
    └── params.json            # Configuration parameters
```

**Autostart**: `start.sh` launches `pigpiod` (GPIO daemon). Freenove server launch is commented out.

### GPU server (for training)

- **Purpose**: YOLO model training on GPU

**Working directory**:
```
~/work/
├── test20250807_yolov8/        # Main working directory
│   ├── data.yaml               # Dataset config v2 (961 images)
│   ├── train.py                # Training script (100 epochs)
│   ├── bench.py                # Model benchmark
│   ├── train/valid/test/       # Dataset (train/valid/test splits)
│   ├── yolov8n.pt              # Base model YOLOv8n
│   ├── yolo11n.pt              # Base model YOLOv11n
│   └── RESULT/                 # Best result (100 epochs, batch=16, GPU)
│       ├── weights/best.pt     # mAP50=0.995, mAP50-95=0.885
│       ├── results.csv         # Metrics per epoch
│       └── confusion_matrix.png, F1_curve.png, etc.
└── ultralytics/                # Ultralytics repo clone (for development)
```

## Networking

All devices are on the same local network. It's recommended to configure SSH aliases in `~/.ssh/config`:

```
Host rpi
    HostName 192.168.x.x
    User user

Host gpu-server
    HostName 192.168.x.x
    User user
    IdentityFile ~/.ssh/gpu-server
```

Actual IP addresses, usernames, and SSH keys are in `docs/credentials.md` (not committed).

## Robot hardware

### GPIO pinout
| Component | GPIO pins |
|---|---|
| Left motor | GPIO 23 (forward), GPIO 24 (backward) |
| Right motor | GPIO 5 (forward), GPIO 6 (backward) |
| Servo 0 (claw) | GPIO 7 |
| Servo 1 (lift) | GPIO 8 |
| Servo 2 | GPIO 25 |
| Ultrasonic trigger | GPIO 27 |
| Ultrasonic echo | GPIO 22 |
| IR sensor 1 | GPIO 16 |
| IR sensor 2 | GPIO 20 (PCB v1) / GPIO 26 (PCB v2) |
| IR sensor 3 | GPIO 21 |

### Operating modes (car.py)
- **mode_ultrasonic**: Obstacle avoidance (< 45 cm — reverse + turn, otherwise forward)
- **mode_infrared**: Line following (IR sensors) + object grab with claw (5-12 cm)
- **mode_clamp**: Claw control (up/down/stop) via servos

### Camera
- **Model**: ov5647 (OmniVision)
- **Library**: picamera2 + libcamera
- **Modes**: preview (1280x720), still (1920x1080), stream (400x300)
- **Transform**: vflip=True (camera is mounted upside down)
