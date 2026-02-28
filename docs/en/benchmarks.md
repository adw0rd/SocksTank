# Inference Benchmarks

YOLO inference speed measurements on different devices and model formats.
Input: random 640x480 RGB frame. Measurement: 20-30 frames after 3-5 warmup iterations.

## RPi 4 Model B (legacy) (Cortex-A72 1.8 GHz, 3.3 GB RAM)

OS: Debian bookworm **64-bit**, Python 3.11 (aarch64), torch 2.8.0+cpu
Cooling: heatsink case (passive + active)

| Model | Format | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | PyTorch | 879 | 869 | 899 | **1.1** |
| YOLOv8n | PyTorch | 880 | 872 | 886 | **1.1** |
| YOLOv11n | NCNN | 409 | 402 | 440 | **2.4** |
| YOLOv11n | ONNX | ❌ | — | — | **crash** |

> ⚠️ ONNX (onnxruntime 1.24.2): rpi4 (legacy) hangs on model load.
> GPU device discovery in onnxruntime causes kernel hang. Do not use until fixed.

Temperature during benchmark: 44→49°C (heatsink case), throttled=0x0.

Measured: 2026-02-24, updated 2026-02-25

## RPi 5 Model B (Cortex-A76 2.4 GHz, 8 GB RAM)

OS: Debian trixie **64-bit**, Python 3.13.5 (aarch64), torch 2.10.0+cpu
Cooling: active (PWM fan)
Power: LM2596 DC-DC (2x18650→5.1V) via GPIO, or lab PSU 5.1V

### pip ncnn native + OMP workaround (lab PSU 5.1V, recommended)

