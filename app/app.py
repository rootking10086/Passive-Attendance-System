from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime, timezone, time
import hashlib
import os
import json
import pandas as pd
from sqlalchemy import func, or_
import traceback
import glob
from flask_migrate import Migrate
from collections import defaultdict
from calendar import monthrange
from zoneinfo import ZoneInfo

# ===查询app.py当前使用的python版本===
import sys
print("Python executable:", sys.executable)
print("Python version:", sys.version)

shanghai = ZoneInfo("Asia/Shanghai")

app = Flask(__name__)

# === 配置数据库和 JWT ===
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'    # 自动指向 instance/users.db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'I-n8FuU7KSCNWv-3Pfp-Szj3c_CLtJc_R-dSR6_Aupo'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)  # 设置 access token 有效期为 1 小时
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)  # 设置 refresh token 有效期为 7 天

db = SQLAlchemy(app)

# 在 SQLAlchemy 初始化之后添加
migrate = Migrate(app, db)

jwt = JWTManager(app)

# === 创建access_token和refresh_token ===
def create_tokens(user_identity):
    access_token = create_access_token(identity=user_identity)
    refresh_token = create_refresh_token(identity=user_identity)
    return access_token, refresh_token

# === 签名密钥 ===
SECRET_KEY = "qt-kOi34txlRrByAwdiVlQPJ54bh7a3mmJuJOc3kA9Y"
LOG_FILE = "考勤日志.txt"

def generate_signature(user_id, device_id, timestamp):
    raw = f"{user_id}:{device_id}:{timestamp}:{SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# === 数据库模型 ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # ✅ 新增字段
    last_logout_time = db.Column(db.DateTime, nullable=True)  # ✅ 新增字段

    attendances = db.relationship('Attendance', backref='user', cascade="all, delete-orphan")
    refresh_tokens = db.relationship('RefreshToken', backref='user', cascade="all, delete-orphan")

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    device_name = db.Column(db.String(80), nullable=False)
    device_id = db.Column(db.String(80), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)
    received_at = db.Column(db.String(80), nullable=False)
    from_cache = db.Column(db.Boolean, default=False, nullable=False)
    source = db.Column(db.String(20), default="unknown")  # ✅ 新增字段

    clock_out_timestamp = db.Column(db.Integer, nullable=True)              # 下班时间（可为空）
    clock_in_status = db.Column(db.String(20), nullable=True)          # 上班打卡状态
    clock_out_status = db.Column(db.String(20), default="NOT_CLOCKED") # 下班打卡状态
    has_appeal = db.Column(db.Boolean, default=False)

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)  # "leave" or "out"
    reason = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.String(80), nullable=False)  # ISO 格式时间字符串
    end_time = db.Column(db.String(80), nullable=False)
    submitted_at = db.Column(db.String(80), nullable=False)

class RefreshToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    refresh_token = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None))

    def __init__(self, user_id, refresh_token):
        self.user_id = user_id
        self.refresh_token = refresh_token

class Beacon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    mac = db.Column(db.String(64), nullable=False,unique=True)

    def to_dict(self):
        return {
            "name": self.name,
            "mac": self.mac
        }

class ExportLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=True)  # 空表示全部用户导出
    month = db.Column(db.String(7), nullable=False)  # 格式 YYYY-MM
    filename = db.Column(db.String(255), nullable=False)
    exported_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo('Asia/Shanghai')).replace(tzinfo=None))

class Config(db.Model):
    __tablename__ = 'config'
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(256), nullable=False)

class ForbiddenPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.String(5), nullable=False)  # HH:MM
    end_time = db.Column(db.String(5), nullable=False)    # HH:MM
    reason = db.Column(db.String(255), nullable=False, default="禁止打卡")

# === 初始化数据库 ===
def create_tables():
    with app.app_context():
        db.create_all()

create_tables()

# === 通用获取配置项（字符串） ===
def get_config_value(key: str, default: str = None) -> str:
    config = Config.query.filter_by(key=key).first()
    return config.value if config else default

# === 通用设置配置项 ===
def set_config_value(key: str, value: str):
    config = Config.query.filter_by(key=key).first()
    if config:
        config.value = value
    else:
        config = Config(key=key, value=value)
        db.session.add(config)
    db.session.commit()

# === 获取时间类型的配置项 ===
def get_config_time(key: str, default_time: time) -> time:
    value = get_config_value(key)
    if value:
        try:
            hour, minute = map(int, value.split(":"))
            return time(hour, minute)
        except Exception:
            pass
    return default_time

