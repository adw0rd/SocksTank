from ultralytics import YOLO
from picamera2 import Picamera2
from libcamera import Transform
import sys
import cv2
import time
import numpy as np
import logging as log

log.basicConfig(
    level=log.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


log.info("Настройка камеры ov5647 (Picamera2)")
fps = 3
width, height = 1280, 720
picam2 = Picamera2()
picam2.preview_configuration.main.size = (width, height)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.transform = Transform(vflip=True)
picam2.framerate = fps
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()

log.info("Загрузка модели YOLOv8")
model = YOLO("best.pt")

# log.info("Открытие исходного видеофайла")
# capture = cv2.VideoCapture(0)

# log.info("Чтение параметров видео")
# fps = int(capture.get(cv2.CAP_PROP_FPS))
# width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
# height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

log.info("Настройка выходного файла")
output_video_path = "detect.mp4"
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

color = (255, 0, 0)
i = 0
t = time.time()
while True:
    log.info("Захват кадра: %r", time.time() - t)
    t = time.time()
    # ret, frame = capture.read()
    frame = picam2.capture_array()
    # if not ret:
    #     break

    log.info("Обработка кадра с помощью модели YOLO")
    results = model(frame)
    annotated_frame = results[0]
    # cv2.imshow("Camera", annotated_frame.plot())

    log.info("Получение данных об объектах")
    classes_names = annotated_frame.names
    classes = annotated_frame.boxes.cls.cpu().numpy()
    boxes = annotated_frame.boxes.xyxy.cpu().numpy().astype(np.int32)
    log.info("Рисование рамок и подписей на кадре: %r (%r)", classes_names, classes)
    for class_id, box, conf in zip(classes, boxes, annotated_frame.boxes.conf):
        if conf > 0.5:
            class_name = classes_names[int(class_id)]
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                class_name,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

    log.info("Запись обработанного кадра в выходной файл")
    writer.write(frame)
    if i > 300:
        break
    i += 1

log.info("Освобождение ресурсов и закрытие окон")
# capture.release()
writer.release()
cv2.destroyAllWindows()
