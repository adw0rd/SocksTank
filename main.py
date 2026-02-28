#!/usr/bin/env python3
"""SocksTank — робот-танк для поиска носков с компьютерным зрением."""

import typer

app = typer.Typer(help="SocksTank — робот для поиска носков")


@app.command()
def train(
    model: str = typer.Option("yolov8n.pt", help="Базовая модель"),
    data: str = typer.Option("data.yaml", help="Конфиг датасета"),
    epochs: int = typer.Option(100, help="Количество эпох"),
    imgsz: int = typer.Option(640, help="Размер изображения"),
    batch: int = typer.Option(16, help="Размер батча"),
    device: str = typer.Option("0", help="Устройство (0=CUDA, mps, cpu)"),
):
    """Тренировка модели YOLOv8."""
    from ultralytics import YOLO

    yolo = YOLO(model)
    yolo.info()
    results = yolo.train(data=data, epochs=epochs, imgsz=imgsz, batch=batch, device=device)
    print(results)


@app.command()
def bench(
    model: str = typer.Option("yolov8n.pt", help="Модель для бенчмарка"),
    data: str = typer.Option("data.yaml", help="Конфиг датасета"),
    imgsz: int = typer.Option(640, help="Размер изображения"),
    device: int = typer.Option(0, help="GPU устройство"),
):
    """Бенчмарк модели."""
    from ultralytics.utils.benchmarks import benchmark

    benchmark(model=model, data=data, imgsz=imgsz, half=False, device=device)


@app.command()
def detect(
    model: str | None = typer.Option(None, help="Путь к обученной модели (если не указан — выбирается автоматически)"),
    output: str = typer.Option("detect.mp4", help="Выходной видеофайл"),
    conf: float = typer.Option(0.5, help="Порог уверенности"),
    frames: int = typer.Option(300, help="Макс. количество кадров"),
    width: int = typer.Option(1280, help="Ширина кадра"),
    height: int = typer.Option(720, help="Высота кадра"),
    fps: int = typer.Option(3, help="FPS камеры"),
):
    """Детекция носков с камеры Raspberry Pi."""
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

    log.info("Настройка камеры ov5647 (Picamera2)")
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (width, height)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.transform = Transform(vflip=True)
    picam2.framerate = fps
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()

    log.info("Загрузка модели YOLO: %s", resolved_model)
    yolo = YOLO(resolved_model)

    log.info("Настройка выходного файла: %s", output)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output, fourcc, fps, (width, height))

    color = (255, 0, 0)
    t = time.time()
    try:
        for i in range(frames):
            log.info("Захват кадра %d: %.3fs", i, time.time() - t)
            t = time.time()
            frame = picam2.capture_array()

            log.info("Обработка кадра с помощью модели YOLO")
            results = yolo(frame)
            annotated_frame = results[0]

            classes_names = annotated_frame.names
            classes = annotated_frame.boxes.cls.cpu().numpy()
            boxes = annotated_frame.boxes.xyxy.cpu().numpy().astype(np.int32)
            log.info("Объекты: %r (%r)", classes_names, classes)

            for class_id, box, box_conf in zip(classes, boxes, annotated_frame.boxes.conf):
                if box_conf > conf:
                    class_name = classes_names[int(class_id)]
                    x1, y1, x2, y2 = box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, class_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            writer.write(frame)
    finally:
        log.info("Освобождение ресурсов")
        writer.release()
        cv2.destroyAllWindows()


@app.command()
def shot(
    count: int = typer.Option(200, help="Количество снимков"),
    width: int = typer.Option(1920, help="Ширина снимка"),
    height: int = typer.Option(1080, help="Высота снимка"),
    output_dir: str = typer.Option("images", help="Каталог для снимков"),
    pause: int = typer.Option(2, help="Пауза между снимками (сек)"),
    move_pause: int = typer.Option(10, help="Пауза каждые 10 снимков (сек)"),
):
    """Серийная съёмка фото для сбора датасета."""
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
    model: str | None = typer.Option(None, help="Путь к модели YOLO (если не указан — выбирается автоматически)"),
    conf: float = typer.Option(0.5, help="Порог уверенности"),
    host: str = typer.Option("0.0.0.0", help="Хост"),
    port: int = typer.Option(8080, help="Порт"),
    mock: bool = typer.Option(False, help="Mock-режим (без GPIO/камеры)"),
    pcb_version: int = typer.Option(1, help="PCB версия платы Freenove (1 или 2)"),
    ncnn_cpp: bool = typer.Option(False, help="NcnnNativeDetector (pip ncnn + OMP workaround)"),
    ncnn_threads: int = typer.Option(2, help="OMP потоков для ncnn (1–4)"),
):
    """Веб-сервер управления роботом."""
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
    host_arg: str | None = typer.Argument(None, help="Хост Raspberry Pi (например, rpi5)"),
    host: str | None = typer.Option(None, "--host", help="Хост Raspberry Pi (альтернатива позиционному аргументу)"),
    user: str | None = typer.Option(None, help="SSH пользователь"),
    target_dir: str = typer.Option("~/sockstank", help="Каталог проекта на удалённом хосте"),
    port: int = typer.Option(8080, help="Порт SocksTank на удалённом хосте"),
    service: str = typer.Option("sockstank", help="Имя systemd unit для restart (если есть)"),
    skip_build: bool = typer.Option(False, help="Не собирать frontend перед deploy"),
    skip_install: bool = typer.Option(False, help="Не обновлять Python-зависимости на хосте"),
    skip_restart: bool = typer.Option(False, help="Не перезапускать удалённый serve"),
    dry_run: bool = typer.Option(False, help="Только показать шаги без выполнения"),
):
    """Собрать, синхронизировать и перезапустить SocksTank на Raspberry Pi."""
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


if __name__ == "__main__":
    app()
