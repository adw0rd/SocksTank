# Running on the Robot

Deploying the trained model to Raspberry Pi and running sock detection from the camera.

## Copying the model to RPi

After training, copy the best model (`best.pt`) to the robot:

```bash
scp best.pt rpi:~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/
```

Or, if training was done on the GPU server:

```bash
ssh gpu-server
scp ~/work/test20250807_yolov8/RESULT/weights/best.pt rpi:~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/
```

## Running detection

On the Raspberry Pi:

```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/
sudo ./main.py detect --model best.pt --conf 0.5
```

`sudo` is required for camera and GPIO access.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--model` | `best.pt` | Path to the trained model |
| `--output` | `detect.mp4` | Output video file |
| `--conf` | `0.5` | Confidence threshold (0.0–1.0). Detections below the threshold are ignored |
| `--frames` | `300` | Maximum number of frames to record |
| `--width` | `1280` | Frame width (px) |
| `--height` | `720` | Frame height (px) |
| `--fps` | `3` | Camera frame rate |

### Example with ncnn model

If the model was exported to ncnn (see [training](training.md#model-export)):

```bash
sudo ./main.py detect --model best_ncnn_model --conf 0.5
```

## How detection works

1. The ov5647 camera captures frames via **picamera2**
2. Each frame is passed to the **YOLO** model for sock detection
3. Bounding boxes with class labels are drawn around detected socks
4. Processed frames are written to the `detect.mp4` video file

## Viewing results

The `detect.mp4` video file is saved in the current directory on the RPi. Copy it to your computer:

```bash
scp rpi:~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/detect.mp4 .
```

Open with any video player (VLC, mpv, etc.).

## Integration with tank controls

The robot is controlled via `car.py` from the Freenove kit. It supports several modes:

- **mode_ultrasonic** — obstacle avoidance: ultrasonic sensor measures distance to objects. If < 45 cm — the robot reverses and turns
- **mode_infrared** — line following: IR sensors track a line on the floor. When an object is detected at 5–12 cm — it's grabbed with the claw
- **mode_clamp** — claw control: raise, lower, grab

For fully autonomous operation (find socks + drive to them + grab) the detection from `camera_detect.py` needs to be combined with controls from `car.py` — this is the next development stage.

---

[Back to README](README.md)
