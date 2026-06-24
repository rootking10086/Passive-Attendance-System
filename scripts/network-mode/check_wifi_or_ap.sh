#!/bin/bash

# 将日志输出到 /home/pi/Desktop/log.txt
LOG_FILE="/home/pi/Desktop/log.txt"
LOCK_FILE="/tmp/check_wifi_or_ap.lock"

# 获取锁，如果已经有其他进程在运行，退出
exec 200>$LOCK_FILE
flock -n 200 || exit 1

echo "[$(date)] 脚本启动..." >> $LOG_FILE

# 检查 wpa_supplicant.conf 文件是否存在
if test -f /etc/wpa_supplicant/wpa_supplicant.conf; then
    echo "[$(date)] wpa_supplicant.conf 文件存在，尝试连接 Wi-Fi..." >> $LOG_FILE

    # 启动Wi-Fi模式
    sudo /home/pi/Desktop/net_mode_manager/to_STA_mode.sh >> $LOG_FILE 2>&1

    # 检查 to_STA_mode.sh 是否成功
    if [ $? -eq 0 ]; then
        echo "[$(date)] Wi-Fi 连接成功!" >> $LOG_FILE

    else
        echo "[$(date)] Wi-Fi 连接失败，启动热点模式..." >> $LOG_FILE
        # 启动热点模式
        sudo /home/pi/Desktop/net_mode_manager/to_AP_mode.sh >> $LOG_FILE 2>&1
    fi
else
    echo "[$(date)] wpa_supplicant.conf 文件不存在，启动热点模式..." >> $LOG_FILE
    # 如果没有 wpa_supplicant.conf 文件，启动热点模式
    sudo /home/pi/Desktop/net_mode_manager/to_AP_mode.sh >> $LOG_FILE 2>&1
fi
