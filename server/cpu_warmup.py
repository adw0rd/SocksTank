"""Gradual CPU warm-up to reduce power spikes on Raspberry Pi 5."""

import os
import platform
import time
import logging

import numpy as np

log = logging.getLogger(__name__)

IS_LINUX = platform.system() == "Linux"


def gradual_warmup(model, settings) -> None:
    """Warm up the model while increasing the number of active CPU cores.

    On Raspberry Pi 5, saturating all cores instantly can create a power spike
    large enough to crash the system. This helper ramps load gradually:
    1 -> 2 -> 3 -> 4, with short pauses between stages.

    On macOS and Windows, CPU affinity is not managed, but model warm-up still runs.
    """
    stages = _parse_stages(settings.cpu_warmup_stages)
    samples = settings.cpu_warmup_samples
    pause_s = settings.cpu_warmup_pause_s
    all_cores = set(range(os.cpu_count() or 1))

    if not IS_LINUX:
        log.info("Gradual warm-up: non-Linux platform (%s), running without affinity control", platform.system())
        _warmup_iterations(model, samples)
        return

    log.info(
        "CPU warm-up: stages=%s, iterations=%d, pause=%.1fs",
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
            "Stage %d/%d: %d cores, avg %.1f ms/frame, duration %.1fs",
            i + 1,
            len(stages),
            num_cores,
            avg_ms,
            stage_duration,
        )

        # Pause between stages, except the last one
        if i < len(stages) - 1:
            time.sleep(pause_s)

    # Restore access to all CPU cores
    os.sched_setaffinity(0, all_cores)
    log.info("CPU warm-up finished, affinity restored: %d cores", len(all_cores))


def _warmup_iterations(model, samples: int) -> float:
    """Run N inference iterations on a dummy frame and return the average time in ms."""
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
    """Parse a stage string like '1,2,3,4' into [1, 2, 3, 4]."""
    parts = [s.strip() for s in stages_str.split(",") if s.strip()]
    result = []
    for part in parts:
        try:
            n = int(part)
            if n > 0:
                result.append(n)
        except ValueError:
            log.warning("Skipping invalid stage: '%s'", part)
    if not result:
        log.warning("No valid stages found, using [1]")
        return [1]
    return result
