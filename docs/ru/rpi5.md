# Настройка Raspberry Pi 5

Руководство по подготовке RPi 5 для работы робота-танка SocksTank.

## Характеристики

| Параметр | Значение |
|---|---|
| Модель | Raspberry Pi 5 Model B Rev 1.0 |
| SoC | BCM2712 (Cortex-A76) |
| CPU | 4 ядра, 1.5-2.4 GHz |
| RAM | 8 GB |
| ОС | Debian GNU/Linux 13 (trixie) **64-bit** |
| Ядро | 6.12.62+rpt-rpi-2712 aarch64 |
| Python | 3.13.5 (aarch64 **64-bit**) |
| Диск | microSD 117 GB |
| Revision | d04170 |
| IP | 192.168.0.158 (DHCP, hostname rpi5) |

## Отличия от RPi 4 (legacy)

| | RPi 4 Model B | RPi 5 Model B |
|---|---|---|
| CPU | Cortex-A72 1.8 GHz | Cortex-A76 2.4 GHz |
| RAM | 3.3 GB | 8 GB |
| ОС | Debian 12 bookworm 64-bit | Debian 13 trixie 64-bit |
| Python | 3.11.2 (aarch64) | 3.13.5 (aarch64) |
| PyTorch | ✅ 2.8.0+cpu | ✅ 2.10.0+cpu |
| onnxruntime | ✅ 1.24.2 | ✅ 1.24.2 |
| ncnn | ✅ | ✅ 1.0.20260114 |
| Питание | 5V/3A (USB-C) | **5V/5A** (USB PD) |
| pigpiod | Требуется | Не требуется |
| Камера | cam0 (15-pin CSI) | cam0 или cam1 (22-pin FPC) |
| Диск (запись) | 60.7 MB/s (USB SanDisk) | 64.3 MB/s (microSD) |
| Диск (чтение) | 151 MB/s (USB SanDisk) | 90.6 MB/s (microSD) |
| YOLO FPS (NCNN) | 2.4 FPS (1 поток) | **14.9 FPS** (4 OMP потока, с preproc) |

## Питание

RPi 5 потребляет значительно больше энергии, чем RPi 4. Freenove Tank Board DC/DC не справляется.

