#!/usr/bin/env python3
# /home/pi/Desktop/mdns_service/mdns_service.py

from zeroconf import ServiceInfo, Zeroconf
import socket
import time
import logging
import os
from datetime import datetime

# 配置日志
log_file = "/home/pi/Desktop/log.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # 同时在终端输出
    ]
)
logger = logging.getLogger("mDNS_Service")

def get_local_ip():
    """获取本地真实IP地址（非回环地址）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        logger.info(f"获取到本地IP: {ip}")
        return ip
    except Exception as e:
        logger.error(f"获取IP失败: {e}")
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()

def register_service(port=5050):
    """注册HTTP服务"""
    hostname = socket.gethostname()
    ip = get_local_ip()

    service_info = ServiceInfo(
        "_http._tcp.local.",
        f"{hostname} HTTP Server._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"description": "Attendance Upload Server", "version": "1.0"},
        server=f"{hostname}.local."
    )

    zeroconf = Zeroconf()
    try:
        zeroconf.register_service(service_info)
        logger.info(f"✅ 服务已注册: http://{ip}:{port}")
        return zeroconf
    except Exception as e:
        logger.error(f"注册服务失败: {e}")
        return None

def log_system_info():
    """记录系统信息"""
    try:
        # 获取CPU温度
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read()) / 1000
            logger.info(f"CPU温度: {temp}°C")

        # 获取内存使用情况
        with open("/proc/meminfo", "r") as f:
            meminfo = f.readlines()
            total = int(meminfo[0].split()[1])
            free = int(meminfo[1].split()[1])
            used = total - free
            logger.info(f"内存使用: {used}kB / {total}kB ({used/total*100:.1f}%)")

        # 获取系统运行时间
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            logger.info(f"系统运行时间: {days}天 {hours}小时")

    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")

def main():
    logger.info("="*50)
    logger.info("启动 mDNS 服务注册")
    logger.info(f"日志文件: {log_file}")
    logger.info("="*50)

    # 记录初始系统信息
    log_system_info()

    port = 5050  # 默认端口
    last_ip = ""
    restart_count = 0

    while True:
        try:
            # 检查IP是否变化
            current_ip = get_local_ip()
            if current_ip != last_ip:
                logger.info(f"检测到IP变化: {last_ip} -> {current_ip}")
                last_ip = current_ip

            # 注册服务
            zeroconf = register_service(port)
            if not zeroconf:
                logger.error("服务注册失败，5秒后重试...")
                time.sleep(5)
                restart_count += 1
                continue

            # 每5分钟记录一次系统状态
            start_time = time.time()
            while time.time() - start_time < 300:  # 5分钟
                # 每60秒检查一次服务状态
                time.sleep(60)
                logger.info("服务运行中...")

            # 清理并重新注册
            zeroconf.unregister_all_services()
            zeroconf.close()
            logger.info("服务重新注册中...")
            log_system_info()

        except KeyboardInterrupt:
            logger.info("收到中断信号，停止服务...")
            break
        except Exception as e:
            logger.error(f"发生未处理异常: {e}")
            restart_count += 1
            logger.info(f"10秒后重启服务... (重启次数: {restart_count})")
            time.sleep(10)

if __name__ == "__main__":
    main()
    logger.info("服务已停止")
