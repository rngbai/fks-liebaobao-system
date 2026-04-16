# 单文件可拷走运行；仅需同目录 config.py（userId/token）及 requests、certifi
# 砂砾交易日志里 type=2 视为「出售」（若与游戏内显示相反，改 TYPE_SELL）
import hashlib
import hmac
import json
import sys
import threading
import time
from datetime import datetime, timedelta

import certifi
import requests

from config import token, userId

# —— 以下自 api_common 内联，避免依赖 notify_utils / 整包 ——
deviceId = "d6ccb5916deec12a570660d326a1ba59162045e3"
androidId = "333c86058490a30b"
packageId = "com.caike.union"
version = "6.1.8"
channel = "90033"
KEY = "BHbE9oCgl58NUz5oJVDUFMLJO9vGQnvdv0Lem3315wQG8laB4dGcxIXFLfDsInHTa"

mysession = requests.session()
_token_expired_notified = False
_token_expired_lock = threading.Lock()

PATH = "/v11/api/sand/trade/logs"
TYPE_SELL = 2
DEFAULT_VERIFY_MINUTES = 10


class TokenExpiredError(Exception):
    pass


def generate_hmac_sha256(key, message):
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def _build_common_headers(uid, tk, ts, sign, content_type=None):
    headers = {
        "Host": "fks-api.lucklyworld.com",
        "User-Agent": f"{packageId}/{version}-{channel} Dalvik/2.1.0 (Linux; U; Android 12; BVL-AN16 Build/68e417b.1)",
        "packageId": packageId,
        "version": version,
        "channel": channel,
        "deviceId": deviceId,
        "androidId": androidId,
        "userId": uid,
        "token": tk,
        "IMEI": "",
        "ts": ts,
        "sign": sign,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def check_token_valid(response_dict, uid):
    global _token_expired_notified
    if response_dict and (
        response_dict.get("errorCode") == 401
        or "请重新登录" in response_dict.get("message", "")
    ):
        msg = f"CRITICAL: 用户[{uid}] Token 已失效/被挤号！请更新 Token。"
        with _token_expired_lock:
            if not _token_expired_notified:
                _token_expired_notified = True
                print(msg, file=sys.stderr)
        raise TokenExpiredError(msg)
    return True


def _make_api_request(uid, tk, path, data=None, content_type="application/x-www-form-urlencoded", timeout=2.5):
    parameter = f"uid={uid}&version={version}"
    ts = str(round(time.time() * 1000))
    body_md5 = ""
    if data:
        if isinstance(data, dict):
            body_str = "&".join([f"{k}={v}" for k, v in data.items()])
        elif isinstance(data, str):
            body_str = data
        else:
            body_str = json.dumps(data)
        body_md5 = hashlib.md5(body_str.encode()).hexdigest()
    mes = (
        f"post|{path}|{parameter}|{ts}|"
        f"deviceId={deviceId}&androidId={androidId}&userId={uid}&token={tk}"
        f"&packageId={packageId}&version={version}&channel={channel}|{body_md5}"
    )
    get_sign = generate_hmac_sha256(KEY, mes)
    url = f"https://fks-api.lucklyworld.com{path}?{parameter}"
    headers = _build_common_headers(uid, tk, ts, get_sign, content_type)
    try:
        if data:
            response = mysession.post(
                url, headers=headers, data=data, timeout=timeout, verify=certifi.where()
            )
        else:
            response = mysession.post(url, headers=headers, verify=certifi.where())
        response.raise_for_status()
        response_dict = json.loads(response.text)
        check_token_valid(response_dict, uid)
        return response_dict
    except TokenExpiredError:
        raise
    except Exception as e:
        try:
            response_dict = json.loads(response.text)
            check_token_valid(response_dict, uid)
        except (json.JSONDecodeError, NameError):
            pass
        print(f"[{uid}] API请求异常: {e}", file=sys.stderr)
        return None


def fetch_all_logs(uid, tk):
    page = 1
    out = []
    while True:
        resp = _make_api_request(uid, tk, PATH, data={"page": page}, timeout=10)
        if not resp:
            break
        rows = resp.get("list") or []
        out.extend(rows)
        if not resp.get("hasMore"):
            break
        page = int(resp.get("next") or (page + 1))
    return out


def normalize_amount(value):
    text = str(value).strip()
    try:
        return str(int(float(text)))
    except Exception:
        return text


def extract_verify_code(datetime_text):
    digits = "".join(ch for ch in str(datetime_text or "") if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else ""


def parse_log_datetime(datetime_text, now=None):
    if not datetime_text or not isinstance(datetime_text, str):
        return None

    now_dt = now or datetime.now()
    try:
        month_day, hms = datetime_text.strip().split(" ")
        month, day = [int(item) for item in month_day.split(".")]
        hour, minute, second = [int(item) for item in hms.split(":")]
        parsed = datetime(now_dt.year, month, day, hour, minute, second)
        if parsed - now_dt > timedelta(days=1):
            parsed = parsed.replace(year=parsed.year - 1)
        return parsed
    except Exception:
        return None


def enrich_logs(rows, now=None):
    now_dt = now or datetime.now()
    enriched = []
    for row in rows:
        parsed_dt = parse_log_datetime(row.get("datetime"), now_dt)
        item = dict(row)
        item["verifyCode"] = extract_verify_code(row.get("datetime"))
        item["timestamp"] = int(parsed_dt.timestamp() * 1000) if parsed_dt else 0
        enriched.append(item)
    return enriched


def fetch_sell_logs(uid, tk):
    all_rows = fetch_all_logs(uid, tk)
    return [row for row in all_rows if row.get("type") == TYPE_SELL]


def fetch_recent_sell_logs(uid, tk, minutes=DEFAULT_VERIFY_MINUTES, now=None):
    now_dt = now or datetime.now()
    threshold = now_dt - timedelta(minutes=minutes)
    recent_logs = []

    for row in enrich_logs(fetch_sell_logs(uid, tk), now_dt):
        log_ts = row.get("timestamp") or 0
        if not log_ts:
            continue
        parsed_dt = datetime.fromtimestamp(log_ts / 1000)
        if threshold <= parsed_dt <= now_dt:
            recent_logs.append(row)

    recent_logs.sort(key=lambda item: item.get("timestamp", 0), reverse=True)
    return recent_logs


def verify_recent_recharge(uid, tk, amount, verify_code, created_after_ms=None, expire_minutes=DEFAULT_VERIFY_MINUTES, now=None):
    now_dt = now or datetime.now()
    amount_text = normalize_amount(amount)
    verify_code = str(verify_code).strip()
    lower_bound = int(created_after_ms) if created_after_ms else 0
    upper_bound = int(now_dt.timestamp() * 1000)

    recent_logs = fetch_recent_sell_logs(uid, tk, minutes=expire_minutes, now=now_dt)
    matched = None

    for row in recent_logs:
        log_ts = row.get("timestamp") or 0
        if lower_bound and log_ts < lower_bound:
            continue
        if log_ts > upper_bound:
            continue
        if normalize_amount(row.get("amount")) != amount_text:
            continue
        if row.get("verifyCode") != verify_code:
            continue
        matched = row
        break

    return {
        "ok": bool(matched),
        "matched": matched,
        "recentLogs": recent_logs,
        "message": (
            "校验成功"
            if matched
            else f"未匹配到 {expire_minutes} 分钟内金额={amount_text} 且时间后4位={verify_code} 的 type={TYPE_SELL} 记录"
        ),
    }


def main():
    uid = str(userId)
    tk = token

    try:
        if len(sys.argv) >= 2 and sys.argv[1] == "verify":
            if len(sys.argv) < 4:
                print("用法: python select_rockLog.py verify 金额 时间后4位 [创建时间毫秒] [有效分钟]", file=sys.stderr)
                sys.exit(2)
            amount = sys.argv[2]
            verify_code = sys.argv[3]
            created_after_ms = int(sys.argv[4]) if len(sys.argv) >= 5 else None
            expire_minutes = int(sys.argv[5]) if len(sys.argv) >= 6 else DEFAULT_VERIFY_MINUTES
            result = verify_recent_recharge(uid, tk, amount, verify_code, created_after_ms, expire_minutes)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        if len(sys.argv) >= 2 and sys.argv[1] == "recent":
            expire_minutes = int(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_VERIFY_MINUTES
            result = fetch_recent_sell_logs(uid, tk, expire_minutes)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        sells = fetch_sell_logs(uid, tk)
        print(json.dumps(sells, ensure_ascii=False, indent=2))
    except TokenExpiredError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
