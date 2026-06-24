# Raspberry Pi Project

树莓派项目：WiFi 网络模式切换 + 考勤 Web 应用 + mDNS 服务

## 项目结构

```
raspberry-pi-project/
├── app/                          # Flask Web 应用
│   ├── app.py                    # 考勤应用主程序
│   ├── requirements.txt          # Python 依赖
│   └── database/
│       └── users.db              # SQLite 数据库
├── scripts/
│   └── network-mode/             # 网络模式切换脚本
│       ├── to_STA_mode.sh        # 切换为客户端 (STA) 模式
│       ├── to_AP_mode.sh         # 切换为热点 (AP) 模式
│       └── check_wifi_or_ap.sh   # 开机自启检测网络模式
├── services/                     # systemd 服务文件
│   ├── apmode.service            # 网络模式自启服务
│   ├── mdns_service.service      # mDNS 广播服务
│   └── attendance.service        # 考勤应用自启服务
├── web/
│   └── wifi-setup/               # 配网 Web 页面
│       ├── index.php             # 配网页面 (PHP)
│       └── lighttpd.conf         # lighttpd Web 服务器配置
├── mdns/
│   └── mdns_service.py           # mDNS 服务注册脚本
├── docs/                         # 配置文档
│   ├── apt-mirror.md             # APT 换源 & pip 镜像
│   ├── create-ap-hotspot.md      # 创建 WiFi 热点
│   ├── change-timezone.md        # 更改时区
│   ├── sudo-permissions.md       # sudo 权限配置
│   ├── setup-lighttpd.md         # lighttpd + PHP 配置
│   ├── python-venv.md            # Python 虚拟环境
│   └── key-conflict.md           # SSH 密钥冲突解决
├── python-env/
│   └── setup-venv.md             # 虚拟环境说明
└── assets/
    └── screenshots/              # 截图
```

## 快速开始

1. 配置 APT 镜像源: `docs/apt-mirror.md`
2. 安装 create_ap 热点工具: `docs/create-ap-hotspot.md`
3. 更改 Raspberry Pi 时区: `docs/change-timezone.md`
4. 配置 network 脚本权限: `network-mode/755配网权限.txt`
5. 配置 sudo visudo 执行权限: `docs/sudo visudo.txt`
6. 部署 systemd 服务: `docs/auto-start enabled.md`
7. 安装 Web 服务器: `docs/setup-lighttpd.md`
8. 设置 Python 虚拟环境: `docs/python-venv.md`
9. 注册 mdns 服务: `mdns/` 下的 mdns_service.py     #python虚拟环境下运行
10. 运行 app.py: `app/` 下的 app.py     #python虚拟环境下运行
11. 导入 users.db 数据库: `app/database/` 下的users.db

## 注意

1. 若遇到树莓派热点开启错误(如图`assets/screenshots`)

```bash
sudo apt update
sudo apt install iptables -y
```

2. 将以上配置完后应执行以下步骤，确保系统完成初始化！

```bsah
删除wpa_supplicant文件
更新users.db数据库
删除log.txt
删除wifi.txt
删除考勤日志.txt
```