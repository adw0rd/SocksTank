#!/usr/bin/env python3
"""SocksTank robot tank for sock detection with computer vision."""

import code
import time

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

    from server.config import load_persisted_model_path, resolve_model_path, settings

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    configured_model = settings.model_path or load_persisted_model_path()
    resolved_model = resolve_model_path(model, configured_model, runtime_role="serve", mock=mock)

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


@app.command("motor-test")
def motor_test(
    channel: str = typer.Argument(..., help="One of: lf, lb, rf, rb"),
    speed: int = typer.Option(1200, min=200, max=4095, help="Motor duty to apply"),
    seconds: float = typer.Option(1.0, min=0.1, max=5.0, help="How long to drive before auto-stop"),
):
    """Drive a single motor direction for a short diagnostic test."""
    from server.config import settings
    from server.freenove_bridge import load_hardware_modules

    normalized = channel.strip().lower()
    profiles = {
        "lf": (speed, 0),
        "lb": (-speed, 0),
        "rf": (0, speed),
        "rb": (0, -speed),
    }
    if normalized not in profiles:
        raise typer.BadParameter("channel must be one of: lf, lb, rf, rb")

    settings.mock = False
    motor = load_hardware_modules()["motor"]()
    left, right = profiles[normalized]
    typer.echo(f"Driving {normalized} for {seconds:.1f}s at duty {speed}")
    try:
        motor.setMotorModel(left, right)
        time.sleep(seconds)
    finally:
        motor.setMotorModel(0, 0)
        motor.close()
        typer.echo("Motors stopped")


@app.command("motor-shell")
def motor_shell():
    """Open an interactive shell with motor helpers for raw drivetrain tests."""
    from server.config import settings
    from server.freenove_bridge import load_hardware_modules

    settings.mock = False
    motor = load_hardware_modules()["motor"]()

    def set_motor(left: int, right: int):
        motor.setMotorModel(left, right)

    def stop():
        motor.setMotorModel(0, 0)

    def pulse(left: int, right: int, seconds: float = 1.0):
        motor.setMotorModel(left, right)
        time.sleep(seconds)
        motor.setMotorModel(0, 0)

    def lf(speed: int = 1200, seconds: float = 1.0):
        pulse(speed, 0, seconds)

    def lb(speed: int = 1200, seconds: float = 1.0):
        pulse(-speed, 0, seconds)

    def rf(speed: int = 1200, seconds: float = 1.0):
        pulse(0, speed, seconds)

    def rb(speed: int = 1200, seconds: float = 1.0):
        pulse(0, -speed, seconds)

    banner = (
        "SocksTank motor shell\n"
        "Helpers:\n"
        "  set_motor(left, right)\n"
        "  stop()\n"
        "  pulse(left, right, seconds=1.0)\n"
        "  lf(speed=1200, seconds=1.0)\n"
        "  lb(speed=1200, seconds=1.0)\n"
        "  rf(speed=1200, seconds=1.0)\n"
        "  rb(speed=1200, seconds=1.0)\n"
        "Examples:\n"
        "  lf()\n"
        "  set_motor(1500, -1500)\n"
        "  stop()\n"
        "Press Ctrl-D to exit; motors are stopped automatically.\n"
    )

    namespace = {
        "motor": motor,
        "set_motor": set_motor,
        "stop": stop,
        "pulse": pulse,
        "lf": lf,
        "lb": lb,
        "rf": rf,
        "rb": rb,
    }

    try:
        try:
            from IPython import embed

            embed(banner1=banner, user_ns=namespace)
        except ImportError:
            typer.echo("IPython is not installed, falling back to the standard Python shell.")
            code.interact(banner=banner, local=namespace)
    finally:
        motor.setMotorModel(0, 0)
        motor.close()
        typer.echo("Motors stopped")


@app.command()
def shell():
    """Open an interactive project shell."""
    try:
        from IPython import start_ipython
    except ImportError as exc:
        raise typer.Exit("IPython is not installed. Install it to use `main.py shell`.") from exc

    start_ipython(argv=[])


if __name__ == "__main__":
    app()
