from __future__ import annotations

import base64
import re
import threading
import time
from typing import Any

from api_runtime import logger

_CW_WX_CONFIG = {
    "appid": "wx27a18e6dcb0db741",
    "bundleid": "com.caike.lomo",
    "scope": "snsapi_userinfo",
    "state": "",
    "pass_ticket": "",
}
_CW_LOGIN_DOMAIN = "android-api.lucklyworld.com"
_CW_PKG = "com.caike.lomo"
_CW_VER = "4.5.0"
_CW_CHANNEL = "official"
_CW_CH_CODE = "403005"

QR_SESSIONS: dict[str, dict[str, Any]] = {}
QR_LOCK = threading.Lock()
QR_SESSION_TTL = 180

GEM_BALANCE_CACHE: dict[str, tuple[int, float]] = {}
GEM_CACHE_TTL = 30


def qr_fetch_image(q_uuid: str) -> bytes:
    import requests as _req

    hdrs = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
        "accept": "image/avif,image/webp,image/apng,image/png,image/jpeg,*/*;q=0.8",
        "referer": "https://open.weixin.qq.com/",
    }
    response = _req.get(f"https://open.weixin.qq.com/connect/qrcode/{q_uuid}", headers=hdrs, timeout=15)
    response.raise_for_status()
    return response.content


def qr_fetch_uuid() -> str:
    import requests as _req

    hdrs = {
        "user-agent": (
            "Mozilla/5.0 (Linux; Android 12; BVL-AN16 Build/HUAWEIBVL-AN16; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 "
            "Mobile Safari/537.36 MicroMessenger/8.0.47.2560"
        ),
        "Host": "open.weixin.qq.com",
    }
    response = _req.get(
        "https://open.weixin.qq.com/connect/app/qrconnect",
        params=_CW_WX_CONFIG,
        headers=hdrs,
        timeout=20,
    )
    response.raise_for_status()
    match = re.search(r'uuid:\s*"([^"]+)"', response.text or "")
    if match:
        return match.group(1)
    raise ValueError("无法从微信响应中提取 uuid")


def qr_poll_and_login(session_id: str, q_uuid: str):
    import hashlib
    import hmac as _hmac
    import random as _rand
    import requests as _req
    import string as _str

    hdrs = {
        "user-agent": "Mozilla/5.0 MicroMessenger/8.0.47.2560",
        "Host": "long.open.weixin.qq.com",
    }
    params = {"uuid": q_uuid, "f": "url", "_": int(time.time() * 1000)}
    deadline = time.time() + QR_SESSION_TTL

    while time.time() < deadline:
        try:
            response = _req.get("https://long.open.weixin.qq.com/connect/l/qrconnect", params=params, headers=hdrs, timeout=15)
            if "oauth?code=" in response.text:
                code = response.text.split("oauth?code=")[1].split("&")[0]
                dev_id = hashlib.sha1("".join(_rand.choices(_str.ascii_lowercase + _str.digits, k=20)).encode()).hexdigest()
                and_id = "".join(_rand.choices(_str.ascii_lowercase + _str.digits, k=16))
                login_hdrs = {
                    "User-Agent": f"{_CW_PKG}/{_CW_VER} (Linux; U; Android 12; zh-cn) ({_CW_CHANNEL}; {_CW_CH_CODE})",
                    "packageId": _CW_PKG,
                    "version": _CW_VER,
                    "channel": _CW_CHANNEL,
                    "Accept-Encoding": "gzip",
                    "deviceId": dev_id,
                    "androidId": and_id,
                    "IMEI": "",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Host": _CW_LOGIN_DOMAIN,
                    "Connection": "Keep-Alive",
                }
                login_params = {"uid": "", "version": _CW_VER}
                cw_uid = cw_token = None
                for path in ["/api/auth/wx", "/v9/api/auth/wx", "/v11/api/auth/wx"]:
                    for data in [
                        {"credential": code},
                        {"credential": code, "deviceName": "HONOR BVL-AN16"},
                        {"code": code},
                        {"code": code, "deviceName": "HONOR BVL-AN16"},
                    ]:
                        try:
                            resp = _req.post(f"https://{_CW_LOGIN_DOMAIN}{path}", params=login_params, headers=login_hdrs, data=data, timeout=20)
                            payload = resp.json() if resp.text else {}
                            payload_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
                            cw_token = payload.get("token") or payload.get("accessToken") or payload_data.get("token") or payload_data.get("accessToken")
                            cw_uid = payload.get("userId") or payload.get("uid") or payload.get("user_id") or payload_data.get("userId") or payload_data.get("uid") or payload_data.get("user_id")
                            if cw_token and cw_uid:
                                break
                        except Exception:
                            pass
                    if cw_token and cw_uid:
                        break
                with QR_LOCK:
                    if session_id in QR_SESSIONS:
                        if cw_token and cw_uid:
                            QR_SESSIONS[session_id].update({"status": "success", "userId": str(cw_uid), "token": cw_token})
                        else:
                            QR_SESSIONS[session_id].update({"status": "error", "error": "微信 code 换取潮玩 token 失败"})
                return
        except Exception:
            pass
        time.sleep(2)

    with QR_LOCK:
        if session_id in QR_SESSIONS:
            QR_SESSIONS[session_id]["status"] = "timeout"


