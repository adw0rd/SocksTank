# Бенчмарки инференса

Замеры скорости инференса YOLO на разных устройствах и форматах модели.
Входные данные: случайный кадр 640x480 RGB. Замер: 20-30 кадров после 3-5 warmup итераций.

## RPi 4 Model B (legacy) (Cortex-A72 1.8 GHz, 3.3 GB RAM)

OS: Debian bookworm **64-bit**, Python 3.11 (aarch64), torch 2.8.0+cpu
Охлаждение: heatsink case (пассивное + активное)

| Модель | Формат | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | PyTorch | 879 | 869 | 899 | **1.1** |
| YOLOv8n | PyTorch | 880 | 872 | 886 | **1.1** |
| YOLOv11n | NCNN | 409 | 402 | 440 | **2.4** |
| YOLOv11n | ONNX | ❌ | — | — | **крэш** |

> ⚠️ ONNX (onnxruntime 1.24.2): rpi4 (legacy) зависает при загрузке модели.
> GPU device discovery в onnxruntime вызывает kernel hang. Не использовать до фикса.

Температура при бенчмарке: 44→49°C (heatsink case), throttled=0x0.

Дата замера: 2026-02-24, обновлено 2026-02-25

## RPi 5 Model B (Cortex-A76 2.4 GHz, 8 GB RAM)

OS: Debian trixie **64-bit**, Python 3.13.5 (aarch64), torch 2.10.0+cpu
Охлаждение: активное (PWM fan)
Питание: LM2596 DC-DC (2x18650→5.1V) через GPIO, или лаб. БП 5.1V

### XL6019E1 (автономное питание, 2x18650→5.2V, рекомендуется)

| Модель | Формат | Ядра | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | **NCNN** | **4 (плавный старт)** | **89** | 87 | 97 | **11.2** |
| YOLOv11n | NCNN | 3 (taskset) | 90 | 87 | 99 | **11.1** |

EXT5V=5.22-5.23V, VDD_CORE=1.48-1.58A, throttled=0x0, температура 38→47°C.

> ⚠️ Требуется **плавный старт** (загрузка модели на 1 ядре → постепенный переход на 4).
> Прямой запуск на 4 ядрах вызывает крэш из-за пикового броска тока.

### C++ ncnn напрямую (XL6019E1, без Python)

| Модель | Потоки | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | 1 | 119 | 118 | 123 | **8.4** |
| YOLOv11n | **2** | **78** | 77 | 83 | **12.8** |
| YOLOv11n | 4 | — | — | — | **крэш** (пиковый ток) |

> C++ с реальным OpenMP multi-threading. Python binding (pip ncnn) имеет баг: OMP всегда 1 поток.
> 2 потока C++ = 12.8 FPS — на 15% быстрее Python (11.2 FPS).

### LM2596 (автономное питание, 2x18650→5.1V)

| Модель | Формат | Ядра | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN | 2 (taskset) | 90 | 86 | 106 | **11.1** |
| YOLOv11n | NCNN | 1 (taskset) | 130 | 128 | 134 | **7.7** |
| YOLOv11n | NCNN | 3+ | — | — | — | **крэш** |

EXT5V=5.06-5.10V, VDD_CORE до 1.89A (2 ядра), throttled=0x0.

> LM2596 (rated 3A) не держит 3+ ядер. Оптимум: 2 ядра, 11.1 FPS.

### Лабораторный БП 5.1V (для сравнения)

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
| RPi 4 (legacy) | 60.7 MB/s | 151 MB/s |
| RPi 5 | 73.5 MB/s | 94.5 MB/s |
| blackops | 4.4 GB/s | 15.2 GB/s* |

\* blackops: аномально высокая скорость чтения — данные закешировались в RAM.

### Инференс YOLO (YOLOv11n)

| Устройство | Формат | Mean (ms) | FPS | vs RPi 4 PyTorch |
|---|---|---|---|---|
| RPi 4 (legacy) | PyTorch | 879 | **1.1** | — |
| RPi 4 (legacy) | NCNN | 409 | **2.4** | 2.2x |
| RPi 4 (legacy) | ONNX | — | **крэш** | — |
| RPi 5 (XL6019E1, C++) | NCNN C++ (2 OMP threads) | 78 | **12.8** | **11.6x** |
| RPi 5 (XL6019E1, 4 cores) | NCNN Python (плавный старт) | 89 | **11.2** | **10.2x** |
| RPi 5 (XL6019E1, 3 cores) | NCNN (taskset) | 90 | **11.1** | **10.1x** |
| RPi 5 (LM2596, 2 cores) | NCNN (taskset) | 90 | **11.1** | **10.1x** |
| RPi 5 (LM2596, 1 core) | NCNN (taskset) | 130 | **7.7** | **7.0x** |
| RPi 5 (лаб. БП) | NCNN (1 thread) | 161 | **6.2** | **5.6x** |
| RPi 5 | PyTorch | 288 | **3.5** | 3.2x |
| RPi 5 | ONNX | 331 | **3.0** | 2.7x |
| blackops | PyTorch CUDA | 3.2 | **314.8** | **286x** |
| GPU remote (HTTP) | PyTorch CUDA | _TODO_* | — | — |

\* с учётом сетевого overhead (~10-15ms roundtrip по Wi-Fi)

### Температура при нагрузке

| Устройство | Охлаждение | Idle | Нагрузка | Throttled |
|---|---|---|---|---|
| RPi 4 (legacy) | Heatsink case | ~40°C | 44→49°C | 0x0 |
| RPi 5 (XL6019E1) | Active cooler | ~38°C | 38→47°C | 0x0 |
| RPi 5 (LM2596) | Active cooler | ~37°C | 37→60°C | 0x0 |

### Модели

| Модель | Формат | Точность | Размер | Описание |
|---|---|---|---|---|
| yolo11_best.pt | PyTorch | FP16 | 5.2 MB | Тренировка, GPU |
| yolo11_best_ncnn_model/ | NCNN | FP32 | 9.9 MB | RPi продакшен |
| yolo11_best_ncnn_int8_model/ | NCNN | **INT8** | **2.6 MB** | Квантизованная (TODO: бенчмарк) |
| yolo11_best.onnx | ONNX | FP32 | — | Универсальный |

INT8 квантизация: `ncnn2table` (100 калибровочных изображений из train) → `ncnn2int8`.
Ожидаемый прирост: **1.5-2x** скорости при потере mAP ~1-3%.

### Выводы

- **RPi 5 C++ NCNN 2 OMP threads — 12.8 FPS** — абсолютный рекорд (XL6019E1)
- **RPi 5 Python NCNN 4 cores — 11.2 FPS** — лучший результат через Python (XL6019E1, плавный старт)
- NCNN Python binding (pip) имеет OMP баг: всегда 1 поток. C++ ncnn — полноценный OMP
- ONNX работает на RPi 5, но крашит RPi 4 (legacy) (баг onnxruntime GPU discovery)
- blackops GPU быстрее RPi 5 в **25x** (314.8 vs 12.8 FPS)
- XL6019E1 (5A, buck-boost) держит 4 ядра с плавным стартом; LM2596 (3A) — максимум 2 ядра
- RPi 5 **требует стабильный 5.1V** (LM2596 или лаб. БП), Freenove DC/DC не хватает
- **INT8 квантизация** готова, ожидается 1.5-2x прирост (TODO: бенчмарк на RPi 5)

Дата замеров: 2026-02-26 (обновлено)
