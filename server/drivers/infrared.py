"""Infrared sensor driver (depends on PCB version).

Based on Freenove Tank Robot Kit — infrared.py.
- PCB v1: GPIO 16, 20, 21
- PCB v2: GPIO 16, 26, 21
"""

from gpiozero import LineSensor


class Infrared:
    def __init__(self, pcb_version=1):
        if pcb_version == 1:
            pins = (16, 20, 21)
        else:
            pins = (16, 26, 21)

        self._sensors = [LineSensor(p) for p in pins]

    def read_one_infrared(self, channel):
        """Read one sensor (1-indexed). Returns 0 or 1."""
        idx = channel - 1
        if 0 <= idx < len(self._sensors):
            return 1 if self._sensors[idx].value else 0
        return 0

    def read_all_infrared(self):
        """Combined value of all sensors (bitmask)."""
        return (self.read_one_infrared(1) << 2) | (self.read_one_infrared(2) << 1) | self.read_one_infrared(3)

    def close(self):
        for s in self._sensors:
            s.close()