# === 确实上下班状态 ===
def determine_status(clock_in_ts, clock_out_ts):
    clock_in_status = "NOT_CLOCKED"
    clock_out_status = "NOT_CLOCKED"

    WORK_START_TIME = get_config_time("WORK_START_TIME", time(9, 0))
    WORK_END_TIME = get_config_time("WORK_END_TIME", time(18, 0))

    if clock_in_ts:
        dt_in = datetime.fromtimestamp(clock_in_ts, tz=ZoneInfo("Asia/Shanghai"))
        if dt_in.time() <= WORK_START_TIME:
            clock_in_status = "NORMAL"
        else:
            clock_in_status = "LATE"

    if clock_out_ts:
        dt_out = datetime.fromtimestamp(clock_out_ts, tz=ZoneInfo("Asia/Shanghai"))
        if dt_out.time() >= WORK_END_TIME:
            clock_out_status = "NORMAL"
        else:
            clock_out_status = "EARLY_LEAVE"

    return clock_in_status, clock_out_status

# === 判断当前时间是否在给定时间段内，支持跨午夜  ===
def is_time_in_range(start_str, end_str, current_time):
    start = datetime.strptime(start_str, "%H:%M").time()
    end = datetime.strptime(end_str, "%H:%M").time()

    if start < end:
        # 不跨天，例如 12:00 - 13:00
        return start <= current_time < end
    else:
        # 跨天，例如 23:00 - 07:00
        return current_time >= start or current_time < end

# === 用户注册 ===
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    phone = data.get("phone")

    if not username or not password or not phone:
        return jsonify(msg="所有字段都是必填的"), 400

    if User.query.filter_by(username=username).first():
        return jsonify(msg="用户名已存在"), 400

    hashed_password = generate_password_hash(password)
    user = User(username=username, password=hashed_password, phone=phone)
    db.session.add(user)
    db.session.commit()
    return jsonify(msg="注册成功"), 201

# === 注销用户 ===
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    try:
        identity = get_jwt_identity()
        print(f"DEBUG: JWT identity from token: {identity} (type: {type(identity)})")

        # 用 username 查询用户
        user = User.query.filter_by(username=identity).first()
        print(f"DEBUG: 查询用户结果: {user}")

        if not user:
            return jsonify(msg=f"用户不存在: {identity}"), 404

        # 记录注销时间
        user.last_logout_time = datetime.now(ZoneInfo("Asia/Shanghai"))
        print(f"DEBUG: 用户 {user.username} 注销时间已记录")

        # 删除用户及关联数据
        db.session.delete(user)
        db.session.commit()
        print(f"DEBUG: 用户 {user.username} 已删除，相关数据已删除")

        return jsonify(msg="账号已注销，相关数据已删除"), 200

    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: 注销异常: {e}")
        return jsonify(msg=f"注销失败: {e}"), 500

# === 用户登录 ===
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    #print("收到上传数据：", data)
    #print("身份验证用户：", username)
    #print("用户的密码：",password)

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        access_token, refresh_token = create_tokens(username)

        # 保存 refresh_token
        refresh_token_entry = RefreshToken(user_id=username, refresh_token=refresh_token)
        db.session.add(refresh_token_entry)
        db.session.commit()

        # 下发 beacon 信息
        all_beacons = Beacon.query.all()
        beacon_list = [b.to_dict() for b in all_beacons]

        return jsonify(
            access_token=access_token,
            refresh_token=refresh_token,
            username=username,
            role="admin" if user.is_admin else "user",  # 返回角色信息
            beacons=beacon_list
        ), 200

    return jsonify(msg="用户名或密码错误"), 401

# === 申请access_token ===
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user = get_jwt_identity()  # 获取当前用户身份
        new_access_token = create_access_token(identity=current_user)  # 使用 refresh token 创建新的 access token
        return jsonify(access_token=new_access_token), 200
    except Exception as e:
        print("Refresh token 获取失败:", e)
        return jsonify({"msg": "Refresh 失败"}), 401

###############################
# === 获取当前用户信息 ===
@app.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    identity = get_jwt_identity()
    user = User.query.filter_by(username=identity).first()
    if not user:
        return jsonify(msg="用户不存在"), 404
    return jsonify(username=user.username, phone=user.phone), 200

