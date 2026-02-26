#!/bin/bash
# Настройка RPi 5 для SocksTank
# Запуск: ssh rpi5 "cd ~/sockstank && sudo bash scripts/setup_rpi5.sh"

set -e

echo "=== SocksTank RPi 5 Setup ==="

# 1. Бэкап текущего config.txt
CONFIG="/boot/firmware/config.txt"
BACKUP="${CONFIG}.bak.$(date +%Y%m%d_%H%M%S)"

if [ -f "$CONFIG" ]; then
    echo "Бэкап: $CONFIG → $BACKUP"
    cp "$CONFIG" "$BACKUP"
fi

# 2. Показать текущий config.txt
echo ""
echo "=== Текущий config.txt ==="
cat "$CONFIG"
echo ""

# 3. Проверяем что нужно добавить
echo "=== Проверка необходимых настроек ==="

add_if_missing() {
    local key="$1"
    local line="$2"
    if grep -q "^${key}" "$CONFIG" 2>/dev/null; then
        echo "  ✅ Уже есть: $key"
    else
        echo "  ➕ Добавляю: $line"
        echo "$line" >> "$CONFIG"
    fi
}

# Камера OV5647
add_if_missing "dtoverlay=ov5647" "dtoverlay=ov5647,cam0"

# CMA для камеры
add_if_missing "dtoverlay=cma" "dtoverlay=cma,cma-256"

# PWM для сервоприводов
add_if_missing "dtoverlay=pwm-2chan" "dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4"

# Питание через GPIO
add_if_missing "usb_max_current_enable" "usb_max_current_enable=1"
add_if_missing "psu_max_current" "psu_max_current=5000"

# Bluetooth off (экономия энергии)
add_if_missing "dtoverlay=disable-bt" "dtoverlay=disable-bt"

# GPU memory для headless
add_if_missing "gpu_mem" "gpu_mem=16"

# I2C (для сенсоров)
add_if_missing "dtparam=i2c_arm" "dtparam=i2c_arm=on"

echo ""
echo "=== Итоговый config.txt ==="
cat "$CONFIG"

# 4. Отключить Wi-Fi power management
echo ""
echo "=== Wi-Fi power management ==="
if command -v nmcli &> /dev/null; then
    WIFI_CON=$(nmcli -t -f NAME,TYPE con show --active | grep wifi | cut -d: -f1)
    if [ -n "$WIFI_CON" ]; then
        echo "  Wi-Fi: $WIFI_CON"
        # Отключить power saving для стабильности SSH
        nmcli con modify "$WIFI_CON" wifi.powersave 2 2>/dev/null || true
        echo "  ✅ Wi-Fi power saving отключён"
    fi
fi

# 5. Проверка текущего состояния
echo ""
echo "=== Текущее состояние ==="
echo "  Температура: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
echo "  Throttled: $(vcgencmd get_throttled 2>/dev/null || echo 'N/A')"
echo "  Питание: $(vcgencmd pmic_read_adc 2>/dev/null | grep EXT5V || echo 'N/A')"

echo ""
echo "=== Готово! ==="
echo "Перезагрузка нужна для применения config.txt: sudo reboot"
echo "Бэкап сохранён: $BACKUP"
