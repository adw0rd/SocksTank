# Настройка Raspberry Pi 4 (legacy)

> **Примечание:** Эта документация для RPi 4B (legacy). Основной платформой является **RPi 5** — см. [rpi5.md](rpi5.md).

Руководство по подготовке Raspberry Pi 4B для работы робота-танка SocksTank.

## Требования к железу

- **Raspberry Pi 4B** (4 ГБ RAM) — legacy, для новых сборок рекомендуется **RPi 5**
- **SD-карта** 32 ГБ+ (Class 10 / A2)
- **Камера ov5647** (OmniVision) — входит в комплект Freenove Tank Kit
- **Freenove Tank Robot Kit** — собранный по инструкции из комплекта
- **Блок питания** 5V/3A (для RPi 4B) или 5V/5A (для RPi 5)

## Установка ОС

1. Скачать [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Выбрать **Raspberry Pi OS (64-bit)** — Debian bookworm
3. В настройках Imager (кнопка шестерёнки) указать:
   - Имя хоста (например, `tank`)
   - Имя пользователя и пароль
   - Настройки WiFi (SSID и пароль домашней сети)
   - Включить SSH
4. Записать образ на SD-карту
5. Вставить карту в RPi, включить питание

После загрузки подключиться по SSH:

```bash
ssh user@tank.local
# или по IP, если mDNS не работает:
ssh user@192.168.x.x
```

## Обновление системы

Перед установкой зависимостей обновить систему до актуальной версии:

```bash
sudo rm /var/lib/apt/lists/*.debian.org_*
sudo apt update
sudo apt upgrade -y
```

Без этого шага некоторые пакеты (emacs-nox, libcap-dev) могут не установиться.

## Установка зависимостей

### Системные утилиты

```bash
sudo apt install htop mc emacs-nox git screen
```

### Зависимости Freenove Tank Kit

Запустить скрипт установки из комплекта Freenove. Он установит все необходимые библиотеки и настроит тип камеры (ov5647):

```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code
sudo python setup.py
```

### Дополнительные библиотеки

Для работы светодиодов (LED):

```bash
sudo pip install rpi_ws281x --break-system-packages
```

Для работы сервоприводов (аппаратный PWM):

```bash
sudo pip install rpi-hardware-pwm --break-system-packages
```

## Настройка камеры

### Установка библиотек

```bash
sudo apt install libcap-dev python3-picamera2
```

Или через pip:

```bash
sudo pip install picamera2 --break-system-packages
```

### Конфигурация `/boot/firmware/config.txt`

Добавить в конец файла:

```ini
start_x=1
gpu_mem=512

# dtoverlay=vc4-kms-v3d
dtoverlay=cma,cma-320
dtoverlay=dmaheap,size=128M
dtoverlay=ov5647
```

После изменения — перезагрузить RPi (`sudo reboot`).

### Проверка камеры

```bash
v4l2-ctl --device /dev/video0 --all
```

Камера установлена перевёрнутой, поэтому в коде используется `Transform(vflip=True)`.

## Настройка автозапуска

При включении RPi нужно автоматически запускать демон `pigpiod` для работы с GPIO.

### Скрипт `~/start.sh`

```bash
#!/bin/sh
sleep 5
sudo pigpiod
```

### Настройка autostart

```bash
mkdir -p ~/.config/autostart
chmod +x ~/start.sh
```

Создать файл `~/.config/autostart/start.desktop`:

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

## Настройка статического IP (опционально)

Если RPi подключён по WiFi и нужен фиксированный IP:

```bash
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.addresses 192.168.x.x/24
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.gateway 192.168.x.1
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.dns "8.8.8.8"
sudo nmcli con modify "YOUR_WIFI_SSID" ipv4.method manual
sudo nmcli con up "YOUR_WIFI_SSID"
```

Заменить `YOUR_WIFI_SSID` на имя вашей WiFi-сети.

## Проверка компонентов

После установки всех зависимостей проверить работу компонентов:

```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/

# Проверка светодиодов
sudo python test.py Led

# Проверка сервоприводов (клешня, подъём)
sudo python test.py Servo

# Проверка моторов (движение)
sudo python test.py Motor
```

Если всё работает — танк готов к использованию.

## Разгон (опционально)

Разгон может повысить производительность инференса, но увеличивает нагрев. Требуется хорошее охлаждение.

Добавить в `/boot/firmware/config.txt`:

```ini
arm_freq=2147
gpu_freq=750
over_voltage=6
force_turbo=1
sdram_freq=3200
```

Перезагрузить RPi и проверить частоту:

```bash
lscpu | grep "CPU max MHz"
```

> **Важно**: без активного охлаждения (вентилятор или радиатор) разгон может привести к троттлингу и нестабильности.

## Установка ultralytics (YOLO)

```bash
pip install ultralytics[extra] --break-system-packages
```

Если после установки возникает ошибка `numpy.dtype size changed`:

```
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

Переустановить picamera2 и simplejpeg:

```bash
pip install --upgrade picamera2 simplejpeg --break-system-packages
```

## VNC-доступ (опционально)

Для удалённого доступа к рабочему столу RPi:

1. Включить VNC через `raspi-config`:
   ```bash
   sudo raspi-config
   # Interface Options → VNC → Enable
   ```
2. На RPi 5 используется **WayVNC** (Wayland). На RPi 4B — **RealVNC**
3. Подключиться с компьютера через [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/)

---

Следующий шаг: [Подготовка датасета](dataset.md)
