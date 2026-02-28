"""LED strip driver (depends on PCB and RPi version).

Based on Freenove Tank Robot Kit — led.py, rpi_ledpixel.py, spi_ledpixel.py.
- PCB v1 + RPi <5: rpi_ws281x (GPIO 18, 4 LEDs, RGB)
- PCB v1 + RPi 5:  noop + warning (not supported in hardware)
- PCB v2:          SPI LED (spidev, 4 LEDs, GRB)
"""

import time
import logging

from server.drivers._detect import detect_rpi_version

log = logging.getLogger(__name__)

LED_COUNT = 4


class _RpiWs281xStrip:
    """LED via rpi_ws281x (PCB v1 + RPi <5)."""

    def __init__(self):
        from rpi_ws281x import Adafruit_NeoPixel, Color

        self._Color = Color
        self.led_count = LED_COUNT
        self._brightness = 255
        self._colors = [(0, 0, 0)] * self.led_count
        self.strip = Adafruit_NeoPixel(self.led_count, 18, 800000, 10, False, self._brightness, 0)
        self.strip.begin()

    def get_led_count(self):
        return self.led_count

    def set_led_rgb_data(self, index, color):
        if 0 <= index < self.led_count:
            self._colors[index] = (color[0], color[1], color[2])

    def show(self):
        for i, (r, g, b) in enumerate(self._colors):
            self.strip.setPixelColor(i, self._Color(r, g, b))
        self.strip.show()


class _SpiStrip:
    """LED via SPI (PCB v2)."""

    def __init__(self):
        import spidev
        import numpy

        self._numpy = numpy
        self.led_count = LED_COUNT
        self._brightness = 255
        # GRB order
        self._red_offset = 1
        self._green_offset = 0
        self._blue_offset = 2
        self._colors = [0] * (self.led_count * 3)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.mode = 0

    def get_led_count(self):
        return self.led_count

    def set_led_rgb_data(self, index, color):
        if 0 <= index < self.led_count:
            r, g, b = color[0], color[1], color[2]
            base = index * 3
            self._colors[base + self._red_offset] = round(r * self._brightness / 255)
            self._colors[base + self._green_offset] = round(g * self._brightness / 255)
            self._colors[base + self._blue_offset] = round(b * self._brightness / 255)

    def show(self):
        numpy = self._numpy
        d = numpy.array(self._colors).ravel()
        tx = numpy.zeros(len(d) * 8, dtype=numpy.uint8)
        for ibit in range(8):
            tx[7 - ibit :: 8] = ((d >> ibit) & 1) * 0x78 + 0x80  # noqa: E203
        self.spi.xfer(tx.tolist(), int(8 / 1.25e-6))


class _NoopStrip:
    """Noop stub for PCB v1 + RPi 5 (LED not supported)."""

    def __init__(self):
        self.led_count = LED_COUNT

    def get_led_count(self):
        return self.led_count

    def set_led_rgb_data(self, index, color):
        pass

    def show(self):
        pass


class Led:
    def __init__(self, pcb_version=1):
        pi_version = detect_rpi_version()

        if pcb_version == 1 and pi_version == 1:
            self.strip = _RpiWs281xStrip()
            self._supported = True
        elif pcb_version == 2:
            self.strip = _SpiStrip()
            self._supported = True
        else:
            # PCB v1 + RPi 5
            log.warning("PCB v1 + RPi 5: LED not supported (rpi_ws281x incompatible)")
            self.strip = _NoopStrip()
            self._supported = False

        self._breathe_brightness = 0
        self._breathe_flag = 0
        self._breathe_time = time.time()

    def colorWipe(self, color, wait_ms=50):
        """Wipe color across display a pixel at a time."""
        if not self._supported:
            return
        for i in range(self.strip.get_led_count()):
            self.strip.set_led_rgb_data(i, color)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def Breathing(self, data, wait_ms=5):
        """Breathing brightness effect."""
        if not self._supported:
            return
        now = time.time()
        if now - self._breathe_time > wait_ms / 1000.0:
            self._breathe_time = now
            if self._breathe_flag == 0:
                self._breathe_brightness += 1
                if self._breathe_brightness >= 255:
                    self._breathe_flag = 1
            else:
                self._breathe_brightness -= 1
                if self._breathe_brightness <= 0:
                    self._breathe_flag = 0
            b = self._breathe_brightness
            for i in range(self.strip.get_led_count()):
                self.strip.set_led_rgb_data(i, (int(data[0] * b / 255), int(data[1] * b / 255), int(data[2] * b / 255)))
            self.strip.show()

    def _wheel(self, pos):
        """Rainbow color generator (0..255)."""
        if pos < 0 or pos > 255:
            return (0, 0, 0)
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        if pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

    def rainbow(self, wait_ms=20, iterations=1):
        """Rainbow effect across all pixels."""
        if not self._supported:
            return
        for j in range(256 * iterations):
            for i in range(self.strip.get_led_count()):
                self.strip.set_led_rgb_data(i, self._wheel((i + j) & 255))
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def ledIndex(self, index, R, G, B):
        """Set color of specific LEDs by bitmask."""
        if not self._supported:
            return
        color = (R, G, B)
        for i in range(LED_COUNT):
            if index & 0x01 == 1:
                self.strip.set_led_rgb_data(i, color)
                self.strip.show()
            index >>= 1
