# Настройка Raspberry Pi 5

Руководство по подготовке RPi 5 для работы робота-танка SocksTank.

## Характеристики

| Параметр | Значение |
|---|---|
| Модель | Raspberry Pi 5 Model B Rev 1.0 |
| SoC | BCM2712 (Cortex-A76) |
| CPU | 4 ядра, 1.5-2.4 GHz |
| RAM | 8 GB |
| ОС | Debian GNU/Linux 13 (trixie) **64-bit** |
| Ядро | 6.12.62+rpt-rpi-2712 aarch64 |
| Python | 3.13.5 (aarch64 **64-bit**) |
| Диск | microSD 117 GB |
| Revision | d04170 |
| IP | 192.168.0.158 (DHCP, hostname rpi5) |

## Отличия от RPi 4

| | RPi 4 Model B | RPi 5 Model B |
|---|---|---|
| CPU | Cortex-A72 1.8 GHz | Cortex-A76 2.4 GHz |
| RAM | 3.3 GB | 8 GB |
| ОС | Debian 12 bookworm 64-bit | Debian 13 trixie 64-bit |
| Python | 3.11.2 (aarch64) | 3.13.5 (aarch64) |
| PyTorch | ✅ 2.8.0+cpu | ✅ 2.10.0+cpu |
| onnxruntime | ✅ 1.24.2 | ✅ 1.24.2 |
| ncnn | ✅ | ✅ 1.0.20260114 |
| Питание | 5V/3A (USB-C) | **5V/5A** (USB PD) |
| pigpiod | Требуется | Не требуется |
| Камера | cam0 (15-pin CSI) | cam0 или cam1 (22-pin FPC) |

## Питание

**Критическая проблема**: RPi 5 потребляет значительно больше энергии, чем RPi 4.

Подробная документация: [../rpi5-power.md](../rpi5-power.md)

### Потребление (замеры PMIC)

| Режим | Питание | VDD_CORE (A) | EXT5V_V (V) |
|---|---|---|---|
| Idle | Литий (2x18650) | 1.63 | 4.86 |
| Компиляция | Литий (2x18650) | 2.61 | 4.73 |
| 4 ядра YOLO | Литий (2x18650) | ~3-4 | ~4.5-4.7 |
| Idle | Лаб. БП 5.1V | 1.46 | 5.08 |
| 4 ядра YOLO | Лаб. БП 5.1V | 1.75-2.0 | 5.06-5.08 |
| Idle | LM2596 (2x18650→5.1V) | 1.38 | 5.10 |
| 1 ядро YOLO | LM2596 (2x18650→5.1V) | 1.47-1.53 | 5.08-5.10 |
| 4 ядра YOLO | LM2596 (2x18650→5.1V) | — | ❌ крэш |
| Idle | XL6019E1 (2x18650→5.2V) | 1.41 | 5.23 |
| 4 ядра YOLO | XL6019E1 (2x18650→5.2V) | 1.48-1.58 | 5.22-5.23 |

### Источники питания (результаты тестов)

| Источник | EXT5V_V | Результат |
|---|---|---|
| Freenove Tank Board (2x18650 DC/DC) | ~4.8-4.9V | ❌ Undervoltage, крэши при 2+ ядрах |
| USB-C зарядка 3A | ~4.8V | ❌ Undervoltage |
| Xiaomi 120W USB-C | 4.73-4.86V | ❌ Undervoltage (нет PD) |
| LM2596 (2x18650→5.1V, GPIO) | 5.08-5.10V | ✅ Стабильно на 1-2 ядрах, крэш на 3+ |
| **XL6019E1** (2x18650→5.2V, GPIO) | 5.22-5.23V | ✅ Стабильно на 4 ядрах (плавный старт) |
| Лабораторный БП 5.1V/5A (GPIO) | 5.06-5.08V | ✅ Стабильно, throttled=0x0 |
| Официальный RPi 5 PSU (27W) | 5.0-5.1V | ✅ Рекомендуется |

### Решение: XL6019E1 DC-DC Buck-Boost Converter ✅

```
Батареи (2x18650, 7.4V) → XL6019E1 → 5.2V → RPi 5 GPIO (Pin 2 = 5V, Pin 6 = GND)
```

Настроить выход на **5.2V** (потенциометр, проверить мультиметром перед подключением).

#### Сравнение конвертеров

| Конвертер | Тип | Rated | Выход | 1 ядро | 2 ядра | 3 ядра | 4 ядра |
|---|---|---|---|---|---|---|---|
| LM2596 | buck | 3A | 5.1V | ✅ 7.7 FPS | ✅ 11.1 FPS | ❌ крэш | ❌ крэш |
| **XL6019E1** | buck-boost | **5A** | 5.2V | ✅ | ✅ | ✅ 11.1 FPS | ✅ **11.2 FPS** |

#### Результаты с XL6019E1

| Режим | EXT5V_V | VDD_CORE_A | Throttled | Результат |
|---|---|---|---|---|
| Idle | 5.23V | 1.41A | 0x0 | ✅ |
| NCNN 4 ядра (100 итераций) | 5.22-5.23V | 1.48-1.58A | 0x0 | ✅ **11.2 FPS** |

