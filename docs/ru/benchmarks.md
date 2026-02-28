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
Охлаждение: активное (PWM-вентилятор)
Питание: LM2596 DC-DC (2x18650→5.1V) через GPIO или лабораторный БП 5.1V

### pip ncnn native + OMP workaround (лаб. БП 5.1V, рекомендуется)

| Модель | Формат | OMP потоки | Mean (ms) | Инференс (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | **pip ncnn native** | **4** | **67.2** | 63.4 | **14.9** |
| YOLOv11n | pip ncnn native | 2 | 81.0 | 77.6 | **12.3** |
| YOLOv11n | pip ncnn native | 1 | 122.7 | 119.2 | **8.1** |
| YOLOv11n | pip ncnn (чистый, без preproc) | 4 | **63.4** | 63.4 | **15.8** |

> **OMP workaround**: `ncnn.set_omp_num_threads(N)` перед каждым инференсом обходит баг pip ncnn.
> `get_omp_num_threads()` возвращает 1 (баг), но `set` работает!
> Препроцессинг (letterbox + normalize) теперь добавляет только ~3.8ms к чистому инференсу.
> Именно эти числа являются основным RPi benchmark path, потому что они сняты на том же runtime, что и прод: `NcnnNativeDetector` в `server/inference.py`.
> `ultralytics` NCNN wrapper не стоит использовать как главный performance reference на RPi: он не совпадает с production path, может занижать FPS и может не принимать некоторые NCNN layout'ы, например каталог с именем `*_ncnn_int8_model`.

### XL6019E1 (автономное питание, 2x18650→5.2V)

| Модель | Формат | Ядра | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN (ultralytics) | 4 (плавный старт) | 89 | 87 | 97 | **11.2** |
| YOLOv11n | NCNN (ultralytics) | 3 (taskset) | 90 | 87 | 99 | **11.1** |

EXT5V=5.22-5.23V, VDD_CORE=1.48-1.58A, throttled=0x0, температура 38→47°C.

> ⚠️ Требуется **[плавный старт](rpi5-power.md#плавный-старт-cpu-warmup)** (загрузка модели на 1 ядре → постепенный переход на 4).
> Прямой запуск на 4 ядрах вызывает крэш из-за пикового броска тока.

### LM2596 (автономное питание, 2x18650→5.1V)

| Модель | Формат | Ядра | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN | 2 (taskset) | 90 | 86 | 106 | **11.1** |
| YOLOv11n | NCNN | 1 (taskset) | 130 | 128 | 134 | **7.7** |
| YOLOv11n | NCNN | 3+ | — | — | — | **крэш** |

EXT5V=5.06-5.10V, VDD_CORE до 1.89A (2 ядра), throttled=0x0.

> LM2596 (номинально 3A) не держит 3+ ядер. Оптимум: 2 ядра, 11.1 FPS.

### Лабораторный БП 5.1V (для сравнения, исторический baseline)

| Модель | Формат | Потоки | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN (native API) | 1 | 161 | 149 | 178 | **6.2** |
| YOLOv11n | PyTorch | 4 | 288 | 285 | 298 | **3.5** |
| YOLOv11n | ONNX | auto | 331 | 276 | 426 | **3.0** |

> Замеры выполнены через ultralytics YOLO wrapper (без OMP workaround).
> С OMP workaround (`ncnn.set_omp_num_threads`) — см. секцию "pip ncnn native" выше.

Температура при бенчмарке: 68→75°C (активный кулер), throttled=0x0.
Питание: EXT5V=5.03-5.08V, VDD_CORE до 2.0A при нагрузке.

Исторический baseline: 2026-02-25

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

### Разгон (лаб. БП 5.1V)

Тест разгона RPi 5 через `arm_freq` и `over_voltage` в `/boot/firmware/config.txt`.
Бенчмарк: pip ncnn native, 4 OMP потока, 20 кадров после 3 warmup.

| Частота | over_voltage | Инференс (ms) | FPS | Throttled | Темп. | vs Сток |
|---|---|---|---|---|---|---|
| **2400 MHz** (сток) | — | 63.2 | **15.8** | 0x0 | ~55°C | — |
| **2600 MHz** | 4 | 61.6 | **16.2** | 0x0 | ~58°C | **+2.5%** |
| **2800 MHz** | 6 | 72.4 | **13.8** | 0x50000 | ~57°C | **-12.7%** |

> 2800 MHz вызывает throttling из-за просадки напряжения (0x50000: биты 16+18) даже на лаб. БП 5.1V.
> 2600 MHz работает без throttling, но даёт лишь +2.5% — не стоит риска.
> **Вывод**: стоковые 2400 MHz оптимальны. Разгон RPi 5 для NCNN инференса неэффективен.

Дата замера: 2026-02-28

## blackops GPU (NVIDIA RTX 4070 SUPER)

OS: Ubuntu, Python 3.13.3, torch + CUDA

| Модель | Формат | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | PyTorch CUDA | 3.2 | 3.2 | 3.2 | **314.8** |

Дата замера: 2026-02-25

## Сводное сравнение всех устройств

### Характеристики

| | RPi 4 Model B (legacy) | RPi 5 Model B | blackops |
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
| **RPi 5 (pip ncnn, 4 OMP)** | **pip ncnn native (чистый)** | **63.4** | **15.8** | **14.4x** |
| RPi 5 (pip ncnn, 4 OMP) | pip ncnn native (с preproc) | 67.2 | **14.9** | **13.5x** |
| RPi 5 (pip ncnn, 2 OMP) | pip ncnn native (с preproc) | 81.0 | **12.3** | **11.2x** |
| RPi 5 (XL6019E1, 4 cores) | NCNN ultralytics (плавный старт) | 89 | **11.2** | **10.2x** |
| RPi 5 (LM2596, 2 cores) | NCNN ultralytics (taskset) | 90 | **11.1** | **10.1x** |
| RPi 5 (лаб. БП) | NCNN (1 thread) | 122.7 | **8.1** | **7.4x** |
| RPi 5 | PyTorch | 288 | **3.5** | 3.2x |
| RPi 5 | ONNX | 331 | **3.0** | 2.7x |
| blackops | PyTorch CUDA | 3.2 | **314.8** | **286x** |

> **pip ncnn native** = pip ncnn (1.0.20260114) + OMP workaround (`set_omp_num_threads`).
> Реализовано в `NcnnNativeDetector` (`server/inference.py`).

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
| yolo11_best_ncnn_int8_model/ | NCNN | **INT8** | **2.6 MB** | Квантизованная (1 поток: 117.5ms / 8.5 FPS) |
| yolo11_best.onnx | ONNX | FP32 | — | Универсальный |

INT8 квантизация: `ncnn2table` (100 калибровочных изображений из train) → `ncnn2int8`.

**Результаты INT8 бенчмарка** (RPi 5, pip ncnn native + OMP workaround):

| Модель | OMP потоки | Total (ms) | Инференс (ms) | FPS | vs FP32 |
|---|---|---|---|---|---|
| FP32 | 1 | 122.6 | 118.6 | **8.2** | — |
| INT8 | 1 | 117.9 | 112.3 | **8.5** | **1.04x** |
| FP32 | 2 | 84.3 | 77.4 | **11.9** | — |
| INT8 | 2 | 86.5 | 77.4 | **11.6** | 0.97x |
| FP32 | 3 | 77.4 | — | **12.9** | — |
| INT8 | 3 | 82.0 | — | **12.2** | 0.94x |
| **FP32** | **4** | **70.9** | **63.4** | **14.1** | — |
| INT8 | 4 | 77.7 | 68.0 | **12.9** | 0.91x |

INT8 немного быстрее только на 1 потоке (+4%). Начиная с 2 потоков FP32 остаётся быстрее. Главное преимущество INT8 по-прежнему в размере модели: 2.6 MB (на 75% меньше).

### Выводы

- **RPi 5 pip ncnn 4 OMP threads — 15.8 FPS (чистый) / 14.9 FPS (с preproc)** — лучший актуальный результат
- **OMP workaround работает**: `ncnn.set_omp_num_threads(N)` обходит баг `get_omp_num_threads()=1`
- C++ ncnn wrapper не нужен — pip ncnn native быстрее (сборка ncnn из исходников в 6x медленнее pip wheel)
- ONNX работает на RPi 5, но крашит RPi 4 (legacy) (баг onnxruntime GPU discovery)
- blackops GPU быстрее RPi 5 примерно в **21x** (314.8 vs 14.9 FPS)
- XL6019E1 (5A, buck-boost) держит 4 ядра с плавным стартом; LM2596 (3A) — максимум 2 ядра
- RPi 5 **требует стабильный 5.1V+** через GPIO, Freenove DC/DC не хватает
- **INT8 квантизация**: около +4% на 1 OMP потоке (8.5 vs 8.2 FPS), но медленнее на 2-4 потоках; размер модели остаётся 2.6 MB (75% меньше)
- **Разгон** RPi 5: 2600 MHz даёт +2.5%, 2800 MHz вызывает throttling — стоковые 2400 MHz оптимальны

Дата замеров: 2026-02-28 (обновлено)
