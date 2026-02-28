# TODO

## RPi 5

- [x] Переустановить 64-bit Raspberry Pi OS (Debian 13 trixie)
- [x] Установить torch, ultralytics, ncnn, onnxruntime
- [x] Замерить YOLO инференс на 4 ядрах (PyTorch 3.5 FPS, NCNN 14.6 FPS, ONNX 6.8 FPS)
- [x] Установить DC-DC конвертер (XL6019E1, 5.2V, 4 ядра стабильно, 11.2 FPS)
- [x] Замерить диск (microSD: запись 73.5 MB/s, чтение 94.5 MB/s)
- [x] Настроить config.txt (PWM, камера, питание, gpu_mem, disable-bt)
- [x] Установить SocksTank зависимости (fastapi, uvicorn, pydantic-settings)
- [x] Протестировать SocksTank serve --mock (10.9 FPS)
- [ ] Подключить камеру (кабель 22→15 pin заказан)
- [ ] Протестировать SocksTank serve с реальной камерой
- [ ] Фотка танка с носком в клешне для корневого README

## Оптимизация

- [x] Оптимизировать postprocess (было ~14ms overhead → 3.4ms, vectorized numpy вместо Python loop)
- [x] Попробовать разгон RPi 5 — 2600: +2.5% (16.2 FPS), 2800: throttle. Не стоит того, откат на сток
