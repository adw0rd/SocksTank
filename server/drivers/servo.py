"""Servo driver (depends on PCB and RPi version).

Based on Freenove Tank Robot Kit — servo.py.
- PCB v1 + RPi <5: pigpio (GPIO 7, 8, 25)
- PCB v1 + RPi 5:  gpiozero AngularServo (GPIO 7, 8, 25)
- PCB v2:          rpi_hardware_pwm HardwarePWM (GPIO 12, 13)
"""

import logging

from server.drivers._detect import detect_rpi_version

log = logging.getLogger(__name__)


class _PigpioServo:
    """PCB v1 + RPi <5: pigpio daemon."""

    def __init__(self):
        import pigpio

        self.pins = {0: 7, 1: 8, 2: 25}
        self.pi = pigpio.pi()
        for pin in self.pins.values():
            self.pi.set_mode(pin, pigpio.OUTPUT)
            self.pi.set_PWM_frequency(pin, 50)
            self.pi.set_PWM_range(pin, 4000)

    def setServoPwm(self, channel, angle):
        pin = self.pins.get(int(channel))
        if pin is not None:
            self.pi.set_PWM_dutycycle(pin, 80 + (400 / 180) * angle)

    def setServoStop(self, channel):
        pin = self.pins.get(int(channel))
        if pin is not None:
            self.pi.set_PWM_dutycycle(pin, 0)


class _GpiozeroServo:
    """PCB v1 + RPi 5: gpiozero AngularServo."""

    def __init__(self):
        from gpiozero import AngularServo

        min_pw = 0.5 / 1000
        max_pw = 2.5 / 1000
        self.servos = {
            0: AngularServo(7, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=min_pw, max_pulse_width=max_pw),
            1: AngularServo(8, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=min_pw, max_pulse_width=max_pw),
            2: AngularServo(25, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=min_pw, max_pulse_width=max_pw),
        }

    def setServoPwm(self, channel, angle):
        servo = self.servos.get(int(channel))
        if servo is not None:
            servo.angle = angle

    def setServoStop(self, channel):
        servo = self.servos.get(int(channel))
        if servo is not None:
            servo.angle = None


class _HardwareServo:
    """PCB v2: rpi_hardware_pwm on GPIO 12/13."""

    def __init__(self):
        from rpi_hardware_pwm import HardwarePWM

        self.pwm0 = HardwarePWM(pwm_channel=0, hz=50, chip=0)  # GPIO 12
        self.pwm1 = HardwarePWM(pwm_channel=1, hz=50, chip=0)  # GPIO 13
        self.pwm0.start(0)
        self.pwm1.start(0)

    def _angle_to_duty(self, angle):
        """0..180 deg -> 2.5..12.5% duty cycle."""
        return (angle / 180) * 10.0 + 2.5

    def setServoPwm(self, channel, angle):
        ch = int(channel)
        duty = self._angle_to_duty(angle)
        if ch == 0:
            self.pwm0.change_duty_cycle(duty)
        elif ch == 1:
            self.pwm1.change_duty_cycle(duty)

    def setServoStop(self, channel):
        ch = int(channel)
        if ch == 0:
            self.pwm0.stop()
        elif ch == 1:
            self.pwm1.stop()


class Servo:
    """Main class — selects backend by PCB and RPi version."""

    def __init__(self, pcb_version=1):
        self.pcb_version = pcb_version
        self.pi_version = detect_rpi_version()

        if pcb_version == 1 and self.pi_version == 1:
            self._pwm = _PigpioServo()
        elif pcb_version == 1 and self.pi_version == 2:
            self._pwm = _GpiozeroServo()
        else:
            # PCB v2 — HardwarePWM for any RPi
            self._pwm = _HardwareServo()

        log.info(
            "Servo: pcb_version=%d, pi_version=%d, backend=%s",
            pcb_version,
            self.pi_version,
            type(self._pwm).__name__,
        )

    def _angle_range(self, channel, angle):
        """Clamp angle per channel."""
        ch = int(channel)
        if ch == 0:
            return max(90, min(150, angle))
        elif ch == 1:
            return max(90, min(150, angle))
        elif ch == 2:
            return max(0, min(180, angle))
        return angle

    def setServoAngle(self, channel, angle):
        angle = self._angle_range(channel, int(angle))
        self._pwm.setServoPwm(str(channel), angle)

    def setServoEnabled(self, channel, enabled: bool):
        if enabled:
            return
        if hasattr(self._pwm, "setServoStop"):
            self._pwm.setServoStop(str(channel))
