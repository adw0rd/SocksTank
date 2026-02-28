# Raspberry Pi 4 Setup (legacy)

> **Note:** RPi 4B is a legacy platform. The primary platform is **RPi 5** — see [rpi5.md](rpi5.md).
>
> Reason for migration: RPi 4 is too slow for real-time detection. YOLO inference on RPi 4: **2.4 FPS** (NCNN, 1 thread) vs **14.9 FPS** on RPi 5 (pip ncnn native, 4 OMP threads, with preprocessing) — more than a **6x** difference. PyTorch is even worse: 1.1 FPS. The sock-finding task requires at least 10 FPS, which RPi 4 cannot deliver.

Guide for preparing a Raspberry Pi 4B to run the SocksTank robot.

## Hardware requirements

- **Raspberry Pi 4B** (4 GB RAM) — legacy, for new builds **RPi 5** is recommended
- **SD card** 32 GB+ (Class 10 / A2)
- **ov5647 camera** (OmniVision) — included in the Freenove Tank Kit
- **[Freenove Tank Robot Kit](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi)** — assembled following the [included instructions](https://github.com/adw0rd/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/blob/main/Tutorial.pdf)
- **Power supply** 5V/3A (for RPi 4B) or 5V/5A (for RPi 5)

## OS installation

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select **Raspberry Pi OS (64-bit)** — Debian bookworm
3. In Imager settings (gear icon) configure:
   - Hostname (e.g., `tank`)
   - Username and password
   - WiFi settings (SSID and password)
   - Enable SSH
4. Flash the image to the SD card
5. Insert the card into RPi and power on

Connect via SSH after boot:

```bash
ssh user@tank.local
# or by IP if mDNS doesn't work:
ssh user@192.168.x.x
```

## System update

Update the system before installing dependencies:

```bash
sudo rm /var/lib/apt/lists/*.debian.org_*
sudo apt update
sudo apt upgrade -y
```

Without this step some packages (emacs-nox, libcap-dev) may fail to install.

## Installing dependencies

### System utilities

```bash
sudo apt install htop mc emacs-nox git screen
```

### Freenove Tank Kit dependencies

Run the setup script from the Freenove kit. It installs all required libraries and configures the camera type (ov5647):

```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code
sudo python setup.py
```

### Additional libraries

For LED support:

```bash
sudo pip install rpi_ws281x --break-system-packages
```

For servo support (hardware PWM):

```bash
sudo pip install rpi-hardware-pwm --break-system-packages
```

## Camera setup

### Installing libraries

```bash
sudo apt install libcap-dev python3-picamera2
```

Or via pip:

```bash
sudo pip install picamera2 --break-system-packages
```

### Configuring `/boot/firmware/config.txt`

Add to the end of the file:

```ini
start_x=1
gpu_mem=512

# dtoverlay=vc4-kms-v3d
dtoverlay=cma,cma-320
dtoverlay=dmaheap,size=128M
dtoverlay=ov5647
```

Reboot the RPi after changes (`sudo reboot`).

### Verifying the camera

```bash
v4l2-ctl --device /dev/video0 --all
```

The camera is mounted upside down, so `Transform(vflip=True)` is used in the code.

## Autostart setup

The `pigpiod` daemon must start automatically on boot for GPIO access.

### Script `~/start.sh`

```bash
#!/bin/sh
sleep 5
sudo pigpiod
```

### Configuring autostart

```bash
mkdir -p ~/.config/autostart
chmod +x ~/start.sh
```

Create file `~/.config/autostart/start.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=start
NoDisplay=true
Exec=/home/user/start.sh
```

```bash
chmod +x ~/.config/autostart/start.desktop
```

## Static IP (optional)

If the RPi is connected via WiFi and you need a fixed IP:

```bash
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.addresses 192.168.x.x/24
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.gateway 192.168.x.1
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.dns "8.8.8.8"
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.method manual
sudo nmcli con up "YOUR_WIFI_SSID"
```

Replace `YOUR_WIFI_SSID` with your WiFi network name.

## Verifying components

After installing all dependencies, verify that components work:

```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/

# Test LEDs
sudo python test.py Led

# Test servos (claw, lift)
sudo python test.py Servo

# Test motors (movement)
sudo python test.py Motor
```

If everything works — the tank is ready.

## Overclocking (optional)

Overclocking can improve inference performance but increases heat. Good cooling is required.

Add to `/boot/firmware/config.txt`:

```ini
arm_freq=2147
gpu_freq=750
over_voltage=6
force_turbo=1
sdram_freq=3200
```

Reboot and verify the frequency:

```bash
lscpu | grep "CPU max MHz"
```

> **Warning**: without active cooling (fan or heatsink) overclocking may cause throttling and instability.

## Installing ultralytics (YOLO)

```bash
pip install ultralytics[extra] --break-system-packages
```

If you get a `numpy.dtype size changed` error after installation:

```
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

Reinstall picamera2 and simplejpeg:

```bash
pip install --upgrade picamera2 simplejpeg --break-system-packages
```

## VNC access (optional)

For remote desktop access to the RPi:

1. Enable VNC via `raspi-config`:
   ```bash
   sudo raspi-config
   # Interface Options → VNC → Enable
   ```
2. Connect from your computer using [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/)

---

Next step: [Dataset preparation](dataset.md)