Решение: **XL6019E1** buck-boost конвертер (2x18650 → 5.2V → GPIO) + конденсаторы + [плавный старт](rpi5-power.md#плавный-старт-cpu-warmup).

Подробные замеры, сравнение конвертеров, схема подключения и рекомендации: **[rpi5-power.md](rpi5-power.md)**

## Охлаждение

Рекомендуется **RPi 5 Active Cooler** — алюминиевый радиатор с PWM-вентилятором, подключается к разъёму FAN на плате RPi 5. Скорость вентилятора управляется автоматически по температуре.

Температура при нагрузке (YOLO инференс 4 ядра): 38→47°C (XL6019E1), 37→60°C (LM2596). Throttled=0x0.

У оригинала есть логотип Raspberry Pi, копии функционально идентичны.

Альтернатива: **Argon THRML 30 mm**-подобный blower-кулер для Raspberry Pi 5. Он компактнее по высоте и может быть удобен, если внутри корпуса мало места. Это пока не основная рекомендация, но как низкопрофильный вариант выглядит перспективно для тестов.

![Argon THRML 30 mm style cooler](../../assets/cooler-argon-thrml.jpg)

![Active Cooler установлен на RPi 5](../../assets/cooler-installed.jpg)

![Оригинальный Active Cooler (логотип Raspberry Pi)](../../assets/cooler-original.jpg)

![Клон Active Cooler с термопрокладками](../../assets/cooler-clone.jpg)

Где купить:
- Ozon (оригинал): [кейс + кулер](https://ozon.ru/t/6dwBhuE), [кулер](https://ozon.ru/t/hoNZF6l)
- Ozon (копии): [вариант 1](https://ozon.ru/t/hoNZFqO), [вариант 2](https://ozon.ru/t/6dwBNmn)
- AliExpress: [пример](https://ali.click/b7k211d). Искать: «Raspberry Pi 5 active cooler» или «RPi 5 heatsink fan PWM»
- Ozon (низкопрофильная альтернатива): [Argon THRML 30 mm style cooler](https://ozon.ru/t/DukWou1)
- AliExpress (низкопрофильная альтернатива): [Argon THRML 30 mm style cooler](https://ali.click/uae311m)

## Установка ОС

Использовать **Raspberry Pi OS Lite (64-bit)** через Raspberry Pi Imager:
- OS: Raspberry Pi OS (other) → Raspberry Pi OS Lite (64-bit)
- Hostname: rpi5
- Username: zeus
- Wi-Fi + SSH: включить

## Сеть

Используется **DHCP** (ipv4.method: auto) + hostname `rpi5`. Статический IP не нужен — доступ по hostname через mDNS (avahi):

```bash
ssh rpi5            # вместо ssh 192.168.0.xxx
http://rpi5:8080    # веб-панель
```

Если mDNS не работает (Windows без Bonjour, или другая сеть), можно настроить статический IP:

```bash
sudo nmcli con modify "netplan-wlan0-YOUR_SSID" ipv4.addresses 192.168.0.158/24
sudo nmcli con modify "netplan-wlan0-YOUR_SSID" ipv4.gateway 192.168.0.1
sudo nmcli con modify "netplan-wlan0-YOUR_SSID" ipv4.dns "8.8.8.8"
sudo nmcli con modify "netplan-wlan0-YOUR_SSID" ipv4.method manual
sudo nmcli con up "netplan-wlan0-YOUR_SSID"
```

## Установленные пакеты

```
Python 3.13.5 (aarch64 64-bit)
torch 2.10.0+cpu
torchvision 0.25.0
ultralytics 8.4.16
cv2 4.13.0 (opencv-python-headless)
numpy 2.4.2
ncnn 1.0.20260114
onnxruntime 1.24.2
matplotlib 3.10.8
scipy 1.17.1
polars 1.38.1
```

## config.txt

Файл: `/boot/firmware/config.txt`

Необходимо добавить для SocksTank:

```ini
# PWM для сервоприводов Freenove Tank Board
dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4

# Камера OV5647
dtoverlay=ov5647

# Питание через GPIO от Freenove Tank Board
usb_max_current_enable=1
psu_max_current=5000
```

### Отличие от RPi 4 (legacy)

- **pigpiod** не нужен на RPi 5 (используется встроенный GPIO)
- **Камера**: на RPi 5 разъёмы cam0/cam1 с 22-pin FPC (не 15-pin CSI как на RPi 4). Необходим [кабель 22→15 pin](https://ozon.ru/t/lwESi2D) или [переходник 22-to-15](https://ozon.ru/t/EAxTi6d). На AliExpress искать: «Raspberry Pi 5 camera cable 22pin to 15pin» или «RPi 5 CSI FPC adapter 22 15».
- **LED (PCB v1)**: встроенные RGB-светодиоды на оригинальной плате PCB v1 не поддерживаются на RPi 5. Там несовместим `rpi_ws281x`, поэтому LED-управление в UI специально отключено. На RPi 4 LED работают, и на PCB v2 они тоже работают через SPI.

## Бенчмарки

Ключевые цифры (YOLOv11n, pip ncnn native + OMP workaround):

| Конфигурация | FPS | vs RPi 4 |
|---|---|---|
| 4 OMP потока (чистый инференс) | **15.8** | 14.4x |
| 4 OMP потока (с preproc) | **14.9** | 13.5x |
| XL6019E1, 4 ядра (автономное) | **11.2** | 10.2x |
| LM2596, 2 ядра (автономное) | **11.1** | 10.1x |

Диск: запись 73.5 MB/s, чтение 94.5 MB/s (microSD).

Подробные замеры по всем форматам, источникам питания, INT8 и температурам: **[benchmarks.md](benchmarks.md)**, **[disk-benchmarks.md](disk-benchmarks.md)**
