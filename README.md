# SocksTank

<img align="left" width="200px" src="assets/SocksTank.jpeg">

На базе проекта [Freenove Tank Robot](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi) был выдуман проект `SocksTank`, его главная миссия - искать носки по всей квартире и аккуратно собирать их в одну большую кучу прямо возле стиральной машины.

Если вы уже успешно собрали проект `Freenove Tank`, тогда самое время перейти к следующему этапу - обучение собственной модели и последующий запуск её на платформе Raspberry Pi.

Я подготовил подробнейшее руководство, которое шаг за шагом проведет вас через весь процесс настройки и запуска модели на вашем устройстве.

---

* **Подготовка Raspberry Pi**
    * [Выбор между RPI4B и RPI5](docs/ru/rpi.md)
    * [Запуск с носителя (sd card, usb flash, hat+ssd)](docs/ru/rpi5.md#user-content-storage)
    * [Обновление Raspberry Pi OS (Debian) до deb12u1-u3](docs/ru/rpi5.md#user-content-upgrade)
    * [Установка зависимостей](docs/ru/rpi5.md#user-content-deps)
    * [Настройка автозапуска](docs/ru/rpi5.md#user-content-autostart)
    * [Работа с камерой](docs/ru/rpi5.md#user-content-camera)
    * [Разгон Raspberry Pi](docs/ru/rpi5.md#user-content-boost)
    * [Охлаждение](docs/ru/rpi5.md#user-content-cooling)
    * [Установка ultralytics, pytorch и т.д.](docs/ru/rpi5.md#user-content-ultralytics)
* **Подготовка датасета**
    * [Создание коллекции фотографий носков](docs/ru/dataset.md#user-content-camera)
    * [Использование Roboflow для аннотаций](docs/ru/dataset.md#user-content-roboflow)
    * [Аугментация при помощи imgaug](docs/ru/dataset.md#user-content-augmentation)
* **Тренировка модели**
    * [YOLOv8](docs/ru/yolo8.md#user-content-train)
    * [YOLOv11](docs/ru/yolo11.md#user-content-train)
* **Инференс**
    * [YOLOv8](docs/ru/yolo8.md#user-content-inference)
    * [YOLOv11](docs/ru/yolo11.md#user-content-inference)
    * [YOLOv11 + ncnn](docs/ru/yolo11.md#user-content-ncnn)
