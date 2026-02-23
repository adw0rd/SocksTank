# SocksTank

<img align="left" width="200px" src="assets/SocksTank.jpeg">

**SocksTank** is a Raspberry Pi 4B-based robot tank that hunts for socks around the apartment using computer vision (YOLOv8) and picks them up with a claw.

Built on top of [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi). If you've already assembled the Freenove Tank, it's time for the next step — train your own model and run it on a Raspberry Pi.

<br clear="left">

* **Raspberry Pi setup**
    * [Hardware requirements & OS installation](docs/en/rpi.md)
    * [Installing dependencies](docs/en/rpi.md#installing-dependencies)
    * [Camera setup](docs/en/rpi.md#camera-setup)
    * [Autostart & static IP](docs/en/rpi.md#autostart-setup)
    * [Overclocking](docs/en/rpi.md#overclocking-optional)
    * [Installing ultralytics (YOLO)](docs/en/rpi.md#installing-ultralytics-yolo)
* **Dataset preparation**
    * [Capturing photos](docs/en/dataset.md#capturing-photos)
    * [Uploading to Roboflow & annotation](docs/en/dataset.md#uploading-to-roboflow)
    * [Augmentation](docs/en/dataset.md#augmentation)
    * [Exporting the dataset](docs/en/dataset.md#exporting-the-dataset)
* **Model training**
    * [Training (GPU, Apple Silicon, CPU)](docs/en/training.md#training)
    * [Evaluating results](docs/en/training.md#evaluating-results)
    * [Model export (ncnn for RPi)](docs/en/training.md#model-export)
* **Inference**
    * [Deploying to RPi & running detection](docs/en/inference.md)
    * [Integration with tank controls](docs/en/inference.md#integration-with-tank-controls)
* [**Infrastructure**](docs/en/infrastructure.md)

---

**SocksTank** — робот-танк на базе Raspberry Pi 4B, который ищет носки по квартире с помощью компьютерного зрения (YOLOv8) и собирает их клешнёй.

Построен поверх [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi). Если вы уже собрали Freenove Tank, самое время перейти к следующему этапу — обучить собственную модель и запустить её на Raspberry Pi.

* **Настройка Raspberry Pi**
    * [Требования к железу и установка ОС](docs/ru/rpi.md)
    * [Установка зависимостей](docs/ru/rpi.md#установка-зависимостей)
    * [Настройка камеры](docs/ru/rpi.md#настройка-камеры)
    * [Автозапуск и статический IP](docs/ru/rpi.md#настройка-автозапуска)
    * [Разгон](docs/ru/rpi.md#разгон-опционально)
    * [Установка ultralytics (YOLO)](docs/ru/rpi.md#установка-ultralytics-yolo)
* **Подготовка датасета**
    * [Съёмка фотографий](docs/ru/dataset.md#съёмка-фотографий)
    * [Загрузка в Roboflow и аннотирование](docs/ru/dataset.md#загрузка-в-roboflow)
    * [Аугментация](docs/ru/dataset.md#аугментация)
    * [Экспорт датасета](docs/ru/dataset.md#экспорт-датасета)
* **Тренировка модели**
    * [Тренировка (GPU, Apple Silicon, CPU)](docs/ru/training.md#тренировка)
    * [Оценка результатов](docs/ru/training.md#оценка-результатов)
    * [Экспорт модели (ncnn для RPi)](docs/ru/training.md#экспорт-модели)
* **Инференс**
    * [Деплой на RPi и запуск детекции](docs/ru/inference.md)
    * [Интеграция с управлением танком](docs/ru/inference.md#интеграция-с-управлением-танком)
* [**Инфраструктура**](docs/ru/infrastructure.md)

## License

MIT
