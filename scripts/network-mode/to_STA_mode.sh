#!/bin/bash

echo "转换为客户端模式STA-WIFI"

# 停止 create_ap（如果之前在运行）
if [ -f /tmp/ap_mode.pid ]; then
    PID=$(cat /tmp/ap_mode.pid)
    echo "停止 create_ap 进程 PID: $PID" | tee -a /home/pi/Desktop/log.txt
    sudo kill "$PID" 2>/dev/null
    rm /tmp/ap_mode.pid
fi

# 停止 hostapd 和 dnsmasq
sudo systemctl stop hostapd 2>/dev/null
sudo systemctl stop dnsmasq 2>/dev/null

# 停止旧 wpa_supplicant
sudo killall wpa_supplicant 2>/dev/null
sleep 1
pgrep wpa_supplicant && sudo kill -9 $(pgrep wpa_supplicant) 2>/dev/null

# 重启 wlan0
sudo ip link set wlan0 down
sudo ip addr flush dev wlan0
sudo ip link set wlan0 up

# 检查是否已有 wpa_supplicant 进程
if pgrep -x "wpa_supplicant" > /dev/null
then
    echo "wpa_supplicant 已在运行"
else
    echo "启动 wpa_supplicant"
    sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
fi

# 启动新的 wpa_supplicant 后台进程
#sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf

# 请求 IP 地址
sudo dhclient wlan0

# 等待更多时间，确保网络稳定
echo "等待 10 秒以确保网络完全稳定..." | tee -a /home/pi/Desktop/log.txt
sleep 10

# 等待最多 30 秒判断是否联网
echo "正在尝试联网..." | tee -a /home/pi/Desktop/log.txt
for i in {1..30}; do
    if ping -c 1 -W 1 www.baidu.com &> /dev/null; then
        echo "已连接互联网" | tee -a /home/pi/Desktop/log.txt
        break
    fi
    echo "尝试连接中...第 $i 次" | tee -a /home/pi/Desktop/log.txt
    sleep 1
done

# 如果连接失败，退出并返回错误状态
if ! ping -c 1 -W 1 www.baidu.com &> /dev/null; then
    echo "Wi-Fi 连接失败，无法获取 IP 地址。" | tee -a /home/pi/Desktop/log.txt
    exit 1
fi

echo "=== 切换完成 ===" | tee -a /home/pi/Desktop/log.txt
