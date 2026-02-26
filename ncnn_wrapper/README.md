# ncnn_wrapper — C++ NCNN обёртка для SocksTank

C++ обёртка NCNN-инференса с pybind11 биндингами для Python. Заменяет Python ncnn binding, который имеет баг с OMP потоками на aarch64 (`get_omp_num_threads()` всегда возвращает 1).

## Зависимости

### RPi 5 (Debian trixie, aarch64)

```bash
# ncnn (из исходников или пакетного менеджера)
sudo apt install libncnn-dev

# Или собрать из исходников:
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

## Сборка

```bash
cd ncnn_wrapper
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
make install  # копирует .so/.dylib в ncnn_wrapper/
```

Результат: `ncnn_wrapper/ncnn_wrapper.cpython-3XX-*.so`

## Использование

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

### SocksTank сервер

```bash
# Запуск с C++ ncnn wrapper
python main.py serve --model models/yolo11_best_ncnn_model --ncnn-cpp --ncnn-threads 2

# Или через переменные окружения
SOCKSTANK_NCNN_CPP=true SOCKSTANK_NCNN_THREADS=2 python main.py serve
```

Если C++ wrapper не найден, сервер автоматически переключится на ultralytics.

## Производительность (RPi 5)

| Backend | Потоки | Время | FPS |
|---------|--------|-------|-----|
| C++ ncnn (этот wrapper) | 2 OMP | ~78ms | ~12.8 |
| Python ncnn (баг) | 1 OMP | ~130ms | ~7.7 |
| ultralytics NCNN | 4 cores | ~89ms | ~11.2 |
| ultralytics PyTorch | 1 core | ~288ms | ~3.5 |
