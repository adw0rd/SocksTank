"""Плавный старт CPU — поэтапная загрузка ядер для предотвращения краша питания на RPi 5."""

import os
import platform
import time
import logging

import numpy as np

log = logging.getLogger(__name__)

IS_LINUX = platform.system() == "Linux"


def gradual_warmup(model, settings) -> None:
    """Плавный прогрев модели с поэтапным увеличением числа CPU-ядер.

    На RPi 5 мгновенная загрузка всех ядер вызывает пиковый бросок тока,
    который может крашнуть систему. Этот модуль загружает ядра постепенно:
    1 → 2 → 3 → 4, с паузами между стадиями.

    На macOS/Windows affinity не управляется, но warmup модели всё равно выполняется.
    """
    stages = _parse_stages(settings.cpu_warmup_stages)
    samples = settings.cpu_warmup_samples
    pause_s = settings.cpu_warmup_pause_s
    all_cores = set(range(os.cpu_count() or 1))

    if not IS_LINUX:
        log.info("Плавный старт: не Linux (%s) — прогрев без управления affinity", platform.system())
        _warmup_iterations(model, samples)
        return

    log.info(
        "Плавный старт CPU: стадии=%s, итераций=%d, пауза=%.1fс",
        stages,
        samples,
        pause_s,
    )

    for i, num_cores in enumerate(stages):
        cores = set(range(num_cores))
        os.sched_setaffinity(0, cores)

        stage_start = time.monotonic()
        avg_ms = _warmup_iterations(model, samples)
        stage_duration = time.monotonic() - stage_start

        log.info(
            "Стадия %d/%d: %d ядер, avg %.1f мс/кадр, стадия %.1fс",
            i + 1,
            len(stages),
            num_cores,
            avg_ms,
            stage_duration,
        )

        # Пауза между стадиями (кроме последней)
        if i < len(stages) - 1:
            time.sleep(pause_s)

    # Восстановить доступ ко всем ядрам
    os.sched_setaffinity(0, all_cores)
    log.info("Плавный старт завершён, affinity восстановлен: %d ядер", len(all_cores))


def _warmup_iterations(model, samples: int) -> float:
    """Запустить N итераций инференса на фиктивном кадре, вернуть среднее время (мс)."""
    dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    times_ms = []

    for _ in range(samples):
        t0 = time.monotonic()
        if hasattr(model, "detect"):
            model.detect(dummy, 0.5)
        else:
            model(dummy, verbose=False)
        elapsed_ms = (time.monotonic() - t0) * 1000
        times_ms.append(elapsed_ms)

    avg_ms = sum(times_ms) / len(times_ms) if times_ms else 0.0
    return avg_ms


def _parse_stages(stages_str: str) -> list[int]:
    """Распарсить строку стадий '1,2,3,4' в список [1, 2, 3, 4]."""
    parts = [s.strip() for s in stages_str.split(",") if s.strip()]
    result = []
    for part in parts:
        try:
            n = int(part)
            if n > 0:
                result.append(n)
        except ValueError:
            log.warning("Пропущена невалидная стадия: '%s'", part)
    if not result:
        log.warning("Нет валидных стадий, используется [1]")
        return [1]
    return result
