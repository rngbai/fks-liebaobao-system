from __future__ import annotations

import base64
import binascii
import json
import logging
import logging.handlers
import mimetypes
import os
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from config import userId
from env_bootstrap import load_local_env

load_local_env()


HOST = os.environ.get("RECHARGE_VERIFY_HOST", "0.0.0.0")
PORT = int(os.environ.get("RECHARGE_VERIFY_PORT", "5000"))

LOG_DIR = Path(os.environ.get("FKS_LOG_DIR", Path(__file__).resolve().parent / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _setup_logging():
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)
    rotating = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    rotating.setFormatter(fmt)
    root.addHandler(rotating)


_setup_logging()
logger = logging.getLogger("fks")

RECEIVER_BEAST_ID = str(userId)
RECEIVER_BEAST_NICK = os.environ.get("RECEIVER_BEAST_NICK", "面板小助手")
DEFAULT_CANCEL_LIMIT = 5
BASE_DIR = Path(__file__).resolve().parent
ADMIN_DIST_DIR = BASE_DIR / "admin" / "dist"
ADMIN_INDEX_FILE = ADMIN_DIST_DIR / "index.html"
UPLOADS_DIR = BASE_DIR / "uploads"
ALLOWED_UPLOAD_FOLDERS = {"guarantee-proof", "community-avatar"}
ADMIN_USERNAME = os.environ.get("FKS_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("FKS_ADMIN_PASSWORD", "")

try:
    ADMIN_SESSION_TTL_MS = max(10 * 60 * 1000, int(os.environ.get("FKS_ADMIN_SESSION_TTL_MS", "43200000")))
except (TypeError, ValueError):
    ADMIN_SESSION_TTL_MS = 12 * 60 * 60 * 1000

ADMIN_SESSIONS: dict[str, dict[str, int | str]] = {}
ADMIN_SESSION_LOCK = threading.Lock()

try:
    DASHBOARD_CACHE_TTL_SECONDS = max(0, int(os.environ.get("FKS_DASHBOARD_CACHE_TTL_SECONDS", "8")))
except (TypeError, ValueError):
    DASHBOARD_CACHE_TTL_SECONDS = 8

_DASHBOARD_CACHE: dict[str, dict[str, object]] = {}
_DASHBOARD_CACHE_LOCK = threading.Lock()

_PUBLIC_ORDERS_CACHE: dict[str, dict[str, object]] = {}
_PUBLIC_ORDERS_CACHE_TTL = 10
_PUBLIC_ORDERS_CACHE_LOCK = threading.Lock()


def now_ms() -> int:
    return int(time.time() * 1000)


def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_bytes(handler, status_code, body, content_type="application/octet-stream"):
    handler.send_response(status_code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, openid, x-user-key, x-admin-token")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def build_json(handler, status_code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    build_bytes(handler, status_code, body, "application/json; charset=utf-8")


def build_html(handler, status_code, html_text):
    build_bytes(handler, status_code, html_text.encode("utf-8"), "text/html; charset=utf-8")


def ok(data=None, message="success"):
    return {"ok": True, "message": message, "data": data or {}}


def fail(message, status=200, data=None):
    return status, {"ok": False, "message": message, "data": data or {}}


def resolve_admin_asset(request_path):
    if request_path in ("/admin", "/admin/", "/admin/index.html"):
        return ADMIN_INDEX_FILE

    if not request_path.startswith("/admin/"):
        raise FileNotFoundError("后台资源路径不存在")

    relative_path = request_path[len("/admin/") :].lstrip("/")
    if not relative_path:
        return ADMIN_INDEX_FILE

    admin_root = ADMIN_DIST_DIR.resolve()
    candidate = (ADMIN_DIST_DIR / relative_path).resolve()
    try:
        candidate.relative_to(admin_root)
    except ValueError as exc:
        raise PermissionError("非法后台资源路径") from exc

    if candidate.is_file():
        return candidate

    if Path(relative_path).suffix:
        raise FileNotFoundError(f"未找到后台资源文件: {candidate}")

    return ADMIN_INDEX_FILE


def load_admin_asset(request_path):
    asset_path = resolve_admin_asset(request_path)
    if not asset_path.exists():
        raise FileNotFoundError(f"未找到后台构建文件: {asset_path}")

    content_type = mimetypes.guess_type(str(asset_path))[0] or "application/octet-stream"
    suffix = asset_path.suffix.lower()
    if suffix == ".html":
        content_type = "text/html; charset=utf-8"
    elif suffix == ".css":
        content_type = "text/css; charset=utf-8"
    elif suffix == ".js":
        content_type = "text/javascript; charset=utf-8"
    elif suffix == ".json":
        content_type = "application/json; charset=utf-8"
    return asset_path.read_bytes(), content_type


def load_upload_asset(request_path):
    relative_path = str(request_path or "")[len("/uploads/") :].lstrip("/")
    if not relative_path:
        raise FileNotFoundError("缺少上传资源路径")
    upload_root = UPLOADS_DIR.resolve()
    candidate = (UPLOADS_DIR / relative_path).resolve()
    try:
        candidate.relative_to(upload_root)
    except ValueError as exc:
        raise PermissionError("非法上传资源路径") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"未找到上传资源文件: {candidate}")
    content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
    return candidate.read_bytes(), content_type


def save_base64_image(image_base64, image_name="", folder="guarantee-proof"):
    folder_name = str(folder or "guarantee-proof").strip().lower() or "guarantee-proof"
    if folder_name not in ALLOWED_UPLOAD_FOLDERS:
        folder_name = "guarantee-proof"

    raw_text = str(image_base64 or "").strip()
    if not raw_text:
        raise ValueError("缺少图片内容")

    header = ""
    if raw_text.startswith("data:"):
        header, _, raw_text = raw_text.partition(",")

    try:
        content = base64.b64decode(raw_text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("图片数据解析失败") from exc

    if not content:
        raise ValueError("图片内容为空")

    suffix = Path(str(image_name or "")).suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        if "image/png" in header.lower():
            suffix = ".png"
        elif "image/webp" in header.lower():
            suffix = ".webp"
        elif "image/gif" in header.lower():
            suffix = ".gif"
        else:
            suffix = ".jpg"
    if suffix == ".jpeg":
        suffix = ".jpg"

    upload_dir = (UPLOADS_DIR / folder_name).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = upload_dir / file_name
    file_path.write_bytes(content)
    return f"/uploads/{folder_name}/{file_name}"


def get_request_scheme(handler):
    forwarded_proto = str(handler.headers.get("X-Forwarded-Proto") or "").strip().split(",")[0].strip().lower()
    if forwarded_proto in ("http", "https"):
        return forwarded_proto

    forwarded = str(handler.headers.get("Forwarded") or "").strip()
    if forwarded:
        match = re.search(r"proto=([^;\s,]+)", forwarded, re.IGNORECASE)
        if match:
            proto = match.group(1).strip().lower()
            if proto in ("http", "https"):
                return proto

    if str(handler.headers.get("X-Forwarded-Ssl") or "").strip().lower() == "on":
        return "https"
    if str(handler.headers.get("Front-End-Https") or "").strip().lower() == "on":
        return "https"
    return "http"


def build_public_file_url(handler, relative_url):
    host = str(handler.headers.get("Host") or f"127.0.0.1:{PORT}").strip()
    scheme = get_request_scheme(handler)
    return f"{scheme}://{host}{relative_url}"


def get_dashboard_cache_key(start_date_text, end_date_text, limit):
    return f"{start_date_text}:{end_date_text}:{int(limit)}"


def get_cached_dashboard_payload(start_date_text, end_date_text, limit):
    if DASHBOARD_CACHE_TTL_SECONDS <= 0:
        return None
    cache_key = get_dashboard_cache_key(start_date_text, end_date_text, limit)
    now_ts = time.time()
    with _DASHBOARD_CACHE_LOCK:
        cached = _DASHBOARD_CACHE.get(cache_key)
        if not cached:
            return None
        if cached.get("expires_at", 0) <= now_ts:
            _DASHBOARD_CACHE.pop(cache_key, None)
            return None
        return cached.get("payload")


def set_cached_dashboard_payload(start_date_text, end_date_text, limit, payload):
    if DASHBOARD_CACHE_TTL_SECONDS <= 0:
        return
    cache_key = get_dashboard_cache_key(start_date_text, end_date_text, limit)
    with _DASHBOARD_CACHE_LOCK:
        _DASHBOARD_CACHE[cache_key] = {
            "payload": payload,
            "expires_at": time.time() + DASHBOARD_CACHE_TTL_SECONDS,
        }


def clear_dashboard_cache():
    with _DASHBOARD_CACHE_LOCK:
        _DASHBOARD_CACHE.clear()


def parse_dashboard_date_text(date_text, field_label):
    text = str(date_text or "").strip()
    if not text:
        raise ValueError(f"{field_label}不能为空")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date(), text
    except ValueError as exc:
        raise ValueError(f"{field_label}格式应为 YYYY-MM-DD") from exc


def resolve_dashboard_date_range(params):
    start_text = str(params.get("start_date", [""])[0] or "").strip()
    end_text = str(params.get("end_date", [""])[0] or "").strip()

    if start_text or end_text:
        start_date, start_text = parse_dashboard_date_text(start_text, "开始日期")
        end_date, end_text = parse_dashboard_date_text(end_text, "结束日期")
    else:
        days = max(1, min(93, to_int(params.get("days", ["7"])[0], 7) or 7))
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
        start_text = start_date.strftime("%Y-%m-%d")
        end_text = end_date.strftime("%Y-%m-%d")

    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")

    day_count = (end_date - start_date).days + 1
    if day_count > 93:
        raise ValueError("日期范围不能超过 93 天")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_text": start_text,
        "end_text": end_text,
        "day_count": day_count,
    }


def cleanup_admin_sessions():
    current_ms = now_ms()
    with ADMIN_SESSION_LOCK:
        expired_tokens = [
            session_token
            for session_token, session in ADMIN_SESSIONS.items()
            if current_ms >= int((session or {}).get("expiresAt") or 0)
        ]
        for session_token in expired_tokens:
            ADMIN_SESSIONS.pop(session_token, None)


def get_admin_session_record(session_token):
    if not session_token:
        return None
    with ADMIN_SESSION_LOCK:
        session = ADMIN_SESSIONS.get(session_token)
        if not session:
            return None
        expires_at = int(session.get("expiresAt") or 0)
        if expires_at and expires_at <= now_ms():
            ADMIN_SESSIONS.pop(session_token, None)
            return None
        return {
            "username": session.get("username") or ADMIN_USERNAME,
            "expiresAt": expires_at,
        }


def create_admin_session(username):
    cleanup_admin_sessions()
    session_token = secrets.token_urlsafe(32)
    expires_at = now_ms() + ADMIN_SESSION_TTL_MS
    with ADMIN_SESSION_LOCK:
        ADMIN_SESSIONS[session_token] = {
            "username": username,
            "expiresAt": expires_at,
        }
    return {
        "token": session_token,
        "username": username,
        "expiresAt": expires_at,
    }


def revoke_admin_session(session_token):
    if session_token:
        with ADMIN_SESSION_LOCK:
            ADMIN_SESSIONS.pop(session_token, None)


def verify_admin_login(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def check_user_active(user_row):
    if int(user_row.get("status") or 1) == 0:
        raise PermissionError("该账户已被停用，请联系管理员")


def make_profile(payload, headers):
    return {
        "nickName": payload.get("nickName") or payload.get("nick_name") or "",
        "avatarUrl": payload.get("avatarUrl") or payload.get("avatar_url") or "",
        "account": payload.get("account") or "",
        "beastId": payload.get("beastId") or payload.get("beast_id") or "",
        "phone": payload.get("phone") or "",
        "email": payload.get("email") or "",
        "openid": headers.get("openid") or payload.get("openid") or "",
    }


def get_public_orders_cache(key):
    with _PUBLIC_ORDERS_CACHE_LOCK:
        entry = _PUBLIC_ORDERS_CACHE.get(key)
        if entry and time.time() < entry["exp"]:
            return entry["data"]
        return None


def set_public_orders_cache(key, data):
    with _PUBLIC_ORDERS_CACHE_LOCK:
        _PUBLIC_ORDERS_CACHE[key] = {"data": data, "exp": time.time() + _PUBLIC_ORDERS_CACHE_TTL}


def clear_public_orders_cache():
    with _PUBLIC_ORDERS_CACHE_LOCK:
        _PUBLIC_ORDERS_CACHE.clear()


def _check_required_env():
    errors = []
    if not ADMIN_PASSWORD:
        errors.append("FKS_ADMIN_PASSWORD 未设置（不允许空密码运行）")
    if not os.environ.get("MYSQL_PASSWORD", "").strip():
        errors.append("MYSQL_PASSWORD 未设置")
    if errors:
        for err in errors:
            print(f"[FATAL] {err}", flush=True)
        raise SystemExit("请在 .env 或环境变量中设置上述必需配置后再启动。")
