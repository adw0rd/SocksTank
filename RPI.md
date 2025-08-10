## Обновление до deb12u1-u3

Иначе не установится emacs-nox, libcap-dev.

```
sudo rm /var/lib/apt/lists/*.debian.org_*
sudo apt update
sudo apt upgrade -y
```

# Установка

Установка тулзов:

```
sudo apt install htop mc emacs-nox git screen
```

Можно установить сразу все зависимости, установить тип камеры (у меня "ov5647", подробнее в Tutorial.pdf):

<img width="691" height="343" alt="image" src="https://github.com/user-attachments/assets/92a97d1a-6de4-4354-aee3-20511d304f79" />


```
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code
sudo python setup.py
```

Чтобы работал Led нужно доустановить `rpi_ws281x`:

```
sudo pip install rpi_ws281x --break-system-packages
```

Чтобы работал Servo нужно доустановить `rpi-hardware-pwm`:

```
sudo pip install rpi-hardware-pwm --break-system-packages
```

# Автозапуск

Описываем `~/start.sh`:

```
#!/bin/sh
sleep 5
sudo pigpiod

# cd "/home/zeus/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server"
# pwd
# sleep 10
# sudo python main.py
```

Создаем каталог и файл автозапуска:

```
mkdir ~/.config/autostart/
touch ~/.config/autostart/start.desktop
chmod +x ~/.config/autostart/start.desktop
chmod +x ~/start.sh
```

И добавляем его в автозапуск `~/.config/autostart/start.desktop`:

```
[Desktop Entry]
Type=Application
Name=start
NoDisplay=true
Exec=/home/zeus/start.sh
```

## Камера

Camera info, drivers:
```
v4l2-ctl --device /dev/video0 --all
```

```
sudo apt install libcap-dev
sudo apt install python3-picamera2
# OR
sudo pip install picamera2 --break-system-packages
```

Добавить запуск иксов и камеры в `/boot/firmware/config.txt`:

```
start_x=1
gpu_mem=512

# dtoverlay=vc4-kms-v3d
dtoverlay=cma,cma-320
dtoverlay=dmaheap,size=128M
# dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
dtoverlay=ov5647
```

## Разгон

Before

```
# lscpu |grep CPU
CPU(s):                                  4
On-line CPU(s) list:                     0-3
CPU(s) scaling MHz:                      100%
CPU max MHz:                             2200.0000
CPU min MHz:                             2200.0000
NUMA node0 CPU(s):                       0-3
```

```
emacs /boot/firmware/config.txt
arm_freq=2147
gpu_freq=750
over_voltage=6
force_turbo=1
gpu_mem=512
sdram_freq=3200
```

After

```
CPU op-mode(s):                       32-bit, 64-bit
CPU(s):                               4
On-line CPU(s) list:                  0-3
CPU(s) scaling MHz:                   100%
CPU max MHz:                          2200.0000
CPU min MHz:                          2200.0000
NUMA node0 CPU(s):                    0-3
```


## Проверка

```
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server/
sudo python test.py Led
sudo python test.py Servo
sudo python test.py Motor
```


## Установка ultralytics/YOLO

```
pip install ultralytics[extra] --break-system-packages
```

Если после установки `ultralytics` возникла ошибка:

```
  File "simplejpeg/_jpeg.pyx", line 1, in init simplejpeg._jpeg
ValueError: numpy.dtype size changed, may indicate binary incompatibility. Expected 96 from C header, got 88 from PyObject
```

Поможет переустановка picamera2 и simplejpeg:

```
pip install --upgrade picamera2 simplejpeg --break-system-packages
```
