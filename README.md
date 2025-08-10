# SocksTank

На базе проекта [Freenove Tank Robot](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi) был выдуман проект `SocksTank`, его главная миссия это искать носки по квартире и собирать их в общую кучу, рядом со стиральной машинкой.

Таким образом, после сборки проекта `Freenove Tank` можно будет перейти к обучению модели и инференсу на Raspberry PI

* Подготовка Raspberry Pi
    * [Выбор между RPI4B и RPI5](docs/rpi.md)
    * [Запуск с носителя (sd card, usb flash, hat+ssd)](docs/rpi5.md#storage)
    * [Обновление до deb12u1-u3](docs/rpi5.md#upgrade)
    * [Установка зависимостей](docs/rpi5.md#deps)
    * [Настройка автозапуска](docs/rpi5.md#autostart)
    * [Работа с камерой](docs/rpi5.md#camera)
    * [Разгон процессора](docs/rpi5.md#boost)
    * [Охлаждение](docs/rpi5.md#cooling)
    * [Установка ultralytics](docs/rpi5.md#ultralytics)
* Подготовака датасета:
    * [Создание коллекции фотографий носков](docs/camera_shot.md)
    * [Использование Roboflow для аннотаций](docs/roboflow.md)
    * [Аугментация при помощи imgaug](docs/augmentation.md)
* Тренировка модели:
    * [YOLOv8](docs/train_yolo8.md)
    * [YOLOv11](docs/train_yolo11.md)
* Инференс:
    * [YOLOv8](docs/yolo8.md)
    * [YOLOv11](docs/yolo11.md)
    * [YOLOv11 + ncnn](docs/yolo11_ncnn.md)
