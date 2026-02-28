# Инфраструктура SocksTank

## Хосты

### rpi5 (основной)

- **Назначение**: робот-танк (Raspberry Pi 5 Model B)
- **OS**: Debian 13 (trixie) 64-bit, aarch64
- **CPU**: BCM2712 (Cortex-A76), 4 ядра, 2.4 GHz
- **RAM**: 8 GB
- **Python**: 3.13.5
- **Подключение**: WiFi (DHCP, hostname `rpi5`)
- **Питание**: XL6019E1 buck-boost (2x18650 → 5.2V → GPIO)

**Установленные пакеты** (ключевые):
- ultralytics, torch 2.10.0+cpu, torchvision
- ncnn 1.0.20260114, onnxruntime 1.24.2
- picamera2, opencv-python-headless
- gpiozero, rpi_hardware_pwm, rpi-ws281x

**Автозапуск**: pigpiod не требуется на RPi 5 (встроенный GPIO).

Подробная настройка: [rpi5.md](rpi5.md)

### rpi4 (legacy)

- **Назначение**: робот-танк (Raspberry Pi 4B)
- **OS**: Debian 12 (bookworm), aarch64
- **Подключение**: WiFi

**Установленные пакеты** (ключевые):
- ultralytics, torch, torchvision
- picamera2, opencv-python
- gpiozero, pigpio, rpi_hardware_pwm
- rpi-ws281x (LED), rpi-lgpio

**Файловая структура**:
```
~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/
└── Code/Server/              # Основной код робота
    ├── main.py                # Freenove сервер (TCP, управление с клиента)
    ├── car.py                 # Управление танком (моторы + сервоприводы + сенсоры)
    ├── motor.py               # Моторы (gpiozero, GPIO 23/24, 5/6)
    ├── servo.py               # Сервоприводы (pigpio/gpiozero/hardware PWM, GPIO 7/8/25)
    ├── camera.py              # Класс Camera (preview, stream, video)
    ├── camera_detect.py       # Детекция носков (перенесён в legacy/)
    ├── camera_shot.py         # Серийная съёмка (перенесён в legacy/)
    ├── best.pt                # Обученная модель (скопирована на робот)
    ├── ultrasonic.py          # Ультразвуковой сенсор (GPIO 27/22, gpiozero)
    ├── infrared.py            # ИК-сенсоры линии (GPIO 16/20|26/21)
    ├── led.py                 # Управление LED
    ├── server.py              # TCP-сервер
    ├── tcp_server.py          # TCP-сервер (low-level)
    ├── parameter.py           # Менеджер параметров (PCB/RPi версия)
    └── params.json            # Параметры конфигурации
```

**Автозапуск**: `start.sh` запускает `pigpiod` (демон для GPIO). Запуск сервера Freenove закомментирован.

### blackops (GPU-сервер для тренировки)

- **Назначение**: тренировка моделей YOLO на GPU
- **GPU**: NVIDIA RTX 4070 SUPER

**Рабочая директория**:
```
~/work/
├── test20250807_yolov8/        # Основная рабочая директория
│   ├── venv/                   # Python venv (ultralytics + torch)
│   ├── data.yaml               # Конфиг датасета v2 (961 изображение)
│   ├── train.py                # Скрипт тренировки (100 эпох)
│   ├── bench.py                # Бенчмарк модели
│   ├── train/valid/test/       # Датасет (train/valid/test splits)
│   ├── yolov8n.pt              # Базовая модель YOLOv8n
│   ├── yolo11n.pt              # Базовая модель YOLOv11n
│   └── runs/detect/            # Результаты тренировок
│       ├── train/weights/best.pt   # YOLOv8n: mAP50=0.995, mAP50-95=0.885
│       └── train2/weights/best.pt  # YOLOv11n: mAP50=0.995, mAP50-95=0.96
└── ultralytics/                # Клон репо ultralytics (для разработки)
```

## Сетевое взаимодействие

Все устройства в одной локальной сети. Для удобства рекомендуется настроить SSH-алиасы в `~/.ssh/config`:

```
Host rpi5
    HostName rpi5
    User user

Host rpi4
    HostName 192.168.x.x
    User user

Host blackops
    HostName 192.168.x.x
    User user
    IdentityFile ~/.ssh/blackops
```

Реальные IP-адреса, имена пользователей и SSH-ключи — в `docs/credentials.md` (не коммитится).

## Аппаратная часть робота

### GPIO распиновка
| Компонент | GPIO пины | Углы |
|---|---|---|
| Левый мотор | GPIO 23 (forward), GPIO 24 (backward) |
| Правый мотор | GPIO 5 (forward), GPIO 6 (backward) |
| Сервопривод 0 (клешня) | GPIO 7 | 90° закрыта, 150° открыта |
| Сервопривод 1 (подъём) | GPIO 8 | 150° вверх, 90° вниз |
| Сервопривод 2 | GPIO 25 |
| Ультразвук trigger | GPIO 27 |
| Ультразвук echo | GPIO 22 |
| ИК-сенсор 1 | GPIO 16 |
| ИК-сенсор 2 | GPIO 20 (PCB v1) / GPIO 26 (PCB v2) |
| ИК-сенсор 3 | GPIO 21 |

### Режимы работы (car.py)
- **mode_ultrasonic**: Обход препятствий (< 45 см — назад + поворот, иначе вперёд)
- **mode_infrared**: Следование по линии (ИК-сенсоры) + захват объекта клешнёй (5-12 см)
- **mode_clamp**: Управление клешнёй (up/down/stop) через сервоприводы

### Камера
- **Модель**: ov5647 (OmniVision)
- **Библиотека**: picamera2 + libcamera
- **Режимы**: preview (1280x720), still (1920x1080), stream (400x300)
- **Трансформация**: vflip=True (камера перевёрнута)
