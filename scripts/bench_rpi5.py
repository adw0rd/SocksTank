#!/usr/bin/env python3
"""Безопасный бенчмарк NCNN моделей на RPi 5 с плавным стартом.

Использует taskset для ограничения ядер и предотвращения краша питания.
Запуск: sudo taskset -c 0 python3 scripts/bench_rpi5.py
"""

import os
import sys
import time
import platform

import numpy as np


def set_affinity(cores: list[int]):
    """Установить CPU affinity (только Linux)."""
    if platform.system() == "Linux":
        os.sched_setaffinity(0, set(cores))
        print(f"  CPU affinity: ядра {cores}")


def bench_model(model_path: str, label: str, n_warmup: int = 5, n_iter: int = 20):
    """Бенчмарк одной модели."""
    from ultralytics import YOLO

    print(f"\n{'=' * 60}")
    print(f"  {label}: {model_path}")
    print(f"{'=' * 60}")

    if not os.path.exists(model_path):
        print("  SKIP: модель не найдена")
        return None

    # Стадия 1: загрузка на 1 ядре
    set_affinity([0])
    print("  Загрузка модели на 1 ядре...")
    model = YOLO(model_path)
    dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Warmup на 1 ядре
    print(f"  Warmup ({n_warmup} итераций, 1 ядро)...")
    for i in range(n_warmup):
        model(dummy, verbose=False)
    time.sleep(1)

    # Стадия 2: бенч на 2 ядрах
    set_affinity([0, 1])
    print("  Warmup (3 итерации, 2 ядра)...")
    for i in range(3):
        model(dummy, verbose=False)
    time.sleep(1)

    # Стадия 3: бенч на разном кол-ве ядер
    results = {}
    for n_cores in [1, 2, 3, 4]:
        cores = list(range(n_cores))
        set_affinity(cores)
        time.sleep(0.5)

        # Warmup для этой конфигурации
        for _ in range(3):
            model(dummy, verbose=False)

        # Замер
        times = []
        for _ in range(n_iter):
            t0 = time.monotonic()
            model(dummy, verbose=False)
            times.append((time.monotonic() - t0) * 1000)

        avg = sum(times) / len(times)
        mn, mx = min(times), max(times)
        fps = 1000 / avg
        results[n_cores] = {"avg": avg, "min": mn, "max": mx, "fps": fps}
        print(f"  {n_cores} ядер: avg={avg:.1f}ms min={mn:.1f}ms max={mx:.1f}ms FPS={fps:.1f}")

        # Пауза между стадиями (предотвращение пикового тока)
        if n_cores < 4:
            time.sleep(2)

    # Восстановить все ядра
    set_affinity(list(range(os.cpu_count() or 4)))
    return results


def main():
    print("Бенчмарк NCNN моделей на RPi 5")
    print(f"Python {sys.version}")
    print(f"OS: {platform.platform()}")
    print(f"CPU: {os.cpu_count()} ядер")

    # Читаем температуру
    try:
        temp = os.popen("vcgencmd measure_temp").read().strip()
        print(f"Температура: {temp}")
    except Exception:
        pass

    models = [
        ("models/yolo11_best_ncnn_model", "FP32 NCNN"),
        ("models/yolo11_best_ncnn_int8_model", "INT8 NCNN"),
    ]

    all_results = {}
    for path, label in models:
        result = bench_model(path, label)
        if result:
            all_results[label] = result

    # Сводная таблица
    if all_results:
        print(f"\n{'=' * 60}")
        print("  СВОДКА")
        print(f"{'=' * 60}")
        print(f"{'Модель':<12} {'Ядра':>5} {'Avg ms':>8} {'FPS':>6} {'Прирост':>8}")
        print("-" * 45)

        fp32_avgs = all_results.get("FP32 NCNN", {})
        for label, results in all_results.items():
            for n_cores, r in sorted(results.items()):
                speedup = ""
                if label == "INT8 NCNN" and n_cores in fp32_avgs:
                    ratio = fp32_avgs[n_cores]["avg"] / r["avg"]
                    speedup = f"{ratio:.2f}x"
                print(f"{label:<12} {n_cores:>5} {r['avg']:>8.1f} {r['fps']:>6.1f} {speedup:>8}")

    print("\nГотово!")


if __name__ == "__main__":
    main()
