#!/usr/bin/env python3
"""SocksTank robot tank for sock detection with computer vision."""

import typer

app = typer.Typer(help="SocksTank robot for sock detection")


@app.command()
def train(
    model: str = typer.Option("yolov8n.pt", help="Base model"),
    data: str = typer.Option("data.yaml", help="Dataset config"),
    epochs: int = typer.Option(100, help="Number of epochs"),
    imgsz: int = typer.Option(640, help="Image size"),
    batch: int = typer.Option(16, help="Batch size"),
    device: str = typer.Option("0", help="Device (0=CUDA, mps, cpu)"),
):
    """Train a YOLOv8 model."""
    from ultralytics import YOLO

    yolo = YOLO(model)
    yolo.info()
    results = yolo.train(data=data, epochs=epochs, imgsz=imgsz, batch=batch, device=device)
    print(results)


@app.command()
def bench(
    model: str = typer.Option("yolov8n.pt", help="Model to benchmark"),
    data: str = typer.Option("data.yaml", help="Dataset config"),
    imgsz: int = typer.Option(640, help="Image size"),
    device: int = typer.Option(0, help="GPU device"),
):
    """Benchmark a model."""
    from ultralytics.utils.benchmarks import benchmark

    benchmark(model=model, data=data, imgsz=imgsz, half=False, device=device)


@app.command()
def detect(
    model: str | None = typer.Option(None, help="Path to the trained model (auto-selected if omitted)"),
    output: str = typer.Option("detect.mp4", help="Output video file"),
    conf: float = typer.Option(0.5, help="Confidence threshold"),
    frames: int = typer.Option(300, help="Maximum number of frames"),
    width: int = typer.Option(1280, help="Frame width"),
    height: int = typer.Option(720, help="Frame height"),
    fps: int = typer.Option(3, help="Camera FPS"),
):
    """Detect socks from a Raspberry Pi camera."""
    import sys
    import logging as log
    import time

    import cv2
    import numpy as np
    from ultralytics import YOLO
    from picamera2 import Picamera2
    from libcamera import Transform
    from server.config import resolve_model_path

    log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout)

    resolved_model = resolve_model_path(model, runtime_role="detect")

    log.info("Configuring ov5647 camera (Picamera2)")
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (width, height)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.transform = Transform(vflip=True)
    picam2.framerate = fps
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()

    log.info("Loading YOLO model: %s", resolved_model)
    yolo = YOLO(resolved_model)

    log.info("Configuring output file: %s", output)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output, fourcc, fps, (width, height))

    color = (255, 0, 0)
    t = time.time()
    try:
        for i in range(frames):
            log.info("Captured frame %d: %.3fs", i, time.time() - t)
            t = time.time()
            frame = picam2.capture_array()

            log.info("Running YOLO inference on frame")
            results = yolo(frame)
            annotated_frame = results[0]

            classes_names = annotated_frame.names
            classes = annotated_frame.boxes.cls.cpu().numpy()
            boxes = annotated_frame.boxes.xyxy.cpu().numpy().astype(np.int32)
            log.info("Objects: %r (%r)", classes_names, classes)

            for class_id, box, box_conf in zip(classes, boxes, annotated_frame.boxes.conf):
                if box_conf > conf:
                    class_name = classes_names[int(class_id)]
                    x1, y1, x2, y2 = box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            writer.write(frame)
    finally:
        log.info("Releasing resources")
        writer.release()
        cv2.destroyAllWindows()


@app.command()
def shot(
    count: int = typer.Option(200, help="Number of photos"),
    width: int = typer.Option(1920, help="Photo width"),
    height: int = typer.Option(1080, help="Photo height"),
    output_dir: str = typer.Option("images", help="Output directory for photos"),
    pause: int = typer.Option(2, help="Delay between photos (seconds)"),
    move_pause: int = typer.Option(10, help="Delay every 10 photos (seconds)"),
):
    """Capture a series of photos for dataset collection."""
    import os
    import time

    from picamera2 import Picamera2
    from libcamera import Transform

    os.makedirs(output_dir, exist_ok=True)

    cam = Picamera2()
    config = cam.create_still_configuration(main={"size": (width, height)}, transform=Transform(vflip=True))
    cam.configure(config)
    cam.start()

    try:
        for i in range(count):
            print(f"Iter {i}")
            if i % 10 == 0:
                print(f"Move to next sock... Sleep {move_pause} seconds")
                time.sleep(move_pause)
            else:
                time.sleep(pause)
            cam.capture_file(os.path.join(output_dir, f"image{i}.jpg"))
    finally:
        cam.stop()


