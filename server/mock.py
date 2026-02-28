"""Mock classes for development on macOS without GPIO or a camera."""

import time
import random
import numpy as np


class MockMotor:
    """Mock implementation of tankMotor."""

    def __init__(self):
        self.left = 0
        self.right = 0

    def setMotorModel(self, left, right):
        self.left = left
        self.right = right

    def close(self):
        pass


class MockServo:
    """Mock implementation of Servo."""

    def __init__(self):
        self.angles = {0: 90, 1: 140, 2: 90}

    def setServoAngle(self, channel, angle):
        self.angles[channel] = angle


class MockLed:
    """Mock implementation of Led."""

    def __init__(self):
        self.color = (0, 0, 0)

    def colorWipe(self, color, wait_ms=0):
        self.color = color

    def Breathing(self, color, wait_ms=0):
        pass

    def rainbow(self, wait_ms=20, iterations=1):
        pass

    def rainbowCycle(self, wait_ms=20, iterations=1):
        pass

    def ledIndex(self, index, r, g, b):
        pass


class MockUltrasonic:
    """Mock ultrasonic sensor that returns a random distance."""

    def get_distance(self):
        return round(random.uniform(10, 200), 1)

    def close(self):
        pass


class MockInfrared:
    """Mock infrared sensor that returns random values."""

    def read_all_infrared(self):
        return random.randint(0, 7)

    def read_one_infrared(self, channel):
        return random.randint(0, 1)

    def close(self):
        pass


class MockPicamera2:
    """Mock Picamera2 that generates test frames for macOS development."""

    is_mock = True

    def __init__(self):
        self._running = False
        self._size = (640, 480)

    def configure(self, config):
        pass

    def create_preview_configuration(self, main=None, transform=None):
        if main and "size" in main:
            self._size = main["size"]
        return {}

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def capture_array(self):
        import cv2

        w, h = self._size
        frame = np.random.randint(40, 80, (h, w, 3), dtype=np.uint8)
        cv2.putText(frame, "MOCK - deploy to RPi", (w // 2 - 160, h // 2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        ts = time.strftime("%H:%M:%S")
        cv2.putText(frame, ts, (w // 2 - 55, h // 2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return frame

    def close(self):
        self.stop()
