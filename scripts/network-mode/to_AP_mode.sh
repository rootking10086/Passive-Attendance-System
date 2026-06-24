#!/bin/bash

# 保存当前脚本 PID
echo $$ > /tmp/ap_mode.pid

# 关闭 wpa_supplicant（断开STA模式）
sudo killall wpa_supplicant hostapd dnsmasq create_ap 2>/dev/null
sudo systemctl stop wpa_supplicant 2>/dev/null

# 重置 wlan0 接口
sudo ip link set wlan0 down
sudo ip addr flush dev wlan0
sudo ip link set wlan0 up

# 设置静态IP
sudo ip addr add 192.168.12.1/24 dev wlan0

# 启动 hostapd（可选）
sudo systemctl start hostapd 2>/dev/null
sudo systemctl stop dnsmasq 2>/dev/null

# 启动 create_ap（后台运行，记录 PID）
sudo create_ap --no-virt wlan0 lo RaspberryPi 12345678
echo $! > /tmp/ap_mode.pid

echo "热点模式已开启，SSID: chenwifi" | tee -a /home/pi/Desktop/log.txt