# === 记录打卡字段 ===
def log_attendance(data, user_id, result_code, received_at=None):
    # 英文状态 → 中文解释
    result_map = {
        "saved": "成功保存打卡",
        "updated_screen_on": "更新为亮屏打卡",
        "skipped_cache": "缓存记录已存在",
        "ignored_duplicate": "重复打卡被忽略",
        "signature_invalid": "签名验证失败",
        "timestamp_expired": "时间戳过期",
        "ignored_on_leave": "请假期间打卡无效",
        "marked_as_out": "外出打卡记录已保存",
        "unknown": "未知结果"
    }
    result_text = result_map.get(result_code, "未知结果")

    log_entry = {
        "user_id": user_id,
        "status": data.get("status"),
        "device_name": data.get("device_name"),
        "device_id": data.get("device_id"),
        "timestamp": data.get("timestamp"),
        "received_at": received_at or datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        "from_cache": str(data.get("from_cache")).lower() == "true",
        "source": data.get("source", "unknown"),
        "result": result_text  # ✅ 中文描述
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

# === 上传打卡记录 ===
@app.route('/upload', methods=['POST'])
@jwt_required()
def upload_attendance():
    current_user = get_jwt_identity()  # 获取当前用户
    #print(f"当前用户: {current_user}")  # 输出当前用户，确保服务器端能正确处理 Token

    data = request.get_json()
    #print("收到数据：", data)

    required = ["status", "device_name", "timestamp", "device_id", "signature", "from_cache"]
    for field in required:
        if field not in data:
            return jsonify(success=False, error=f"缺少字段: {field}"), 400

    try:
        # 取字段
        result_status = "unknown"
        timestamp = int(data["timestamp"])
        device_id = data["device_id"]
        from_cache = str(data["from_cache"]).lower() == "true"
        signature_client = data["signature"]
        incoming_source = data.get("source", "unknown")

        # 服务器生成签名
        signature_server = generate_signature(current_user, device_id, str(timestamp))
        if signature_client != signature_server:
            result_status = "signature_invalid"
            log_attendance(data, current_user, result_status)
            return jsonify(success=False, error="签名验证失败"), 403

        now = datetime.now(shanghai)
        delta = now - datetime.fromtimestamp(timestamp, shanghai)
        #print(f"时间差：{delta.total_seconds()}秒")
        if delta > timedelta(seconds=30) and not from_cache:
            result_status = "timestamp_expired"
            log_attendance(data, current_user, result_status)
            return jsonify(success=False, error="时间戳过期"), 400

        # 请假/外出检测逻辑
        check_time_iso = datetime.fromtimestamp(timestamp, shanghai).isoformat()

        leave_requests = LeaveRequest.query.filter_by(user_id=current_user).all()
        for leave in leave_requests:
            leave_start = datetime.fromisoformat(leave.start_time)
            leave_end = datetime.fromisoformat(leave.end_time)
            if leave_start <= datetime.fromtimestamp(timestamp, shanghai) <= leave_end:
                result_status = "blocked_by_leave"
                log_attendance(data, current_user, result_status)
                return jsonify(
                    success=False,
                    error="当前时间处于请假/外出期间，打卡无效",
                    leave_type=leave.leave_type,
                    time_range={
                        "start": leave.start_time,
                        "end": leave.end_time
                    },
                    action="pause_service"
                ), 403

        # 重复记录检测,容错检测（可忍误差 ±60 秒）
        REPEAT_WINDOW_SECONDS = 60
        incoming_source = data.get("source", "unknown")

        existing = Attendance.query.filter_by(user_id=current_user, device_id=device_id,device_name=data["device_name"]).filter(
            func.abs(Attendance.timestamp - timestamp) < REPEAT_WINDOW_SECONDS
        ).first()

        #print(f"查询是否存在重复记录：{existing is not None}")

        if existing:
            existing_source = getattr(existing, "source", "unknown")

            # 优先亮屏更新策略
            if incoming_source == "screen_on" and existing_source == "screen_off":
                existing.source = "screen_on"
                db.session.commit()
                result_status = "updated_screen_on"
                log_attendance(data, current_user, result_status)
                return jsonify(success=True, message="打卡记录已更新为亮屏打卡"), 200

            # 缓存来源允许跳过重复上传
            if from_cache:
                result_status = "skipped_cache"
                log_attendance(data, current_user, result_status)
                return jsonify(success=True, message="缓存记录已存在，无需重复上传"), 200

            # 否则判断为重复上传
            result_status = "ignored_duplicate"
            log_attendance(data, current_user, result_status)
            return jsonify(success=False, error="60秒内重复打卡无效"), 400

        # 插入记录
        record = Attendance(
            user_id=current_user,
            status=data["status"],
            device_name=data["device_name"],
            device_id=device_id,
            timestamp=timestamp,
            received_at=now.isoformat(),
            from_cache=from_cache,
            source=incoming_source  # ✅ 加入 source
        )
        db.session.add(record)
        db.session.commit()
        result_status = "saved"
        log_attendance(data, current_user, result_status, record.received_at)

        return jsonify(success=True, message="打卡记录已保存", receivedAt=record.received_at, offlineRetry=from_cache), 200

    except Exception as e:
        traceback.print_exc()  # ✅ 打印完整错误堆栈
        return jsonify(success=False, error=f"服务器错误: {str(e)}"), 500

# === 请假或外出上传记录 ===
@app.route('/leave', methods=['POST'])
@jwt_required()
def submit_leave():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()

        shanghai = ZoneInfo("Asia/Shanghai")

        leave_type = data.get("leave_type")  # 必须为 "leave" 或 "out"
        reason = data.get("reason")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        if leave_type not in ("leave", "out"):
            return jsonify(success=False, error="类型必须为 leave 或 out"), 400

        if not reason or not start_time or not end_time:
            return jsonify(success=False, error="请假/外出的理由和时间段不能为空"), 400

        leave = LeaveRequest(
            user_id=current_user,
            leave_type=leave_type,
            reason=reason,
            start_time=start_time,
            end_time=end_time,
            submitted_at=datetime.now(shanghai).isoformat()
        )
        db.session.add(leave)
        db.session.commit()

        # 记录日志（格式复用打卡记录）
        log_entry = {
            "user_id": current_user,
            "status": f"{leave_type}_request",  # 例如 "leave_request" 或 "out_request"
            "device_name": "N/A",
            "device_id": "N/A",
            "timestamp": int(datetime.now(shanghai).timestamp()),
            "received_at": datetime.now(shanghai).isoformat(),
            "from_cache": False,
            "source": "user_submission",
            "result": f"提交{leave_type}成功: {reason}"
        }

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return jsonify(
            success=True,
            message="提交成功",
            action="pause_service",  # 通知客户端暂停服务
            leave_type=leave_type,
            time_range={"start": start_time, "end": end_time}
        ), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=f"服务器错误: {str(e)}"), 500

