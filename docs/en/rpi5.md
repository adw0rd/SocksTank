# Raspberry Pi 5 Setup

Guide for preparing RPi 5 for the SocksTank robot.

## Specifications

| Parameter | Value |
|---|---|
| Model | Raspberry Pi 5 Model B Rev 1.0 |
| SoC | BCM2712 (Cortex-A76) |
| CPU | 4 cores, 1.5-2.4 GHz |
| RAM | 8 GB |
| OS | Raspbian GNU/Linux 12 (bookworm) |
| Kernel | 6.12.25+rpt-rpi-v8 aarch64 |
| Python | 3.11.2 (**32-bit armhf**, kernel is 64-bit) |
| Disk | microSD 119.1 GB (15 GB partition) |
| Revision | d04170 |
| Serial | 9aad3f08b599e338 |
| IP | 192.168.0.158 (static) |

## Differences from RPi 4 (legacy)

| | RPi 4 Model B | RPi 5 Model B |
|---|---|---|
| CPU | Cortex-A72 1.8 GHz | Cortex-A76 2.4 GHz |
| RAM | 3.3 GB | 8 GB |
| OS | Debian 64-bit | Raspbian 32-bit* |
| Python | 64-bit (aarch64) | 32-bit (armhf) |
| PyTorch | ✅ (pip install) | ❌ (no wheel for armv7l) |
| onnxruntime | ✅ (pip install) | ❌ (no wheel for armv7l) |
| ncnn | ✅ | ✅ |
| Power | 5V/3A (USB-C) | **5V/5A** (USB PD) |
| pigpiod | Required | Not required |
| Camera | cam0 (15-pin CSI) | cam0 or cam1 (22-pin FPC) |
| Disk (write) | 60.7 MB/s (USB SanDisk) | 64.3 MB/s (microSD) |
| Disk (read) | 151 MB/s (USB SanDisk) | 90.6 MB/s (microSD) |

> *Recommended: reinstall 64-bit Raspberry Pi OS for full PyTorch/onnxruntime compatibility.

## Power Issue

RPi 5 draws significantly more power than RPi 4. The Freenove Tank Board DC/DC converter is rated for RPi 3/4 (~2-3A max).

Detailed measurements: [../rpi5-power.md](../rpi5-power.md)

### Solution: LM2596 DC-DC Buck Converter

```
Batteries (2x18650, 7.4V) → LM2596 → 5.1V/3A → RPi 5 GPIO (5V + GND)
```

Set output to **5.1V**. Verify: `vcgencmd pmic_read_adc | grep EXT5V` → >5.0V.

## config.txt

Added parameters for SocksTank:

```ini
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
dtoverlay=ov5647
usb_max_current_enable=1
psu_max_current=5000
```

Full config: [../rpi5-config.txt](../rpi5-config.txt)

## Installed Packages

```
Python 3.11.2 (armhf 32-bit)
numpy 1.26.4, cv2 4.6.0, ncnn 1.0.20260114
ultralytics 8.4.16 (--no-deps, cannot import without torch)
matplotlib 3.10.8, pandas 3.0.1, scipy 1.17.1, Pillow 9.4.0
```

**Not available** (no armv7l wheels): torch, torchvision, onnxruntime

## TODO

- [ ] Reinstall 64-bit Raspberry Pi OS
- [ ] Install LM2596 DC-DC converter for stable power
- [ ] Benchmark YOLO inference (NCNN, PyTorch, ONNX)
- [ ] Connect camera (22→15 pin cable ordered)
- [ ] Test SocksTank serve
