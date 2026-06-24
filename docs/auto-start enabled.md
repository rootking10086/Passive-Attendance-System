# 启动自启动脚本配置

部署 systemd 服务在树莓派上

## 创建服务文件 & 部署自启动服务

## 配置wifi热点转换服务

```bash
sudo nano /etc/systemd/system/apmode.service
```

`/etc/systemd/system/apmode.service` 内容:
```ini
[Unit]
Description=Start Wi-Fi or AP Mode on Boot
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/home/pi/Desktop/net_mode_manager/check_wifi_or_ap.sh
Restart=no
TimeoutStartSec=60s
RemainAfterExit=true
User=pi

[Install]
WantedBy=multi-user.target
```

## 配置开机自启

```bash
sudo systemctl daemon-reload
sudo systemctl enable apmode.service
sudo systemctl start apmode.service
```

## 配置考勤app服务

```bash
sudo nano /etc/systemd/system/attendance.service
```

`/etc/systemd/system/attendance.service` 内容:
```ini
[Unit]
Description=Attendance App Service
After=network.target

[Service]
ExecStart=/home/pi/Desktop/myenv/bin/python3 /home/pi/Desktop/attendance/app.py
WorkingDirectory=/home/pi/Desktop/attendance
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
```

## 配置开机自启

```bash
sudo systemctl daemon-reload
sudo systemctl enable attendance.service
sudo systemctl start attendance.service
```

## 配置mdns服务

```bash
sudo nano /etc/systemd/system/mdns_service.service
```

`/etc/systemd/system/mdns_service.service` 内容:
```ini
[Unit]
Description=Python mDNS Zeroconf Service
After=network.target

[Service]
ExecStart=/home/pi/Desktop/myenv/bin/python3 /home/pi/Desktop/mdns_service/mdns_service.py
WorkingDirectory=/home/pi/Desktop/mdns_service
#StandardOutput=append:/home/pi/Desktop/mdns_service_stdout.log
#StandardError=append:/home/pi/Desktop/mdns_service_stderr.log
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
```

## 配置开机自启

```bash
sudo systemctl daemon-reload
sudo systemctl enable mdns_service.service
sudo systemctl start mdns_service.service
```

## 设置mdns_service脚本可执行

```bash
chmod +x /home/pi/Desktop/mdns_service.py
```

## 可视化部署的服务

```bash
sudo apt install avahi-utils
avahi-browse -at
```