"""Thread-safe HardwareController wrapper around Freenove modules."""

import subprocess
import threading
import logging

from server.freenove_bridge import load_hardware_modules
from server.config import settings

log = logging.getLogger(__name__)


class HardwareController:
    """Control motors, servos, LEDs, and sensors."""

    def __init__(self):
        modules = load_hardware_modules()
        self._motor = modules["motor"]()
        self._servo = modules["servo"]()
        self._led = modules["led"]()
        self._ultrasonic = modules["ultrasonic"]()
        self._infrared = modules["infrared"]()
        self._lock = threading.Lock()
        self._mode = "manual"
        self._motor_left = 0
        self._motor_right = 0
        log.info("HardwareController initialized")

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        self._mode = value

    @property
    def motor_left(self) -> int:
        return self._motor_left

    @property
    def motor_right(self) -> int:
        return self._motor_right

    def set_motor(self, left: int, right: int):
        """Set motor speed. Valid range: -4095..4095."""
        left = max(-4095, min(4095, int(left)))
        right = max(-4095, min(4095, int(right)))
        with self._lock:
            self._motor_left = left
            self._motor_right = right
            self._motor.setMotorModel(left, right)

    def stop_motors(self):
        """Stop both motors immediately."""
        self.set_motor(0, 0)

    def set_servo(self, channel: int, angle: int):
        """Set the servo angle."""
        channel = max(0, min(2, channel))
        angle = max(0, min(180, angle))
        with self._lock:
            self._servo.setServoAngle(channel, angle)

    def set_led(self, r: int, g: int, b: int):
        """Set the color of all LEDs."""
        with self._lock:
            self._led.colorWipe([r, g, b])

    def led_effect(self, effect: str):
        """Run a predefined LED effect."""
        with self._lock:
            if effect == "rainbow":
                self._led.rainbow()
            elif effect == "breathing":
                self._led.Breathing([0, 100, 255])
            elif effect == "off":
                self._led.colorWipe([0, 0, 0])

    def get_distance(self) -> float:
        """Get the ultrasonic sensor distance in centimeters."""
        with self._lock:
            return self._ultrasonic.get_distance()

    def get_infrared(self) -> list[int]:
        """Get infrared sensor states as [IR1, IR2, IR3]."""
        with self._lock:
            val = self._infrared.read_all_infrared()
        return [(val >> 2) & 1, (val >> 1) & 1, val & 1]

    def get_cpu_temp(self) -> float:
        """Return the Raspberry Pi CPU temperature in Celsius."""
        if settings.mock:
            return 42.0
        try:
            out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
            # "temp=48.3'C\n"
            return float(out.split("=")[1].split("'")[0])
        except Exception:
            return 0.0

    def stop_all(self):
        """Stop all controllable subsystems."""
        self.stop_motors()
        self.set_led(0, 0, 0)
        log.info("All systems stopped")

    def close(self):
        """Release hardware resources."""
        self.stop_all()
        try:
            self._motor.close()
        except Exception:
            pass
        try:
            self._ultrasonic.close()
        except Exception:
            pass
        try:
            self._infrared.close()
        except Exception:
            pass
        log.info("HardwareController closed")
