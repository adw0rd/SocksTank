"""Tank motor driver (same for PCB v1 and v2).

Based on Freenove Tank Robot Kit — motor.py.
GPIO: left motor (24, 23), right motor (5, 6).
"""

from gpiozero import Motor


class tankMotor:
    def __init__(self):
        self.left_motor = Motor(24, 23)
        self.right_motor = Motor(5, 6)

    def _clamp(self, duty):
        """Clamp duty to -4095..4095 range."""
        return max(-4095, min(4095, duty))

    def setMotorModel(self, duty1, duty2):
        """Set motor speed. Range: -4095..4095."""
        duty1 = self._clamp(duty1)
        duty2 = self._clamp(duty2)
        # Left motor
        if duty1 > 0:
            self.left_motor.forward(duty1 / 4096)
        elif duty1 < 0:
            self.left_motor.backward(-duty1 / 4096)
        else:
            self.left_motor.stop()
        # Right motor
        if duty2 > 0:
            self.right_motor.forward(duty2 / 4096)
        elif duty2 < 0:
            self.right_motor.backward(-duty2 / 4096)
        else:
            self.right_motor.stop()

    def close(self):
        self.left_motor.close()
        self.right_motor.close()