| Model | Format | OMP threads | Mean (ms) | Inference (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | **pip ncnn native** | **4** | **78** | 64 | **12.8** |
| YOLOv11n | pip ncnn native | 2 | 92 | 77 | **10.9** |
| YOLOv11n | pip ncnn native | 1 | 133 | 119 | **7.5** |
| YOLOv11n | pip ncnn (pure, no preproc) | 4 | **62** | 62 | **16.0** |

> **OMP workaround**: `ncnn.set_omp_num_threads(N)` before each inference bypasses pip ncnn bug.
> `get_omp_num_threads()` returns 1 (bug), but `set` works!
> Preprocess (letterbox + normalize) takes ~14ms.

### XL6019E1 (battery powered, 2x18650→5.2V)

| Model | Format | Cores | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN (ultralytics) | 4 (gradual start) | 89 | 87 | 97 | **11.2** |
| YOLOv11n | NCNN (ultralytics) | 3 (taskset) | 90 | 87 | 99 | **11.1** |

EXT5V=5.22-5.23V, VDD_CORE=1.48-1.58A, throttled=0x0, temperature 38→47°C.

> ⚠️ Requires **[gradual startup](rpi5-power.md#gradual-startup-cpu-warmup)** (load model on 1 core → gradually scale to 4).
> Direct 4-core startup causes crash due to peak current spike.

### LM2596 (battery powered, 2x18650→5.1V)

| Model | Format | Cores | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN | 2 (taskset) | 90 | 86 | 106 | **11.1** |
| YOLOv11n | NCNN | 1 (taskset) | 130 | 128 | 134 | **7.7** |
| YOLOv11n | NCNN | 3+ | — | — | — | **crash** |

EXT5V=5.06-5.10V, VDD_CORE up to 1.89A (2 cores), throttled=0x0.

> LM2596 (rated 3A) cannot handle 3+ cores. Optimum: 2 cores, 11.1 FPS.

### Lab PSU 5.1V (for comparison)

| Model | Format | Threads | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|---|
| YOLOv11n | NCNN (native API) | 1 | 161 | 149 | 178 | **6.2** |
| YOLOv11n | PyTorch | 4 | 288 | 285 | 298 | **3.5** |
| YOLOv11n | ONNX | auto | 331 | 276 | 426 | **3.0** |

> Measured via ultralytics YOLO wrapper (without OMP workaround).
> With OMP workaround (`ncnn.set_omp_num_threads`) — see "pip ncnn native" section above.

Temperature during benchmark: 68→75°C (active cooler), throttled=0x0.
Power: EXT5V=5.03-5.08V, VDD_CORE up to 2.0A under load.

Measured: 2026-02-25 (updated)

### Old measurements (32-bit OS, 1 core, battery)

OS: Raspbian bookworm **32-bit** (armhf), ncnn only.
Power: Freenove Tank Board (2x18650).

| Model | Format | Cores | Mean (ms) | FPS |
|---|---|---|---|---|
| YOLOv11n | NCNN | 1 (taskset) | 323 | **3.1** |
| YOLOv11n | NCNN | 2+ | — | **crash** (undervoltage) |

> **Power issue**: Freenove Tank Board DC/DC cannot provide sufficient current for RPi 5.
> Board shuts down under full load (all 4 cores). See [rpi5-power.md](rpi5-power.md).
> Solution: XL6019E1 DC-DC buck-boost converter or lab PSU 5.1V/5A via GPIO.

## blackops GPU (NVIDIA RTX 4070 SUPER)

OS: Ubuntu, Python 3.13.3, torch + CUDA

| Model | Format | Mean (ms) | Min (ms) | Max (ms) | FPS |
|---|---|---|---|---|---|
| YOLOv11n | PyTorch CUDA | 3.2 | 3.2 | 3.2 | **314.8** |

Measured: 2026-02-25

## Summary Comparison

### Specifications

| | RPi 4 Model B (legacy) | RPi 5 Model B | blackops |
|---|---|---|---|
| CPU | Cortex-A72 4x1.8 GHz | Cortex-A76 4x2.4 GHz | Ryzen (desktop) |
| GPU | — | — | RTX 4070 SUPER |
| RAM | 3.3 GB | 8 GB | 32+ GB |
| OS | Debian 12 bookworm 64-bit | Debian 13 trixie 64-bit | Ubuntu |
| Python | 3.11.2 | 3.13.5 | 3.13.3 |
| Disk | USB SanDisk 115 GB | microSD 117 GB | NVMe Samsung 990 PRO |

### Disk

| Device | Write | Read |
|---|---|---|
| RPi 4 (legacy) | 60.7 MB/s | 151 MB/s |
| RPi 5 | 73.5 MB/s | 94.5 MB/s |
| blackops | 4.4 GB/s | 15.2 GB/s* |

\* blackops: abnormally high read speed — data was cached in RAM.

### YOLO Inference (YOLOv11n)

| Device | Format | Mean (ms) | FPS | vs RPi 4 PyTorch |
|---|---|---|---|---|
| RPi 4 (legacy) | PyTorch | 879 | **1.1** | — |
| RPi 4 (legacy) | NCNN | 409 | **2.4** | 2.2x |
| RPi 4 (legacy) | ONNX | — | **crash** | — |
| **RPi 5 (pip ncnn, 4 OMP)** | **pip ncnn native (pure)** | **62** | **16.0** | **14.5x** |
| RPi 5 (pip ncnn, 4 OMP) | pip ncnn native (with preproc) | 78 | **12.8** | **11.6x** |
| RPi 5 (pip ncnn, 2 OMP) | pip ncnn native (with preproc) | 92 | **10.9** | **9.9x** |
| RPi 5 (XL6019E1, 4 cores) | NCNN ultralytics (gradual start) | 89 | **11.2** | **10.2x** |
| RPi 5 (LM2596, 2 cores) | NCNN ultralytics (taskset) | 90 | **11.1** | **10.1x** |
| RPi 5 (lab PSU) | NCNN (1 thread) | 133 | **7.5** | **6.8x** |
| RPi 5 | PyTorch | 288 | **3.5** | 3.2x |
| RPi 5 | ONNX | 331 | **3.0** | 2.7x |
| blackops | PyTorch CUDA | 3.2 | **314.8** | **286x** |

> **pip ncnn native** = pip ncnn (1.0.20260114) + OMP workaround (`set_omp_num_threads`).
> Implemented in `NcnnNativeDetector` (`server/inference.py`).

### Temperature Under Load

| Device | Cooling | Idle | Under Load | Throttled |
|---|---|---|---|---|
| RPi 4 (legacy) | Heatsink case | ~40°C | 44→49°C | 0x0 |
| RPi 5 (XL6019E1) | Active cooler | ~38°C | 38→47°C | 0x0 |
| RPi 5 (LM2596) | Active cooler | ~37°C | 37→60°C | 0x0 |

### Models

| Model | Format | Precision | Size | Description |
|---|---|---|---|---|
| yolo11_best.pt | PyTorch | FP16 | 5.2 MB | Training, GPU |
| yolo11_best_ncnn_model/ | NCNN | FP32 | 9.9 MB | RPi production |
| yolo11_best_ncnn_int8_model/ | NCNN | **INT8** | **2.6 MB** | Quantized (1 thread: 117.5ms / 8.5 FPS) |
| yolo11_best.onnx | ONNX | FP32 | — | Universal |

INT8 quantization: `ncnn2table` (100 calibration images from train) → `ncnn2int8`.

**INT8 Benchmark Results** (RPi 5, pip ncnn native + OMP workaround):

| Model | OMP threads | Total (ms) | Inference (ms) | FPS | vs FP32 |
|---|---|---|---|---|---|
| FP32 | 1 | 133.2 | 118.6 | **7.5** | — |
| INT8 | 1 | 126.9 | 112.3 | **7.9** | **1.05x** |
| FP32 | 2 | 92.0 | 77.4 | **10.9** | — |
| INT8 | 2 | 92.2 | 77.4 | **10.8** | 1.00x |
| **FP32** | **4** | **78.3** | **63.3** | **12.8** | — |
| INT8 | 4 | 82.9 | 68.0 | **12.1** | 0.94x |

INT8 is faster only on 1 thread (+5%). On 2-4 threads FP32 is faster — INT8 dequantize overhead negates the gain with parallelization. INT8 advantage: model size 2.6 MB (75% smaller).

### Conclusions

- **RPi 5 pip ncnn 4 OMP threads — 16.0 FPS (pure) / 12.8 FPS (with preproc)** — absolute record
- **OMP workaround works**: `ncnn.set_omp_num_threads(N)` bypasses `get_omp_num_threads()=1` bug
- C++ ncnn wrapper not needed — pip ncnn native is faster (building ncnn from source is 6x slower than pip wheel)
- ONNX works on RPi 5 but crashes RPi 4 (legacy) (onnxruntime GPU discovery bug)
- blackops GPU is **25x** faster than RPi 5 (314.8 vs 12.8 FPS)
- XL6019E1 (5A, buck-boost) handles 4 cores with gradual start; LM2596 (3A) — max 2 cores
- RPi 5 **requires stable 5.1V+** via GPIO, Freenove DC/DC is insufficient
- **INT8 quantization**: +6% on 1 OMP thread (117.5ms vs 124.5ms), model size 2.6 MB (75% smaller)

Measured: 2026-02-27 (updated)