def fetch_live_gem_balance(user_id: str, token: str, token_type: str = "fks") -> int | None:
    import hashlib
    import hmac as _hmac
    from urllib.parse import quote

    import certifi as _certifi
    import requests as _req

    sign_key = "BHbE9oCgl58NUz5oJVDUFMLJO9vGQnvdv0Lem3315wQG8laB4dGcxIXFLfDsInHTa"
    device_id = "d6ccb5916deec12a570660d326a1ba59162045e3"
    android_id = "333c86058490a30b"
    package_id = "com.caike.union"
    version = "6.1.1"
    channel = "90033"
    host = "fks-api.lucklyworld.com"
    path = "/v11/api/market/index"

    ua = (
        "com.caike.lomo/4.5.0 (Linux; U; Android 12; zh-cn) (official; 403005)"
        if str(token_type).lower() == "cw"
        else f"{package_id}/{version}-{channel} Dalvik/2.1.0 (Linux; U; Android 12; BVL-AN16 Build/68e417b.1)"
    )

    cache_key = f"{user_id}:{token_type}"
    cached = GEM_BALANCE_CACHE.get(cache_key)
    if cached and time.time() < cached[1]:
        return cached[0]

    data = {"childrenId": "1-1", "productType": "", "extraParam": ""}
    parameter = f"uid={user_id}&version={version}"
    ts = str(round(time.time() * 1000))
    body_str = "&".join([f"{k}={quote(str(v), safe='')}" for k, v in data.items()])
    body_md5 = hashlib.md5(body_str.encode()).hexdigest()
    mes = (
        f"post|{path}|{parameter}|{ts}|"
        f"deviceId={device_id}&androidId={android_id}&userId={user_id}&token={token}"
        f"&packageId={package_id}&version={version}&channel={channel}|{body_md5}"
    )
    sign = _hmac.new(sign_key.encode(), mes.encode(), hashlib.sha256).hexdigest()

    url = f"https://{host}{path}?{parameter}"
    headers = {
        "Host": host,
        "User-Agent": ua,
        "packageId": package_id,
        "version": version,
        "channel": channel,
        "deviceId": device_id,
        "androidId": android_id,
        "userId": user_id,
        "token": token,
        "IMEI": "",
        "ts": ts,
        "sign": sign,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        response = _req.post(url, data=data, headers=headers, timeout=15, verify=_certifi.where())
        payload = response.json()
        if payload.get("errorCode"):
            return None
        qty = (payload.get("turnInfo") or {}).get("qty")
        if qty is None:
            return None
        balance = max(0, int(float(qty)))
        GEM_BALANCE_CACHE[cache_key] = (balance, time.time() + GEM_CACHE_TTL)
        return balance
    except Exception as exc:
        logger.warning("fetch_live_gem_balance failed: %s", exc)
        return None
