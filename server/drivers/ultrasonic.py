"""Ultrasonic sensor driver (same for PCB v1 and v2).

Based on Freenove Tank Robot Kit — ultrasonic.py.
GPIO: trigger=27, echo=22.
"""

import warnings

from gpiozero import DistanceSensor, PWMSoftwareFallback


class Ultrasonic:
    def __init__(self):
        warnings.filterwarnings("ignore", category=PWMSoftwareFallback)
        self.sensor = DistanceSensor(echo=22, trigger=27, max_distance=3)

    def get_distance(self):
        """Distance in centimeters (rounded to 0.1 cm)."""
        return round(float(self.sensor.distance * 100), 1)

    def close(self):
        self.sensor.close()
