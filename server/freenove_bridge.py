"""Импорт модулей Freenove с fallback на mock для macOS."""

import sys
import os
import logging

from server.config import settings

log = logging.getLogger(__name__)


def _try_import_freenove():
    """Попытка импортировать модули Freenove через sys.path."""
    path = os.path.expanduser(settings.freenove_path)
    if not os.path.isdir(path):
        log.warning("Freenove путь не найден: %s — используем mock", path)
        return None

    if path not in sys.path:
        sys.path.insert(0, path)

    try:
        from motor import tankMotor
        from servo import Servo
        from led import Led
        from ultrasonic import Ultrasonic
        from infrared import Infrared

        log.info("Freenove модули загружены из %s", path)
        return {
            "motor": tankMotor,
            "servo": Servo,
            "led": Led,
            "ultrasonic": Ultrasonic,
            "infrared": Infrared,
        }
    except ImportError as e:
        log.warning("Не удалось импортировать Freenove: %s — используем mock", e)
        return None


def _get_mock_modules():
    """Возвращает mock-классы."""
    from server.mock import MockMotor, MockServo, MockLed, MockUltrasonic, MockInfrared

    return {
        "motor": MockMotor,
        "servo": MockServo,
        "led": MockLed,
        "ultrasonic": MockUltrasonic,
        "infrared": MockInfrared,
    }


def load_hardware_modules():
    """Загружает Freenove модули или mock-заглушки."""
    if settings.mock:
        log.info("Mock-режим включён")
        return _get_mock_modules()

    modules = _try_import_freenove()
    if modules is None:
        log.info("Fallback на mock-модули")
        return _get_mock_modules()
    return modules


def load_camera():
    """Загружает Picamera2 или mock-камеру."""
    if settings.mock:
        from server.mock import MockPicamera2

        log.info("Используем MockPicamera2")
        return MockPicamera2()

    try:
        from picamera2 import Picamera2
        from libcamera import Transform

        cam = Picamera2()
        config = cam.create_preview_configuration(
            main={"size": (settings.resolution_w, settings.resolution_h), "format": "RGB888"},
            transform=Transform(vflip=True),
        )
        cam.configure(config)
        log.info("Picamera2 настроена: %dx%d", settings.resolution_w, settings.resolution_h)
        return cam
    except (ImportError, RuntimeError) as e:
        log.warning("Picamera2 недоступна: %s — используем mock", e)
        from server.mock import MockPicamera2

        return MockPicamera2()