@app.command()
def serve(
    model: str | None = typer.Option(None, help="Path to the YOLO model (auto-selected if omitted)"),
    conf: float = typer.Option(0.5, help="Confidence threshold"),
    host: str = typer.Option("0.0.0.0", help="Host"),
    port: int = typer.Option(8080, help="Port"),
    mock: bool = typer.Option(False, help="Mock mode (no GPIO/camera)"),
    pcb_version: int = typer.Option(1, help="Freenove PCB version (1 or 2)"),
    ncnn_cpp: bool = typer.Option(False, help="NcnnNativeDetector (pip ncnn + OMP workaround)"),
    ncnn_threads: int = typer.Option(2, help="OMP threads for ncnn (1-4)"),
):
    """Run the robot control web server."""
    import logging
    import uvicorn

    from server.config import resolve_model_path, settings

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    resolved_model = resolve_model_path(model, settings.model_path, runtime_role="serve", mock=mock)

    # Apply CLI parameters to settings
    settings.model_path = resolved_model
    settings.confidence = conf
    settings.host = host
    settings.port = port
    settings.mock = mock
    settings.pcb_version = pcb_version
    settings.ncnn_cpp = ncnn_cpp
    settings.ncnn_threads = ncnn_threads
    logging.getLogger(__name__).info("Using model: %s", resolved_model)

    from server.app import create_app

    uvicorn.run(create_app(), host=host, port=port)


@app.command()
def deploy(
    host_arg: str | None = typer.Argument(None, help="Raspberry Pi host (for example, rpi5)"),
    host: str | None = typer.Option(None, "--host", help="Raspberry Pi host (alternative to the positional argument)"),
    user: str | None = typer.Option(None, help="SSH user"),
    target_dir: str = typer.Option("~/sockstank", help="Project directory on the remote host"),
    port: int = typer.Option(8080, help="SocksTank port on the remote host"),
    service: str = typer.Option("sockstank", help="systemd unit name used for restart (if present)"),
    skip_build: bool = typer.Option(False, help="Skip frontend build before deploy"),
    skip_install: bool = typer.Option(False, help="Skip Python dependency updates on the host"),
    skip_restart: bool = typer.Option(False, help="Skip remote serve restart"),
    dry_run: bool = typer.Option(False, help="Show steps without executing them"),
):
    """Build, sync, and restart SocksTank on a Raspberry Pi."""
    from server.deploy import resolve_host, run_deploy

    resolved_host = resolve_host(host_arg, host)
    run_deploy(
        resolved_host,
        user=user,
        target_dir=target_dir,
        port=port,
        service=service,
        skip_build=skip_build,
        skip_install=skip_install,
        skip_restart=skip_restart,
        dry_run=dry_run,
    )


@app.command()
def restart(
    host_arg: str | None = typer.Argument(None, help="Raspberry Pi host (for example, rpi5)"),
    host: str | None = typer.Option(None, "--host", help="Raspberry Pi host (alternative to the positional argument)"),
    user: str | None = typer.Option(None, help="SSH user"),
    target_dir: str = typer.Option("~/sockstank", help="Project directory on the remote host"),
    port: int = typer.Option(8080, help="SocksTank port on the remote host"),
    service: str = typer.Option("sockstank", help="systemd unit name used for restart (if present)"),
    dry_run: bool = typer.Option(False, help="Show steps without executing them"),
):
    """Restart SocksTank on a Raspberry Pi and wait for a health check."""
    from server.deploy import resolve_host, run_restart

    resolved_host = resolve_host(host_arg, host)
    run_restart(
        resolved_host,
        user=user,
        target_dir=target_dir,
        port=port,
        service=service,
        dry_run=dry_run,
    )


@app.command()
def logs(
    host_arg: str | None = typer.Argument(None, help="Raspberry Pi host (for example, rpi5)"),
    host: str | None = typer.Option(None, "--host", help="Raspberry Pi host (alternative to the positional argument)"),
    user: str | None = typer.Option(None, help="SSH user"),
    service: str = typer.Option("sockstank", help="systemd unit name used for log reading (if present)"),
    lines: int = typer.Option(100, help="Number of trailing lines"),
    follow: bool = typer.Option(False, help="Follow logs (tail -f / journalctl -f)"),
    dry_run: bool = typer.Option(False, help="Show steps without executing them"),
):
    """Show SocksTank logs from a Raspberry Pi."""
    from server.deploy import resolve_host, run_logs

    resolved_host = resolve_host(host_arg, host)
    run_logs(
        resolved_host,
        user=user,
        service=service,
        lines=lines,
        follow=follow,
        dry_run=dry_run,
    )


@app.command("install-service")
def install_service(
    host_arg: str | None = typer.Argument(None, help="Raspberry Pi host (for example, rpi5)"),
    host: str | None = typer.Option(None, "--host", help="Raspberry Pi host (alternative to the positional argument)"),
    user: str | None = typer.Option(None, help="SSH user"),
    target_dir: str = typer.Option("~/sockstank", help="Project directory on the remote host"),
    service: str = typer.Option("sockstank", help="systemd unit name to install"),
    dry_run: bool = typer.Option(False, help="Show steps without executing them"),
):
    """Install the bundled systemd unit on a Raspberry Pi."""
    from server.deploy import resolve_host, run_install_service

    resolved_host = resolve_host(host_arg, host)
    run_install_service(
        resolved_host,
        user=user,
        target_dir=target_dir,
        service=service,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    app()
