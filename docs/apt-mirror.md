# APT 换源 & pip 镜像配置

## APT 换源

```bash
# 清理缓存
sudo rm -rf /var/lib/apt/lists/*

# 编辑 sources.list
sudo nano /etc/apt/sources.list
# 替换为阿里云镜像源

# 编辑 raspi.list
sudo nano /etc/apt/sources.list.d/raspi.list

# 更新
sudo apt-get update
sudo apt-get upgrade
```

## pip 配置阿里云镜像

```bash
mkdir ~/.pip
sudo nano ~/.pip/pip.conf
```

`~/.pip/pip.conf` 内容:

```ini
[global]
trusted-host=mirrors.aliyun.com
index-url=https://mirrors.aliyun.com/pypi/simple/
```
