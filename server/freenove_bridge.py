"""Load hardware drivers: real (server.drivers) or mock."""

import logging

from server.config import settings

log = logging.getLogger(__name__)


def _try_import_drivers():
    """Try to import real drivers from server.drivers."""
    try:
        from server.drivers.motor import tankMotor
        from server.drivers.servo import Servo
        from server.drivers.led import Led
        from server.drivers.ultrasonic import Ultrasonic
        from server.drivers.infrared import Infrared

        pcb = settings.pcb_version

        log.info("Drivers loaded (pcb_version=%d)", pcb)
        return {
            "motor": tankMotor,
            "servo": lambda: Servo(pcb_version=pcb),
            "led": lambda: Led(pcb_version=pcb),
            "ultrasonic": Ultrasonic,
            "infrared": lambda: Infrared(pcb_version=pcb),
        }
    except ImportError as e:
        log.warning("Failed to import drivers: %s — falling back to mock", e)
        return None


def _get_mock_modules():
    """Return mock classes."""
    from server.mock import MockMotor, MockServo, MockLed, MockUltrasonic, MockInfrared

    return {
        "motor": MockMotor,
        "servo": MockServo,
        "led": MockLed,
        "ultrasonic": MockUltrasonic,
        "infrared": MockInfrared,
    }


def load_hardware_modules():
    """Load hardware drivers or mock stubs."""
    if settings.mock:
        log.info("Mock mode enabled")
        return _get_mock_modules()

    modules = _try_import_drivers()
    if modules is None:
        log.info("Falling back to mock modules")
        return _get_mock_modules()
    return modules


def load_camera():
    """Load Picamera2 or mock camera."""
    if settings.mock:
        from server.mock import MockPicamera2

        log.info("Using MockPicamera2")
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
        log.info("Picamera2 configured: %dx%d", settings.resolution_w, settings.resolution_h)
        return cam
    except (ImportError, RuntimeError) as e:
        log.warning("Picamera2 unavailable: %s — falling back to mock", e)
        from server.mock import MockPicamera2

        return MockPicamera2()
