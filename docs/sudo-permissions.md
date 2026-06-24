# sudo 权限配置

通过 `visudo` 配置免密码 sudo 执行权限。

## 配置

```bash
sudo visudo
```

添加以下内容以允许特定命令免密码执行:

```
pi ALL=(ALL) NOPASSWD: /usr/bin/kill, /usr/bin/systemctl, /sbin/ip, /sbin/wpa_supplicant, /sbin/dhclient, /usr/bin/killall, /bin/pgrep
```
