# Python 虚拟环境

## 创建虚拟环境

```bash
cd /home/pi/Desktop
python -m venv myenv
```

## 激活环境

```bash
source myenv/bin/activate
```

## 管理依赖

```bash
# 导出已安装的依赖
pip freeze > requirements.txt

# 安装依赖
pip install -r requirements.txt
```

## 退出环境

```bash
deactivate
```
