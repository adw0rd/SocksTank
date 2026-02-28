#!/usr/bin/env python3
"""Safe NCNN benchmark for Raspberry Pi 5 with gradual warm-up.

Uses taskset to limit active cores and reduce the risk of power-related crashes.
Run with: sudo taskset -c 0 python3 scripts/bench_rpi5.py
"""

import os
import sys
import time
import platform
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def set_affinity(cores: list[int]):
    """Set CPU affinity on Linux."""
    if platform.system() == "Linux":
        os.sched_setaffinity(0, set(cores))
        print(f"  CPU affinity: cores {cores}")


def bench_model(model_path: str, label: str, n_warmup: int = 5, n_iter: int = 20):
    """Benchmark a single model."""
    from server.inference import _try_load_ncnn_native

    print(f"\n{'=' * 60}")
    print(f"  {label}: {model_path}")
    print(f"{'=' * 60}")

    if not os.path.exists(model_path):
        print("  SKIP: model not found")
        return None

    # Stage 1: load on a single core
    set_affinity([0])
    print("  Loading model on 1 core...")
    warmup_model, _ = _try_load_ncnn_native(model_path, 1)
    if warmup_model is None:
        print("  SKIP: failed to load NCNN model")
        return None
    dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Warm up on 1 core
    print(f"  Warmup ({n_warmup} iterations, 1 core)...")
    for _ in range(n_warmup):
        warmup_model.detect(dummy, 0.5)
    time.sleep(1)

    # Stage 2: benchmark on 2 cores
    set_affinity([0, 1])
    print("  Warmup (3 iterations, 2 cores)...")
    for _ in range(3):
        warmup_model.detect(dummy, 0.5)
    time.sleep(1)

    # Stage 3: benchmark on different core counts
    results = {}
    for n_cores in [1, 2, 3, 4]:
        cores = list(range(n_cores))
        set_affinity(cores)
        model, _ = _try_load_ncnn_native(model_path, n_cores)
        if model is None:
            print(f"  SKIP: failed to reload NCNN model for {n_cores} cores")
            continue
        time.sleep(0.5)

        # Warm up for this configuration
        for _ in range(3):
            model.detect(dummy, 0.5)

        # Measure runtime
        times = []
        for _ in range(n_iter):
            t0 = time.monotonic()
            model.detect(dummy, 0.5)
            times.append((time.monotonic() - t0) * 1000)

        avg = sum(times) / len(times)
        mn, mx = min(times), max(times)
        fps = 1000 / avg
        results[n_cores] = {"avg": avg, "min": mn, "max": mx, "fps": fps}
        print(f"  {n_cores} cores: avg={avg:.1f}ms min={mn:.1f}ms max={mx:.1f}ms FPS={fps:.1f}")

        # Pause between stages to avoid current spikes
        if n_cores < 4:
            time.sleep(2)

    # Restore all CPU cores
    set_affinity(list(range(os.cpu_count() or 4)))
    return results


def main():
    print("NCNN benchmark on Raspberry Pi 5")
    print(f"Python {sys.version}")
    print(f"OS: {platform.platform()}")
    print(f"CPU: {os.cpu_count()} cores")

    # Read the current temperature
    try:
        temp = os.popen("vcgencmd measure_temp").read().strip()
        print(f"Temperature: {temp}")
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

    # Summary table
    if all_results:
        print(f"\n{'=' * 60}")
        print("  SUMMARY")
        print(f"{'=' * 60}")
        print(f"{'Model':<12} {'Cores':>5} {'Avg ms':>8} {'FPS':>6} {'Speedup':>8}")
        print("-" * 45)

        fp32_avgs = all_results.get("FP32 NCNN", {})
        for label, results in all_results.items():
            for n_cores, r in sorted(results.items()):
                speedup = ""
                if label == "INT8 NCNN" and n_cores in fp32_avgs:
                    ratio = fp32_avgs[n_cores]["avg"] / r["avg"]
                    speedup = f"{ratio:.2f}x"
                print(f"{label:<12} {n_cores:>5} {r['avg']:>8.1f} {r['fps']:>6.1f} {speedup:>8}")

    print("\nDone!")


if __name__ == "__main__":
    main()
