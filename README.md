# SocksTank

## Camera

Запускаем камеру

```bash
sudo python camera.py
```

Раз в 10 секунд будет делать 10 снимков с паузой в 2 секунды

## Roboflow: Upload Data

Загружаются фотографии

<img width="850" height="516" alt="image" src="https://github.com/user-attachments/assets/38e06e59-6363-4463-808c-71c0722c2f65" />

## Roboflow: Annotate

Размечаются данные

<img width="1410" height="640" alt="image" src="https://github.com/user-attachments/assets/97fa19b5-90dc-43c5-ba80-8735d1ed30c9" />

## Roboflow: Versions

Create New Version (+Augmentation)
  
<img width="1406" height="439" alt="image" src="https://github.com/user-attachments/assets/02dc7c54-c0b4-49e0-9636-459974bde62a" />

После чего скачиваем датасет (кнопка "Download Dataset") в формате "Yolo v8"

## Установка Yolo, PyTorch, Nvidia CUDA

```
nvidia-smi
ncc

python3 -m venv venv

```

## YOLOv8

В Roboflow можно при скачивании указать формат, выбираем YOLOv8

<img width="813" height="438" alt="image" src="https://github.com/user-attachments/assets/694745a3-ed5e-4e44-96f5-8b866a6f5837" />

```bash
mkdir test && cd test
curl -L "https://app.roboflow.com/ds/LKb6HuPfNp?key=588uQVlgla" > roboflow.zip; unzip roboflow.zip; rm roboflow.zip
```

Обучение на Apple Silicon (m3 pro):

```bash
yolo task=detect mode=train model=yolov8n.pt imgsz=640 data=data.yaml epochs=10 batch=8 name=/path/to/result device=mps
```


Либо через ultralytics:

```py
from ultralytics import YOLO
model = YOLO("yolo11n.pt")
results = model.train(data="coco8.yaml", epochs=100, imgsz=640, device="mps")
```