# === 获取当前用户的请假/外出记录 ===
@app.route('/leave', methods=['GET'])
@jwt_required(optional=True)  # 👈 Token 可选
def get_leave_records():
    try:
        current_user = get_jwt_identity()

        # 没带 token，就返回全部数据（或默认用户数据，或空数组）
        if not current_user:
            # 示例：返回所有用户的记录（不建议用于敏感系统）
            leaves = LeaveRequest.query.order_by(LeaveRequest.start_time.desc()).all()
        else:
            # 有 token，返回当前用户的记录
            leaves = LeaveRequest.query.filter_by(user_id=current_user).order_by(LeaveRequest.start_time.desc()).all()

        result = [
            {
                "id": leave.id,
                "leave_type": leave.leave_type,
                "reason": leave.reason,
                "start_time": leave.start_time,
                "end_time": leave.end_time,
                "submitted_at": leave.submitted_at
            }
            for leave in leaves
        ]
        return jsonify(success=True, records=result), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=f"服务器错误: {str(e)}"), 500

###############################
# === 清除请假/外出的全部记录 ===
@app.route('/clear_leave_records', methods=['POST'])
def clear_leave_records():
    try:
        # 删除所有 LeaveRequest 记录
        deleted = LeaveRequest.query.delete()
        db.session.commit()

        return jsonify(success=True, message=f"已清除 {deleted} 条请假/外出记录"), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=f"清除失败: {str(e)}"), 500

###############################
# === 查看所有用户 ===
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    result = [{"id": u.id, "username": u.username, "phone": u.phone} for u in users]
    return jsonify(result)

# === 设置保存最大导出条数 ===
@app.route('/set_export_limit', methods=['POST'])
def set_export_limit():
    data = request.get_json()
    try:
        new_limit = int(data.get("max_files"))
        if new_limit < 1 or new_limit > 100:
            return jsonify(msg="max_files 必须在 1 到 100 之间"), 400

        set_config_value("max_export_files", str(new_limit))
        return jsonify(msg=f"已设置导出文件最大保留数量为 {new_limit}"), 200
    except Exception as e:
        return jsonify(msg="参数错误，应为整数"), 400

