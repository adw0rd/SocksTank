# SocksTank

На базе проекта [Freenove Tank Robot](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi) был выдуман проект `SocksTank`, его главная миссия - искать носки по квартире и собирать их в общую кучу, рядом со стиральной машинкой.

![telegram-cloud-photo-size-2-5244546013975413165-x](https://github.com/user-attachments/assets/b198d248-06c3-4d03-9301-35bda57b878f)

Если вы уже собрали проект [Freenove Tank](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi), то можно приступить к обучению модели и инференсу на Raspberry Pi. Для этого я пошагово разложил своё скромное руководство:

* **Подготовка Raspberry Pi**
    * [Выбор между RPI4B и RPI5](docs/rpi.md)
    * [Запуск с носителя (sd card, usb flash, hat+ssd)](docs/rpi5.md#storage)
    * [Обновление Raspberry Pi OS (Debian) до deb12u1-u3](docs/rpi5.md#upgrade)
    * [Установка зависимостей](docs/rpi5.md#deps)
    * [Настройка автозапуска](docs/rpi5.md#autostart)
    * [Работа с камерой](docs/rpi5.md#camera)
    * [Разгон Raspberry Pi](docs/rpi5.md#boost)
    * [Охлаждение](docs/rpi5.md#cooling)
    * [Установка ultralytics, pytorch и т.д.](docs/rpi5.md#ultralytics)
* **Подготовака датасета**
    * [Создание коллекции фотографий носков](docs/dataset.md#camera)
    * [Использование Roboflow для аннотаций](docs/dataset.md#roboflow)
    * [Аугментация при помощи imgaug](docs/dataset.md#augmentation)
* **Тренировка модели**
    * [YOLOv8](docs/yolo8.md#train)
    * [YOLOv11](docs/yolo11.md#train)
* **Инференс**
    * [YOLOv8](docs/yolo8.md#inference)
    * [YOLOv11](docs/yolo11.md#inference)
    * [YOLOv11 + ncnn](docs/yolo11.md#ncnn)
