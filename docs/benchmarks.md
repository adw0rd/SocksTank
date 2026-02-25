# Бенчмарки инференса

Замеры скорости инференса YOLO на разных устройствах и форматах модели.
Входные данные: случайный кадр 640x480 RGB. Замер: 20-30 кадров после 3-5 warmup итераций.

## RPi 4 Model B (Cortex-A72 1.8 GHz, 3.3 GB RAM)

OS: Debian bookworm **64-bit**, Python 3.11 (aarch64), torch 2.8.0+cpu
Охлаждение: heatsink case (пассивное + активное)

| Модель | Формат | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | PyTorch | 879 | 869 | 899 | **1.1** |
| YOLOv8n | PyTorch | 880 | 872 | 886 | **1.1** |
| YOLOv11n | NCNN | 409 | 402 | 440 | **2.4** |
| YOLOv11n | ONNX | ❌ | — | — | **крэш** |

> ⚠️ ONNX (onnxruntime 1.24.2): rpi4 зависает при загрузке модели.
> GPU device discovery в onnxruntime вызывает kernel hang. Не использовать до фикса.

Температура при бенчмарке: 44→49°C (heatsink case), throttled=0x0.

Дата замера: 2026-02-24, обновлено 2026-02-25

## RPi 5 Model B (Cortex-A76 2.4 GHz, 8 GB RAM)

OS: Debian trixie **64-bit**, Python 3.13.5 (aarch64), torch 2.10.0+cpu
Охлаждение: активное (PWM fan)
Питание: лабораторный БП 5.1V через GPIO

| Модель | Формат | Потоки | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN (native API) | 1 | 161 | 149 | 178 | **6.2** |
| YOLOv11n | PyTorch | 4 | 288 | 285 | 298 | **3.5** |
| YOLOv11n | ONNX | auto | 331 | 276 | 426 | **3.0** |

> ⚠️ NCNN pip wheel (1.0.20260114) для Python 3.13 aarch64 имеет баг: OpenMP multi-threading
> даёт деградацию (4 потока медленнее 1). Используем 1 поток — он самый быстрый.
> ncnn собран из исходников с `-DNCNN_OPENMP=ON`, но проблема в Python binding.

Температура при бенчмарке: 68→75°C (active cooler), throttled=0x0.
Питание: EXT5V=5.03-5.08V, VDD_CORE до 2.0A при нагрузке.

Дата замера: 2026-02-25 (обновлено)

### Старые замеры (32-bit OS, 1 ядро, литий)

OS: Raspbian bookworm **32-bit** (armhf), ncnn only.
Питание: Freenove Tank Board (2x18650).

| Модель | Формат | Ядра | Mean (ms) | FPS |
|---|---|---|---|---|
| YOLOv11n | NCNN | 1 (taskset) | 323 | **3.1** |
| YOLOv11n | NCNN | 2+ | — | **крэш** (undervoltage) |

> **Проблема питания**: Freenove Tank Board DC/DC не обеспечивает достаточный ток для RPi 5.
> Плата выключается при полной нагрузке (все 4 ядра). См. [rpi5-power.md](rpi5-power.md).
> Решение: LM2596 DC-DC buck converter или лабораторный БП 5.1V/5A через GPIO.

## blackops GPU (NVIDIA RTX 4070 SUPER)

OS: Ubuntu, Python 3.13.3, torch + CUDA

| Модель | Формат | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | PyTorch CUDA | 3.2 | 3.2 | 3.2 | **314.8** |

Дата замера: 2026-02-25

## Сводное сравнение всех устройств

### Характеристики

| | RPi 4 Model B | RPi 5 Model B | blackops |
|---|---|---|---|
| CPU | Cortex-A72 4x1.8 GHz | Cortex-A76 4x2.4 GHz | Ryzen (desktop) |
| GPU | — | — | RTX 4070 SUPER |
| RAM | 3.3 GB | 8 GB | 32+ GB |
| ОС | Debian 12 bookworm 64-bit | Debian 13 trixie 64-bit | Ubuntu |
| Python | 3.11.2 | 3.13.5 | 3.13.3 |
| Диск | USB SanDisk 115 GB | microSD 117 GB | NVMe Samsung 990 PRO |

### Диск

| Устройство | Запись | Чтение |
|---|---|---|
| RPi 4 | 60.7 MB/s | 151 MB/s |
| RPi 5 | 73.5 MB/s | 94.5 MB/s |
| blackops | 4.4 GB/s | 15.2 GB/s* |

\* blackops: аномально высокая скорость чтения — данные закешировались в RAM.

### Инференс YOLO (YOLOv11n)

| Устройство | Формат | Mean (ms) | FPS | vs RPi 4 PyTorch |
|---|---|---|---|---|
| RPi 4 | PyTorch | 879 | **1.1** | — |
| RPi 4 | NCNN | 409 | **2.4** | 2.2x |
| RPi 4 | ONNX | — | **крэш** | — |
| RPi 5 | NCNN (1 thread) | 161 | **6.2** | **5.6x** |
| RPi 5 | PyTorch | 288 | **3.5** | 3.2x |
| RPi 5 | ONNX | 331 | **3.0** | 2.7x |
| blackops | PyTorch CUDA | 3.2 | **314.8** | **286x** |
| GPU remote (HTTP) | PyTorch CUDA | _TODO_* | — | — |

\* с учётом сетевого overhead (~10-15ms roundtrip по Wi-Fi)

### Температура при нагрузке

| Устройство | Охлаждение | Idle | Нагрузка | Throttled |
|---|---|---|---|---|
| RPi 4 | Heatsink case | ~40°C | 44→49°C | 0x0 |
| RPi 5 | Без радиатора | ~42°C | 48→64°C | 0x0 |

### Выводы

- **RPi 5 с NCNN (1 thread) — 6.2 FPS** — лучший результат на RPi
- NCNN multi-threading деградирует из-за бага в Python binding (4 потока медленнее 1)
- ONNX работает на RPi 5, но крашит RPi 4 (баг onnxruntime GPU discovery)
- blackops GPU быстрее RPi 5 в **51x** (314.8 vs 6.2 FPS)
- RPi 5 **требует стабильный 5.1V** (LM2596 или лаб. БП), Freenove DC/DC не хватает

Дата замеров: 2026-02-25
