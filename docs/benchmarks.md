# Бенчмарки инференса

Замеры скорости инференса YOLO на разных устройствах и форматах модели.
Входные данные: случайный кадр 640x480 RGB. Замер: 20-30 кадров после 3-5 warmup итераций.

## RPi 4 Model B (Cortex-A72 1.8 GHz, 3.3 GB RAM)

OS: Debian bookworm, Python 3.11, torch 2.8.0+cpu

| Модель | Формат | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | PyTorch | 877 | 869 | 886 | **1.1** |
| YOLOv8n | PyTorch | 880 | 872 | 886 | **1.1** |
| YOLOv11n | NCNN | 409 | 402 | 440 | **2.4** |

Дата замера: 2026-02-24

## RPi 5 (Cortex-A76 2.4 GHz, активное охлаждение)

_TODO: замеры после настройки rpi5_

## blackops GPU (NVIDIA RTX 4070 SUPER)

_TODO: замеры после включения blackops_

## Сравнение (ожидаемое)

| Устройство | Формат | Ожидаемый FPS |
|---|---|---|
| RPi 4 | PyTorch | 1.1 |
| RPi 4 | NCNN | 2.4 |
| RPi 5 | PyTorch | ~3-5 |
| RPi 5 | NCNN | ~6-10 |
| GPU (remote, HTTP POST) | PyTorch CUDA | ~50-80* |

\* с учётом сетевого overhead (~10-15ms roundtrip по Wi-Fi)
