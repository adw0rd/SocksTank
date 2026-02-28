# SocksTank

<img align="left" width="200px" src="assets/SocksTank.jpeg">

**SocksTank** is a Raspberry Pi-based robot tank that hunts for socks around the apartment using computer vision (YOLO) and picks them up with a claw. Includes a web control panel with live video, motor/servo controls, and real-time telemetry.

Built on top of [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi). If you've already assembled the Freenove Tank, it's time for the next step — train your own model and run it on a Raspberry Pi.

<br clear="left">

## Documentation

* [**Running the project**](docs/en/launch.md) — build frontend, run backend, deploy to RPi
* **Raspberry Pi setup**
    * [RPi 5 setup (recommended)](docs/en/rpi5.md)
    * [RPi 4 setup (legacy)](docs/en/rpi4.md)
    * [RPi 5 power supply](docs/en/rpi5-power.md)
* **Dataset preparation**
    * [Capturing photos](docs/en/dataset.md#capturing-photos)
    * [Uploading to Roboflow & annotation](docs/en/dataset.md#uploading-to-roboflow)
    * [Augmentation](docs/en/dataset.md#augmentation)
    * [Exporting the dataset](docs/en/dataset.md#exporting-the-dataset)
* **Model training**
    * [Training (GPU, Apple Silicon, CPU)](docs/en/training.md#training)
    * [Evaluating results](docs/en/training.md#evaluating-results)
    * [Model export (ncnn for RPi)](docs/en/training.md#model-export)
* **Inference & Web Panel**
    * [Web control panel](docs/en/inference.md#web-control-panel-recommended)
    * [Deploying to RPi](docs/en/inference.md#deploying-to-rpi)
    * [Remote GPU inference](docs/en/inference.md#remote-inference-gpu-server)
    * [Integration with tank controls](docs/en/inference.md#integration-with-tank-controls)
* **Benchmarks**
    * [Inference benchmarks](docs/en/benchmarks.md)
    * [Disk benchmarks](docs/en/disk-benchmarks.md)
* [**Infrastructure**](docs/en/infrastructure.md)

---

**SocksTank** — робот-танк на базе Raspberry Pi, который ищет носки по квартире с помощью компьютерного зрения (YOLO) и собирает их клешнёй. Включает веб-панель управления с живым видео, управлением моторами/сервоприводами и телеметрией в реальном времени.

Построен поверх [Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi). Если вы уже собрали Freenove Tank, самое время перейти к следующему этапу — обучить собственную модель и запустить её на Raspberry Pi.

## Документация

* [**Запуск проекта**](docs/ru/launch.md) — сборка фронтенда, запуск бэкенда, деплой на RPi
* **Настройка Raspberry Pi**
    * [Настройка RPi 5 (рекомендуется)](docs/ru/rpi5.md)
    * [Настройка RPi 4 (legacy)](docs/ru/rpi4.md)
    * [Питание RPi 5](docs/ru/rpi5-power.md)
* **Подготовка датасета**
    * [Съёмка фотографий](docs/ru/dataset.md#съёмка-фотографий)
    * [Загрузка в Roboflow и аннотирование](docs/ru/dataset.md#загрузка-в-roboflow)
    * [Аугментация](docs/ru/dataset.md#аугментация)
    * [Экспорт датасета](docs/ru/dataset.md#экспорт-датасета)
* **Тренировка модели**
    * [Тренировка (GPU, Apple Silicon, CPU)](docs/ru/training.md#тренировка)
    * [Оценка результатов](docs/ru/training.md#оценка-результатов)
    * [Экспорт модели (ncnn для RPi)](docs/ru/training.md#экспорт-модели)
* **Инференс и веб-панель**
    * [Веб-панель управления](docs/ru/inference.md#веб-панель-управления-рекомендуемый-способ)
    * [Деплой на RPi](docs/ru/inference.md#деплой-на-rpi)
    * [Удалённый GPU-инференс](docs/ru/inference.md#удалённый-инференс-gpu-сервер)
    * [Интеграция с управлением танком](docs/ru/inference.md#интеграция-с-управлением-танком)
* **Бенчмарки**
    * [Бенчмарки инференса](docs/ru/benchmarks.md)
    * [Бенчмарки диска](docs/ru/disk-benchmarks.md)
* [**Инфраструктура**](docs/ru/infrastructure.md)
