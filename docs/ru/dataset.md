## Camera

Запускаем камеру

```bash
sudo python camera_shot.py
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
pip install ultralytics
```
