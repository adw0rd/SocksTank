# ncnn_wrapper — C++ NCNN Wrapper for SocksTank (LEGACY)

> **OBSOLETE**: An OMP workaround was discovered for pip ncnn: `ncnn.set_omp_num_threads(N)` before
> each inference bypasses the bug. pip ncnn with 4 OMP threads = **62ms / 16.0 FPS** (pure inference).
> C++ wrapper is not needed — pip wheel is 6x faster than building from source.
> Recommended: `NcnnNativeDetector` in `server/inference.py`.

C++ NCNN inference wrapper with pybind11 Python bindings. Replaces the Python ncnn binding, which has an OMP threading bug on aarch64 (`get_omp_num_threads()` always returns 1).

## Dependencies

### RPi 5 (Debian trixie, aarch64)

```bash
# ncnn (from source or package manager)
sudo apt install libncnn-dev

# Or build from source:
git clone https://github.com/Tencent/ncnn.git
cd ncnn && mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DNCNN_BUILD_EXAMPLES=OFF -DNCNN_BUILD_TOOLS=OFF ..
make -j$(nproc) && sudo make install

# pybind11
pip install pybind11 --break-system-packages

# CMake
sudo apt install cmake
```

### macOS (Homebrew)

```bash
brew install ncnn cmake
pip install pybind11
```

## Building

```bash
cd ncnn_wrapper
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
make install  # copies .so/.dylib to ncnn_wrapper/
```

Result: `ncnn_wrapper/ncnn_wrapper.cpython-3XX-*.so`

## Usage

### Python

```python
from ncnn_wrapper import NCNNDetector

det = NCNNDetector()
det.load("models/yolo11_best_ncnn_model/model.ncnn.param",
         "models/yolo11_best_ncnn_model/model.ncnn.bin",
         num_threads=2)

# image — numpy array (H, W, 3) uint8 RGB
results = det.detect(image, conf_threshold=0.5, nms_threshold=0.45)
# [{"class_id": 0, "confidence": 0.92, "bbox": (x1, y1, x2, y2)}, ...]

print(f"Inference: {det.last_inference_ms():.1f} ms")
```

### SocksTank server

```bash
# Run with C++ ncnn wrapper
python main.py serve --model models/yolo11_best_ncnn_model --ncnn-cpp --ncnn-threads 2

# Or via environment variables
SOCKSTANK_NCNN_CPP=true SOCKSTANK_NCNN_THREADS=2 python main.py serve
```

If the C++ wrapper is not found, the server automatically falls back to ultralytics.

## Performance (RPi 5)

| Backend | Threads | Time | FPS |
|---------|---------|------|-----|
| **pip ncnn + OMP workaround** | **4 OMP** | **62–78ms** | **12.8–16.0** |
| C++ ncnn (this wrapper) | 2 OMP | ~78ms | ~12.8 |
| Python ncnn (no workaround) | 1 OMP | ~130ms | ~7.7 |
| ultralytics NCNN | 4 cores | ~89ms | ~11.2 |
| ultralytics PyTorch | 1 core | ~288ms | ~3.5 |
