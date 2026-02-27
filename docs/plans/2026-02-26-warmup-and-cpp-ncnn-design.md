# Дизайн: Плавный старт + C++ NCNN Wrapper

Дата: 2026-02-26

## Задача 1: Плавный старт (CPU warmup)

### Проблема
XL6019E1 (5A buck-boost) крашит RPi 5 при мгновенной нагрузке на 4 ядра.
Нужен постепенный ramp-up: 1→2→3→4 ядра с паузами между стадиями.

### Решение
Новый модуль `server/cpu_warmup.py`, вызывается в `app.py` lifespan после загрузки модели, до старта камеры.

### Механизм
1. Установить CPU affinity на 1 ядро через `os.sched_setaffinity(0, {0})`
2. Прогнать N warmup-итераций модели (dummy frame 640x640)
3. Добавить ядро, пауза, повторить warmup
4. После финальной стадии — восстановить affinity на все ядра
5. Логировать каждую стадию (время, кол-во ядер)

### Конфигурация (config.py)
```python
cpu_warmup: bool = True           # Включить плавный старт
cpu_warmup_stages: str = "1,2,3,4"  # Стадии (кол-во ядер)
cpu_warmup_samples: int = 3       # Итераций на стадию
cpu_warmup_pause_s: float = 2.0   # Пауза между стадиями (секунды)
```

### Интеграция (app.py)
```python
# После загрузки модели, до старта камеры
if model and not settings.mock and settings.cpu_warmup:
    from server.cpu_warmup import gradual_warmup
    gradual_warmup(model, settings)
```

### Файлы
- **Новый:** `server/cpu_warmup.py` — модуль warmup
- **Изменить:** `server/config.py` — добавить параметры warmup
- **Изменить:** `server/app.py` — вызов warmup в lifespan

---

## Задача 2: C++ NCNN Wrapper с OMP (НЕАКТУАЛЬНО)

> **UPDATE 2026-02-27**: Обнаружен OMP workaround для pip ncnn: `ncnn.set_omp_num_threads(N)`
> перед каждым инференсом обходит баг `get_omp_num_threads()=1`.
> Результат: pip ncnn 4 OMP потока — **62ms чистый инференс / 78ms с preproc = 12.8–16.0 FPS**.
> C++ wrapper **не нужен** — pip wheel быстрее сборки из исходников (сборка ncnn из src в 6x медленнее).
> Реализовано в `NcnnNativeDetector` (`server/inference.py`).

### Проблема (оригинальная)
Python ncnn binding (pip wheel для cp313 aarch64) — `get_omp_num_threads()` всегда 1.
C++ с 2 OMP потоками: 78ms / 12.8 FPS vs Python 130ms / 7.7 FPS (1 поток).

### Решение
C++ модуль с pybind11: класс `NCNNDetector` с полным пайплайном.

### Архитектура

```
ncnn_wrapper/
├── CMakeLists.txt        # Сборка: ncnn + OpenCV + pybind11
├── src/
│   ├── detector.h        # NCNNDetector класс
│   ├── detector.cpp       # Инференс + NMS + OMP контроль
│   └── bindings.cpp      # pybind11 обёртка
├── build/                # Артефакты сборки
└── README.md             # Инструкции сборки
```

### C++ API
```cpp
class NCNNDetector {
public:
    bool load(const std::string& param_path,
              const std::string& bin_path,
              int num_threads = 2);

    // Основной метод: frame (HxWx3 uint8 BGR) → detections
    std::vector<Detection> detect(const uint8_t* data,
                                   int height, int width,
                                   float confidence = 0.5f,
                                   float nms_threshold = 0.45f);

    void set_num_threads(int n);
    float last_inference_ms() const;
};
```

### Python API (через pybind11)
```python
import ncnn_wrapper

det = ncnn_wrapper.NCNNDetector()
det.load("model.ncnn.param", "model.ncnn.bin", num_threads=2)

# numpy array (H, W, 3) uint8 BGR
results = det.detect(frame, confidence=0.5, nms_threshold=0.45)
# → [{"class_id": 0, "confidence": 0.92, "bbox": [x1, y1, x2, y2]}, ...]
```

### Интеграция в InferenceRouter
Новый бэкенд в `inference.py`:

```python
def _infer_local(self, frame, confidence):
    if self._cpp_detector:
        # C++ путь: быстрый, с OMP
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        raw = self._cpp_detector.detect(bgr, confidence=confidence)
        return [{"class": self._names[d["class_id"]], ...} for d in raw]
    else:
        # Fallback: ultralytics YOLO
        results = self._model(frame, conf=confidence, verbose=False)
        ...
```

### Post-processing в C++
- Letterbox resize 640x640 с сохранением пропорций
- Прогон через NCNN (in0 → out0)
- Декодирование: out0 shape [1, 5, 8400] → bbox + confidence
- NMS (IoU threshold 0.45)
- Маппинг координат обратно к оригиналу

### Модель
- Input: `in0` — float32 [3, 640, 640]
- Output: `out0` — float32 [1, 5, 8400] (4 bbox + 1 class conf, 8400 anchors)
- 1 класс: sock (id=0)
- Stride: 32

### Сборка
```bash
# RPi 5 (aarch64)
cd ncnn_wrapper && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4
# → ncnn_wrapper.cpython-313-aarch64-linux-gnu.so

# macOS (для разработки, mock)
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### Зависимости
- ncnn (собрать из исходников с `-DNCNN_OPENMP=ON`)
- OpenCV (для resize/cvtColor)
- pybind11
- CMake 3.14+

### Файлы
- **Новая директория:** `ncnn_wrapper/` — весь C++ код
- **Изменить:** `server/inference.py` — добавить C++ бэкенд
- **Изменить:** `server/config.py` — `ncnn_cpp: bool`, `ncnn_threads: int`
- **Изменить:** `server/app.py` — загрузка C++ детектора

---

## Задачи на rpi5 (SSH)

### INT8 бенчмарк (Задача 1)
- Запустить `models/yolo11_best_ncnn_int8_model/` через ultralytics bench
- Сравнить с FP32 (89ms)
- Ожидание: 1.5-2x прирост

### config.txt (Задача 3)
- Настроить PWM, камеру, питание на rpi5
- `/boot/firmware/config.txt`

### Тест serve (Задача 5)
- После интеграции warmup — деплой и тест на rpi5
