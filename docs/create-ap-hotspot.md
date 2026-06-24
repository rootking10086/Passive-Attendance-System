# 创建 WiFi 热点

使用 `create_ap` 工具在树莓派上创建 WiFi 热点。

## 安装依赖

```bash
sudo apt-get install network-manager
sudo apt-get install git
sudo apt-get update
sudo apt-get install util-linux procps hostapd iproute2 iw haveged dnsmasq
```

## 安装 create_ap

```bash
sudo git clone https://github.com/oblique/create_ap
cd create_ap
sudo make install
```

## 启动热点

```bash
sudo ifconfig wlan0 down
sudo apt install iptables -y
sudo create_ap wlan0 lo wifi_pi 12345678    #热点名称:wifi_pi 热点密码:12345678
```

## 配置开机自启

```bash
sudo nano /etc/create_ap.conf
sudo systemctl enable create_ap.service
```

## 服务管理命令

| 操作 | 命令 |
|------|------|
| 启用开机自启 | `systemctl enable create_ap.service` |
| 禁用开机自启 | `systemctl disable create_ap.service` |
| 查询是否自启 | `systemctl is-enabled create_ap.service` |
| 启动服务 | `systemctl start create_ap.service` |
| 停止服务 | `systemctl stop create_ap.service` |
| 重启服务 | `systemctl restart create_ap.service` |
| 查看状态 | `systemctl status create_ap.service` |
