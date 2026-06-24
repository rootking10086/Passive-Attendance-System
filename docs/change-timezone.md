# 更改时区

将树莓派时区设置为 Asia/Shanghai。

## 方法一: raspi-config

```bash
sudo raspi-config
# Localisation Options → Timezone → Asia → Shanghai
```

## 方法二: 命令行

```bash
# 查看当前时间
timedatectl

# 配置 NTP 时间同步
sudo nano /etc/systemd/timesyncd.conf
```

`/etc/systemd/timesyncd.conf` 添加:

```
NTP=ntp.aliyun.com
```
