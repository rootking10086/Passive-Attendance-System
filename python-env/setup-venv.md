# Python 虚拟环境说明

本项目的 Python 应用运行在虚拟环境中。

- **路径**: `/home/pi/Desktop/myenv`
- **Python 版本**: 3.11.2
- **依赖文件**: `app/requirements.txt`

## 在树莓派上部署

```bash
# 确保已安装 venv
sudo apt install python3-venv

# 创建虚拟环境
cd /home/pi/Desktop
python3 -m venv myenv

# 安装依赖
source myenv/bin/activate
pip install -r /path/to/app/requirements.txt
deactivate
```