# === 导出打卡记录为 Excel ===
@app.route('/export', methods=['GET'])
def export_attendance():
    try:
        mode = request.args.get("mode", "user").strip().lower()
        user_filter = request.args.get("user", "").strip()
        month_filter = request.args.get("month", "").strip()  # 格式：YYYY-MM

        if not month_filter:
            return jsonify(msg="必须提供 month 参数（如 2025-07）"), 400

        # 时间戳范围（秒）
        try:
            month_start = datetime.strptime(month_filter, "%Y-%m")
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            start_ts = int(month_start.timestamp())
            end_ts = int(month_end.timestamp())
        except ValueError:
            return jsonify(msg="月份格式错误，应为 YYYY-MM"), 400

        # === 查询打卡记录 ===
        att_query = Attendance.query.filter(
            Attendance.timestamp >= start_ts,
            Attendance.timestamp < end_ts
        )

        if user_filter:
            att_query = att_query.filter(Attendance.user_id == user_filter)

        attendance_records = att_query.all()

        # === 查询请假记录 ===
        leave_query = LeaveRequest.query.filter(
            LeaveRequest.start_time <= month_end.isoformat(),
            LeaveRequest.end_time >= month_start.isoformat()
        )
        if user_filter:
            leave_query = leave_query.filter(LeaveRequest.user_id == user_filter)

        leave_records = leave_query.all()

        if not attendance_records and not leave_records:
            return jsonify(msg="筛选条件下无打卡或请假记录"), 404

        combined_data = []

        # === 整理打卡数据 ===
        for record in attendance_records:
            combined_data.append({
                "record_type": "打卡",
                "user_id": record.user_id,
                "status": record.status,
                "device_name": record.device_name,
                "device_id": record.device_id,
                "timestamp": record.timestamp,
                "北京时间": datetime.fromtimestamp(record.timestamp).astimezone(
                    timezone(timedelta(hours=8))
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "received_at": record.received_at,
                "from_cache": record.from_cache,
                "source": record.source,
                "result": record.status,  # 可以自定义映射
                "reason": None,
                "start_time": None,
                "end_time": None,
                "submitted_at": None
            })

        # === 整理请假/外出数据 ===
        for record in leave_records:
            combined_data.append({
                "record_type": "请假/外出",
                "user_id": record.user_id,
                "status": None,
                "device_name": None,
                "device_id": None,
                "timestamp": None,
                "北京时间": None,
                "received_at": None,
                "from_cache": None,
                "source": None,
                "result": None,
                "reason": record.reason,
                "start_time": record.start_time,
                "end_time": record.end_time,
                "submitted_at": record.submitted_at
            })

        df = pd.DataFrame(combined_data)

        # === 中文列名映射 ===
        column_map = {
            "record_type": "记录类型",
            "user_id": "用户ID",
            "status": "打卡状态",
            "device_name": "设备名称",
            "device_id": "设备ID",
            "timestamp": "打卡时间戳",
            "北京时间": "北京时间",
            "received_at": "接收时间",
            "from_cache": "是否来自缓存",
            "source": "打卡来源",
            "result": "打卡结果",
            "reason": "请假理由",
            "start_time": "请假开始",
            "end_time": "请假结束",
            "submitted_at": "提交时间"
        }
        df.rename(columns=column_map, inplace=True)

        # === 筛选导出列 ===
        export_columns_user = [col for col in [
            "记录类型", "用户ID", "打卡状态", "北京时间", "打卡结果"
        ] if col in df.columns]

        export_columns_admin = [col for col in [
            "记录类型", "用户ID", "打卡状态", "设备名称", "设备ID", "打卡时间戳", "北京时间",
            "接收时间", "是否来自缓存", "打卡来源", "打卡结果",
            "请假理由", "请假开始", "请假结束", "提交时间"
        ] if col in df.columns]

        export_columns = export_columns_user if mode == "user" else export_columns_admin
        df = df[export_columns]

        # === 构建导出文件名 ===
        if user_filter:
            user = User.query.filter_by(id=user_filter).first()
            username = user.username if user else user_filter
            base_filename = f"{month_filter}_{username}_考勤"
        else:
            base_filename = f"{month_filter}_考勤"

        export_format = request.args.get("format", "xlsx").lower()
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        # 用户下载看到的名字（无时间戳）
        download_filename = f"{base_filename}.{export_format}"

        # 本地保存的文件名（带时间戳）
        local_filename = f"{base_filename}_{timestamp_str}.{export_format}"
        export_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, local_filename)

        # === 写入一次文件 ===
        if export_format == "csv":
            df.to_csv(export_path, index=False, encoding="utf-8-sig")
        else:
            df.to_excel(export_path, index=False)

        # === 清理旧文件 ===
        excel_files = sorted(
            glob.glob(os.path.join(export_dir, "*考勤*.xlsx")) + glob.glob(os.path.join(export_dir, "*考勤*.csv")),
            key=os.path.getmtime
        )
        MAX_FILES = int(get_config_value("max_export_files", default="15"))
        if len(excel_files) > MAX_FILES:
            files_to_delete = excel_files[:len(excel_files) - MAX_FILES]
            for old_file in files_to_delete:
                try:
                    os.remove(old_file)
                except Exception as e:
                    print(f"删除文件失败: {old_file} - {e}")

        # === 写日志（可用 local_filename 或 download_filename）===
        log_entry = ExportLog(
            user_id=user_filter if user_filter else None,
            month=month_filter,
            filename=local_filename  # 或 local_filename 看你想记录哪个
        )
        db.session.add(log_entry)
        db.session.commit()

        # === 发送文件给用户（只使用一次路径）===
        return send_file(
            export_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype=(
                'text/csv' if export_format == "csv"
                else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify(msg=f"导出失败: {str(e)}"), 500

# === 添加Beacon ===
@app.route('/add_beacon', methods=['POST'])
def add_beacon():
    data = request.get_json()
    name = data.get("name")
    mac = data.get("mac")

    if not (name and mac):
        return jsonify(msg="字段不完整"), 400

    # 检查是否已存在相同的 name + mac，避免重复
    existing = Beacon.query.filter_by(name=name, mac=mac).first()
    if existing:
        return jsonify(msg="该 Beacon 已存在"), 400

    new_beacon = Beacon(name=name, mac=mac)
    db.session.add(new_beacon)
    db.session.commit()
    return jsonify(msg="Beacon 添加成功"), 200

# === 获取Beacon ===
@app.route('/get_beacons', methods=['GET'])
def get_beacons():
    beacons = Beacon.query.all()
    return jsonify([b.to_dict() for b in beacons]), 200

# === 删除Beacon ===
@app.route('/delete_beacon', methods=['DELETE'])
def delete_beacon():
    data = request.get_json()
    name = data.get("name")
    mac = data.get("mac")

    if not (name and mac):
        return jsonify(msg="缺少必要字段"), 400

    beacon = Beacon.query.filter_by(name=name, mac=mac).first()
    if not beacon:
        return jsonify(msg="未找到匹配的 Beacon"), 404

    db.session.delete(beacon)
    db.session.commit()
    return jsonify(msg="Beacon 删除成功"), 200

# === 修改Beacon ====
@app.route('/update_beacon', methods=['PUT'])
def update_beacon():
    data = request.get_json()
    old_name = data.get("old_name")
    old_mac = data.get("old_mac")
    new_name = data.get("new_name")
    new_mac = data.get("new_mac")

    if not (old_name and old_mac and new_name and new_mac):
        return jsonify(msg="字段不完整"), 400

    # 找到原始 Beacon
    beacon = Beacon.query.filter_by(name=old_name, mac=old_mac).first()
    if not beacon:
        return jsonify(msg="未找到原始 Beacon"), 404

    # 检查新值是否已存在，避免重复
    existing = Beacon.query.filter_by(name=new_name, mac=new_mac).first()
    if existing and (existing.id != beacon.id):
        return jsonify(msg="修改后的 Beacon 已存在"), 400

    # 修改并保存
    beacon.name = new_name
    beacon.mac = new_mac
    db.session.commit()

    return jsonify(msg="Beacon 修改成功"), 200

# === 设置工作时间 ===
@app.route('/set_work_hours', methods=['POST'])
@jwt_required()
def set_work_hours():
    try:
        data = request.get_json()
        start_time = data.get("start_time")  # 格式: "09:00"
        end_time = data.get("end_time")      # 格式: "18:00"

        # 格式验证
        def validate_time(t):
            try:
                hour, minute = map(int, t.split(":"))
                return time(hour, minute)
            except:
                return None

        if not validate_time(start_time) or not validate_time(end_time):
            return jsonify({"success": False, "msg": "时间格式应为 HH:MM"}), 400

        # 写入数据库
        set_config_value("WORK_START_TIME", start_time)
        set_config_value("WORK_END_TIME", end_time)

        return jsonify({"success": True, "msg": f"工作时间已设置为 {start_time} - {end_time}"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "msg": "内部错误", "error": str(e)}), 500

# === 查看工作时间 ===
@app.route("/get_work_hours", methods=["GET"])
@jwt_required()
def get_work_hours():
    start = get_config_time("WORK_START_TIME", time(9, 0)).strftime("%H:%M")
    end = get_config_time("WORK_END_TIME", time(18, 0)).strftime("%H:%M")
    return jsonify({
        "start_time": start,
        "end_time": end
    })

###############################
# === 判断当前时间是否处于禁止打卡时间段 ===
@app.route('/is_forbidden_time', methods=['GET'])
@jwt_required()
def is_forbidden_time():
    now = datetime.now(ZoneInfo("Asia/Shanghai")).time()
    periods = ForbiddenPeriod.query.all()

    for period in periods:
        if is_time_in_range(period.start_time, period.end_time, now):
            return jsonify({
                "forbidden": True,
                "reason": period.reason or "当前时间禁止打卡"
            })

    return jsonify({"forbidden": False})

# === 获取全部禁止打卡时间段(用户接口) ===
@app.route('/forbidden_periods', methods=['GET'])
@jwt_required()
def get_forbidden_periods():
    periods = ForbiddenPeriod.query.all()
    return jsonify([
        {
            "id": p.id,
            "start": p.start_time,
            "end": p.end_time,
            "reason": p.reason
        }
        for p in periods
    ])

# === 获取全部禁止打卡时间段(管理员接口) ===
@app.route('/forbidden_periods_admin', methods=['GET'])
@jwt_required()
def admin_get_forbidden_periods():
    user_id = get_jwt_identity()
    user = User.query.filter_by(username=user_id).first()
    if not user or not user.is_admin:
        return jsonify({"error": "权限不足"}), 403

    periods = ForbiddenPeriod.query.all()
    return jsonify([
        {
            "id": p.id,
            "start": p.start_time,
            "end": p.end_time,
            "reason": p.reason
        }
        for p in periods
    ])

# === 添加时间段 ===
@app.route('/forbidden_periods_admin', methods=['POST'])
@jwt_required()
def add_forbidden_period():
    user_id = get_jwt_identity()
    user = User.query.filter_by(username=user_id).first()
    if not user or not user.is_admin:
        return jsonify({"error": "权限不足"}), 403

    data = request.get_json()
    start = data.get("start")
    end = data.get("end")
    reason = data.get("reason", "禁止打卡")

    if not start or not end:
        return jsonify({"error": "缺少 start 或 end 参数"}), 400

    period = ForbiddenPeriod(start_time=start, end_time=end, reason=reason)
    db.session.add(period)
    db.session.commit()
    return jsonify({"msg": "添加成功", "id": period.id})

# === 修改时间段 ===
@app.route('/forbidden_periods_admin/<int:id>', methods=['PUT'])
@jwt_required()
def update_forbidden_period(id):
    user_id = get_jwt_identity()
    user = User.query.filter_by(username=user_id).first()
    if not user or not user.is_admin:
        return jsonify({"error": "权限不足"}), 403

    period = db.session.get(ForbiddenPeriod, id)
    if not period:
        return jsonify({"error": "记录不存在"}), 404

    data = request.get_json()
    start = data.get("start")
    end = data.get("end")
    reason = data.get("reason")

    # 更新时要确保start_time和end_time是非空字符串，避免字段变成None
    if start is not None and start.strip() != "":
        period.start_time = start
    if end is not None and end.strip() != "":
        period.end_time = end
    # reason可以为空，但如果传入了就更新，否则保持默认或原值
    if reason is not None:
        period.reason = reason

    db.session.commit()
    return jsonify({"msg": "更新成功"})

# === 删除时间段 ===
@app.route('/forbidden_periods_admin/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_forbidden_period(id):
    user_id = get_jwt_identity()
    user = User.query.filter_by(username=user_id).first()
    if not user or not user.is_admin:
        return jsonify({"error": "权限不足"}), 403

    period = db.session.get(ForbiddenPeriod, id)
    if not period:
        return jsonify({"error": "记录不存在"}), 404

    db.session.delete(period)
    db.session.commit()
    return jsonify({"msg": "删除成功"})

# === 渲染考勤日历 ===
@app.route('/monthly', methods=['GET'])
@jwt_required()
def get_monthly_attendance():
    try:
        current_user = get_jwt_identity()
        month = request.args.get("month")  # 格式："2025-07"

        if not month:
            return jsonify(success=False, error="缺少 month 参数，格式应为 YYYY-MM"), 400

        year, mon = map(int, month.split("-"))
        shanghai_tz = ZoneInfo("Asia/Shanghai")

        # 用上海时区构造月初与月末
        start = datetime(year, mon, 1, 0, 0, 0, tzinfo=shanghai_tz)
        last_day = monthrange(year, mon)[1]
        end = datetime(year, mon, last_day, 23, 59, 59, tzinfo=shanghai_tz)

        # 获取今天的上海时间
        today = datetime.now(shanghai_tz).date()

        # 查询本月所有打卡记录
        records = Attendance.query.filter_by(user_id=current_user).filter(
            Attendance.timestamp >= int(start.timestamp()),
            Attendance.timestamp <= int(end.timestamp())
        ).all()

        # 记录按日期分组
        grouped = defaultdict(list)
        for r in records:
            date = datetime.fromtimestamp(r.timestamp).date()
            grouped[date].append(r)

        result = []
        for date, record_list in grouped.items():
            record_list.sort(key=lambda r: r.timestamp)
            is_today = (date == today)

            first = record_list[0]
            last = record_list[-1] if len(record_list) > 1 else None

            clock_in_ts = first.timestamp
            clock_out_ts = None

            if first.clock_out_timestamp:
                clock_out_ts = first.clock_out_timestamp
            elif last and last != first:
                clock_out_ts = last.timestamp

            clock_in_status, clock_out_status = determine_status(clock_in_ts, clock_out_ts)

            # 格式化时间字符串
            clock_in_time = datetime.fromtimestamp(clock_in_ts).astimezone().isoformat()
            clock_out_time = datetime.fromtimestamp(clock_out_ts).astimezone().isoformat() if clock_out_ts else None

            # 计算全天状态
            if not clock_in_ts and not clock_out_ts:
                day_status = "ABSENT"
            elif clock_in_status == "NORMAL" and clock_out_status == "NORMAL":
                day_status = "NORMAL"
            else:
                day_status = "PARTIAL"

            result.append({
                "date": date.isoformat(),
                "clockIn": clock_in_time,
                "clockOut": clock_out_time,
                "clockInStatus": clock_in_status,
                "clockOutStatus": clock_out_status,
                "dayStatus": day_status,
                "location": last.device_name if last else first.device_name or "",
                "hasAppeal": any(r.has_appeal for r in record_list),
                "isToday": is_today
            })

        return jsonify(success=True, records=result), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=f"服务器错误: {str(e)}"), 500

# === 用户手动下班打卡 ===
@app.route('/clockout', methods=['POST'])
@jwt_required()
def clock_out():
    try:
        # 安全地获取请求体 JSON，防止空或格式错误导致异常
        data = request.get_json(silent=True) or {}
        print(f"[clock_out] 请求体数据: {data}")

        user_id = get_jwt_identity()
        print(f"[clock_out] 当前用户 ID: {user_id}")

        now = datetime.now(shanghai)
        print(f"[clock_out] 当前北京时间: {now.isoformat()}")

        # 获取当天的北京时间范围
        day_start = datetime(now.year, now.month, now.day)
        day_end = day_start + timedelta(days=1)
        print(f"[clock_out] 查询时间范围: {day_start.isoformat()} - {day_end.isoformat()}")

        # 查询当天的上班记录
        attendance = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.timestamp >= int(day_start.timestamp()),
            Attendance.timestamp < int(day_end.timestamp())
        ).order_by(Attendance.timestamp.asc()).first()

        if not attendance:
            print(f"[clock_out] user_id={user_id} 没有找到当天上班记录")
            return jsonify(success=False, message="尚未上班打卡，无法下班打卡"), 400

        print(f"[clock_out] 查询到的上班记录: id={attendance.id}, timestamp={attendance.timestamp}, clock_out_timestamp={attendance.clock_out_timestamp}")

        # 防止重复打卡
        if attendance.clock_out_timestamp:
            print(f"[clock_out] user_id={user_id} 今天已下班打卡，时间戳：{attendance.clock_out_timestamp}")
            return jsonify(success=False, message="今天已下班打卡"), 400

        # 设置下班时间和状态
        attendance.clock_out_timestamp = int(now.timestamp())
        attendance.clock_out_status = "NORMAL"
        db.session.commit()
        print(f"[clock_out] user_id={user_id} 成功设置下班时间戳: {attendance.clock_out_timestamp}")

        return jsonify(success=True,
                       message="下班打卡成功",
                       timestamp=now.isoformat(),
                       clockOutStatus="NORMAL"), 200

    except Exception as e:
        import traceback
        print(f"[clock_out] 发生异常: {str(e)}")
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

###############################
# === 删除用户上传的下班打卡记录 ===
@app.route('/test/clockout', methods=['DELETE'])
def test_delete_clock_out_by_username():
    try:
        # 获取并清洗参数
        username = request.args.get("username")
        if not username:
            return jsonify(success=False, message="缺少 username 参数"), 400
        username = username.strip().lower()

        date_str = request.args.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify(success=False, message="date 参数格式错误，应为 YYYY-MM-DD"), 400
        else:
            target_date = datetime.now(shanghai).date()

        # 查询用户（大小写不敏感）
        user = User.query.filter(db.func.lower(User.username) == username).first()
        if not user:
            print(f"[test_delete_clock_out] 未找到用户: {username}")
            return jsonify(success=False, message="未找到该用户名"), 404

        print(f"[test_delete_clock_out] 请求 username={username}, 匹配 user_id={user.id}")

        # 计算时间范围
        day_start = datetime(target_date.year, target_date.month, target_date.day)
        day_end = day_start + timedelta(days=1)
        day_start_ts = int(day_start.timestamp())
        day_end_ts = int(day_end.timestamp())

        print(f"[test_delete_clock_out] 日期: {target_date}, 查询范围: {day_start_ts} - {day_end_ts}")

        # 查找考勤记录（注意 user_id 是字符串 username，不是整数 id）
        attendance = Attendance.query.filter(
            Attendance.user_id == user.username,
            Attendance.timestamp >= day_start_ts,
            Attendance.timestamp < day_end_ts
        ).order_by(Attendance.timestamp.asc()).first()

        if not attendance:
            print(f"[test_delete_clock_out] 未找到 user_id={user.id} 在 {target_date} 的考勤记录")

            # 打印当天所有记录帮助排查
            all_attendance = Attendance.query.filter(
                Attendance.timestamp >= day_start_ts,
                Attendance.timestamp < day_end_ts
            ).all()
            print("[test_delete_clock_out] 当日考勤记录如下：")
            for a in all_attendance:
                print(f"  - record_id={a.id}, user_id={a.user_id}, timestamp={a.timestamp}, clock_out={a.clock_out_timestamp}")

            return jsonify(success=False, message=f"{target_date} 无考勤记录"), 404

        if not attendance.clock_out_timestamp:
            return jsonify(success=False, message=f"{target_date} 尚未有下班打卡记录"), 400

        # 删除下班打卡数据
        attendance.clock_out_timestamp = None
        attendance.clock_out_status = None
        db.session.commit()

        print(f"[test_delete_clock_out] 用户 {username} 在 {target_date} 的下班打卡记录已删除")

        return jsonify(success=True, message=f"用户 {username} 在 {target_date} 的下班打卡记录已删除"), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

# === 启动服务 ===
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5050
    )
