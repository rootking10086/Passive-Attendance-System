# lighttpd + PHP 配置

用于配网页面的 Web 服务器搭建。

## 安装

```bash
sudo apt install lighttpd
sudo apt install php-cgi
```

## 配置 PHP

```bash
sudo lighty-enable-mod fastcgi
sudo lighty-enable-mod fastcgi-php
service lighttpd force-reload
sudo systemctl restart lighttpd
```

## 验证 PHP-CGI

```bash
which php-cgi
```

## 设置权限

```bash
sudo chown -R www-data:www-data /var/www/html
sudo chmod -R 755 /var/www/html
```

## 测试

```bash
curl -I http://localhost/wifi-setup/
```
