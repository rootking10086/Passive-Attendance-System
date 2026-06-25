# 🎯 无感考勤系统 (Passive Attendance System)

> 基于树莓派 + 蓝牙低功耗 (BLE) 的**无感考勤解决方案** —— 员工走近即签到，无需掏出手机或刷卡。

本项目实现了从**设备配网** → **蓝牙扫描** → **数据记录** → **Excel 导出**的全链路闭环，适用于中小型办公室、实验室或活动签到的自动化管理。

---

## ✨ 功能特性

- **无感考勤**：通过 BLE 蓝牙信号自动识别周边设备，实现“走近即签到，离开即签退”
- **双网络模式**：支持 **AP 热点模式**（无需路由器，开箱即用）与 **STA 客户端模式**（连接现有 WiFi）
- **一键配网**：内置 Web 配网页面（PHP + lighttpd），手机/电脑连接热点后即可配置 WiFi
- **零配置发现**：集成 mDNS 服务，支持通过 `http://raspberrypi.local` 访问，无需记忆 IP 地址
- **安全认证**：Flask + JWT 接口鉴权，保障考勤数据安全
- **数据导出**：支持一键导出 Excel 考勤报表，方便与 HR 系统对接
- **开机自启**：所有核心服务均配置为 systemd 守护进程，断电重启后自动恢复运行

---

## 🖥️ 硬件与系统要求

本项目已在以下硬件平台上完成测试与验证，均能稳定运行：

| 硬件平台 | 运行系统 | 测试状态 |
| :--- | :--- | :--- |
| **Raspberry Pi 4B** | Raspberry Pi OS (Bookworm) | ✅ 完全兼容 |
| **Raspberry Pi Zero 2W** | Raspberry Pi OS (Bookworm) | ✅ 完全兼容 |

> 💡 无论是性能强劲的 Pi 4B，还是低功耗的 Zero 2W，本项目均采用相同的系统环境（Bookworm），依赖安装和部署流程完全一致，无需额外适配。

## 🧱 技术栈

| 层级 | 技术 |
| :--- | :--- |
| **后端** | Python 3.10 + Flask + SQLite + JWT |
| **蓝牙扫描** | `bluepy` / `bleak` (BLE 协议栈) |
| **网络管理** | Bash 脚本 + `create_ap` (热点工具) + `systemd` |
| **Web 服务器** | lighttpd + PHP (配网界面) |
| **服务发现** | mDNS (Avahi / `zeroconf`) |
| **硬件平台** | Raspberry Pi 4B / 3B+ (支持板载蓝牙) |

---

## 📁 项目结构

```
raspberry-pi-project/
├── app/                          # Flask Web 应用
│   ├── app.py                    # 考勤应用主程序
│   ├── requirements.txt          # Python 依赖
│   └── database/
│       └── users.db              # SQLite 数据库
├── scripts/
│   └── network-mode/             # 网络模式切换脚本
│       ├── to_STA_mode.sh        # 切换到 WiFi 客户端模式
│       ├── to_AP_mode.sh         # 切换到 AP 热点模式
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

---

## 🚀 快速开始（从零部署）

> 以下步骤适用于全新烧录的 Raspberry Pi OS (Bookworm)，已在 Pi 4B 和 Zero 2W 上验证通过

### 1️⃣ 克隆项目到树莓派

```bash
git clone git@github.com:rootking10086/Passive-Attendance-System.git
cd Passive-Attendance-System
2️⃣ 基础环境配置
更换 APT 镜像源（国内加速）：参考 docs/apt-mirror.md

修改时区为本地时间：参考 docs/change-timezone.md

安装热点创建工具 create_ap：参考 docs/create-ap-hotspot.md

3️⃣ 配置 Python 虚拟环境
bash
python3 -m venv venv
source venv/bin/activate
pip install -r app/requirements.txt
（详细说明见 docs/python-venv.md）

4️⃣ 部署 Web 配网页面 (lighttpd + PHP)
参考 docs/setup-lighttpd.md 安装 lighttpd 并配置 PHP

将 web/wifi-setup/ 目录软链接到 /var/www/html/ 或按文档配置

5️⃣ 配置脚本权限与 sudo 提权
bash
chmod +x scripts/network-mode/*.sh
配置 visudo 权限，允许无密码执行网络切换脚本：参考 docs/sudo-permissions.md 和 docs/sudo visudo.txt

6️⃣ 注册 systemd 开机自启服务
复制 services/ 下的 .service 文件到 /etc/systemd/system/，然后执行：

bash
sudo systemctl enable apmode.service mdns_service.service attendance.service
sudo systemctl start apmode.service mdns_service.service attendance.service
（详细说明见 docs/auto-start enabled.md）

7️⃣ 导入初始数据库
将 app/database/users.db 拷贝到应用目录，或通过 Flask 初始化脚本生成。

8️⃣ 启动 mDNS 服务
在虚拟环境中运行：

bash
python mdns/mdns_service.py
（此后可通过 http://raspberrypi.local 访问 Web 界面）

9️⃣ 启动考勤应用
bash
python app/app.py
默认监听 0.0.0.0:5000，访问 http://树莓派IP:5000 即可使用。

⚠️ 常见问题与注意事项
🔥 热点开启报错
若启动 AP 热点时提示 iptables 相关错误，执行：

bash
sudo apt update
sudo apt install iptables -y
（详见 assets/screenshots/Hotspot activation error.jpg）

🧹 初始化清理清单
完成首次配置后，建议清除以下临时/日志文件，避免干扰后续运行：

bash
sudo rm -f /etc/wpa_supplicant/wpa_supplicant.conf   # 清除旧 WiFi 配置（谨慎！）
rm -f app/database/log.txt                           # 删除运行日志
rm -f app/database/wifi.txt                          # 删除 WiFi 配置缓存
rm -f app/database/考勤日志.txt                       # 删除测试打卡数据
⚠️ 删除 wpa_supplicant.conf 会断开当前 WiFi，仅当你想彻底重置网络时操作。

🔑 SSH 密钥冲突
若 git pull 时遇到 Host key verification failed，参考 docs/key-conflict.md 清除旧的 SSH 缓存。

🤝 贡献与反馈
欢迎通过 Issues 提交 Bug 报告或功能建议，也欢迎 Fork 本项目并提交 Pull Request。

📧 作者邮箱：161797991@qq.com

🌐 项目主页：https://github.com/rootking10086/Passive-Attendance-System

📄 许可证
本项目采用 MIT License，允许自由使用、修改和分发，仅需保留原始版权声明。

⭐ 如果这个项目对你有帮助
请给一个 Star ⭐ 支持一下，这会让我更有动力持续更新！