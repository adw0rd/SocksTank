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

### Источники питания (результаты тестов)

| Источник | EXT5V_V | Результат |
|---|---|---|
| Freenove Tank Board (2x18650 DC/DC) | ~4.8-4.9V | ❌ Undervoltage, крэши при 2+ ядрах |
| USB-C зарядка 3A | ~4.8V | ❌ Undervoltage |
| Xiaomi 120W USB-C | 4.73-4.86V | ❌ Undervoltage (нет PD) |
| Лабораторный БП 5.1V/5A (GPIO) | 5.06-5.08V | ✅ Стабильно, throttled=0x0 |
| Официальный RPi 5 PSU (27W) | 5.0-5.1V | ✅ Рекомендуется |

### Решение: LM2596 DC-DC Buck Converter

```
Батареи (2x18650, 7.4V) → LM2596 → 5.1V/3A → RPi 5 GPIO (5V + GND)
```

Настроить выход на **5.1V**. Проверить: `vcgencmd pmic_read_adc | grep EXT5V` → >5.0V.

### Workaround (без LM2596)

```bash
# Ограничить нагрузку: 1 ядро, низкий приоритет
taskset -c 0 nice -n 19 <command>
```

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

### Инференс YOLO (64-bit ОС, лаб. БП 5.1V, active cooler)

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
- [ ] Установить LM2596 DC-DC конвертер для стабильного питания
- [x] Замерить диск (microSD: запись 73.5 MB/s, чтение 94.5 MB/s)
- [ ] Настроить config.txt (PWM, камера, питание)
- [ ] Подключить камеру (кабель 22→15 pin заказан)
- [ ] Установить SocksTank зависимости (fastapi, uvicorn, pydantic-settings)
- [ ] Протестировать SocksTank serve --mock