Проверка: `vcgencmd pmic_read_adc | grep EXT5V` → >5.0V.

> ⚠️ Требуется **плавный старт**: загрузка модели на 1 ядре → постепенный переход на 4.
> Прямой запуск на 4 ядрах вызывает крэш из-за пикового броска тока.

## Установка ОС

Использовать **Raspberry Pi OS Lite (64-bit)** через Raspberry Pi Imager:
- OS: Raspberry Pi OS (other) → Raspberry Pi OS Lite (64-bit)
- Hostname: rpi5
- Username: zeus
- Wi-Fi + SSH: включить

## Установленные пакеты

```
Python 3.13.5 (aarch64 64-bit)
torch 2.10.0+cpu
torchvision 0.25.0
ultralytics 8.4.16
cv2 4.13.0 (opencv-python-headless)
numpy 2.4.2
ncnn 1.0.20260114
onnxruntime 1.24.2
matplotlib 3.10.8
scipy 1.17.1
polars 1.38.1
```

## config.txt

Файл: `/boot/firmware/config.txt`

Необходимо добавить для SocksTank:

```ini
# PWM для сервоприводов Freenove Tank Board
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4

# Камера OV5647
dtoverlay=ov5647

# Питание через GPIO от Freenove Tank Board
usb_max_current_enable=1
psu_max_current=5000
```

### Отличие от RPi 4

- **pigpiod** не нужен на RPi 5 (используется встроенный GPIO)
- **Камера**: на RPi 5 разъёмы cam0/cam1 с 22-pin FPC (не 15-pin CSI как на RPi 4). Необходим переходник или кабель 22→15 pin.

## Бенчмарки

### Диск (microSD 117 GB)

| Операция | Скорость |
|---|---|
| Запись | **73.5 MB/s** |
| Чтение | **94.5 MB/s** |

### Инференс YOLO (64-bit ОС, active cooler)

#### XL6019E1 (2x18650, автономное питание, рекомендуется)

| Формат | Ядра | Mean (ms) | Min (ms) | Max (ms) | FPS | vs RPi 4 |
|---|---|---|---|---|---|---|
| **NCNN** | **4 (плавный старт)** | **89** | 87 | 97 | **11.2** | **10.2x** |
| NCNN | 3 (taskset) | 90 | 87 | 99 | **11.1** | **10.1x** |

Температура: 38→47°C. Throttled=0x0, EXT5V=5.22-5.23V.

#### LM2596 (2x18650, автономное питание)

| Формат | Ядра | Mean (ms) | Min (ms) | Max (ms) | FPS | vs RPi 4 |
|---|---|---|---|---|---|---|
| NCNN | 2 (taskset) | 90 | 86 | 106 | **11.1** | **10.1x** |
| NCNN | 1 (taskset) | 130 | 128 | 134 | **7.7** | **7.0x** |
| NCNN | 3+ | — | — | — | **крэш** | — |

Температура: 1 ядро 37→44°C, 2 ядра 53→60°C. Throttled=0x0, EXT5V=5.06-5.10V.

#### Лаб. БП 5.1V (для сравнения)

| Формат | Потоки | Mean (ms) | Min (ms) | Max (ms) | FPS | vs RPi 4 |
|---|---|---|---|---|---|---|
| NCNN (native) | 1 | 161 | 149 | 178 | **6.2** | **5.6x** |
| PyTorch | 4 | 288 | 285 | 298 | **3.5** | **3.2x** |
| ONNX | auto | 331 | 276 | 426 | **3.0** | **2.7x** |

> ⚠️ NCNN 4 потока медленнее 1 — баг в Python binding OpenMP. Используем 1 поток.

Температура: 68→75°C (active cooler), throttled=0x0.

### Старые замеры (32-bit ОС, литий)

| Формат | Ядра | Mean (ms) | FPS | vs RPi 4 |
|---|---|---|---|---|
| NCNN | 1 (taskset) | 323 | **3.1** | 1.3x |
| NCNN | 2+ | — | **крэш** | undervoltage |

## TODO

- [x] Переустановить 64-bit Raspberry Pi OS (Debian 13 trixie)
- [x] Установить torch, ultralytics, ncnn, onnxruntime
- [x] Замерить YOLO инференс на 4 ядрах (PyTorch 3.5 FPS, NCNN 14.6 FPS, ONNX 6.8 FPS)
- [x] Установить DC-DC конвертер (XL6019E1, 5.2V, 4 ядра стабильно, 11.2 FPS)
- [x] Замерить диск (microSD: запись 73.5 MB/s, чтение 94.5 MB/s)
- [ ] Настроить config.txt (PWM, камера, питание)
- [ ] Подключить камеру (кабель 22→15 pin заказан)
- [x] Установить SocksTank зависимости (fastapi, uvicorn, pydantic-settings)
- [x] Протестировать SocksTank serve --mock (3.4 FPS)
