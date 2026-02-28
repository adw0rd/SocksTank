"""Auto-detect Raspberry Pi version."""

import logging

log = logging.getLogger(__name__)


def detect_rpi_version() -> int:
    """Detect RPi version: 2 for RPi 5+, 1 for others.

    Reads /sys/firmware/devicetree/base/model.
    Returns 1 if file is not accessible (not an RPi).
    """
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            model = f.read().strip("\x00").strip()
        if "Raspberry Pi 5" in model:
            log.info("Detected Raspberry Pi 5 (pi_version=2)")
            return 2
        log.info("Detected %s (pi_version=1)", model)
        return 1
    except (FileNotFoundError, PermissionError):
        log.debug("Cannot read /sys/firmware/devicetree/base/model — not an RPi")
        return 1
