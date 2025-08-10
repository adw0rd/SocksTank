# Установка

Чтобы работал Led нужно доустановить rpi_ws281x:

```
sudo pip install rpi_ws281x --break-system-packages
```

# Автозаспуск

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

И добавляем его в автозапуск:

```
mkdir ~/.config/autostart/
echo "Exec=/home/zeus/start.sh" > ~/.config/autostart/start.desktop
chmod +x ~/start.sh
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
