# -*- coding: utf-8 -*-
"""
独立模块：仅用于查询「宝石」余额（与 auto_sell_gui._get_gem_qty / exchange_api.get_market_balance 一致）。

- API: POST /v11/api/market/index
- 参数: childrenId=1-1, productType=空, extraParam=空
- 宝石数量: 响应 JSON 中 turnInfo.qty

不依赖本项目 exchange_api / config，可单独复制到其他工程使用。
依赖: requests, certifi（与主项目一致）
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from urllib.parse import quote

import certifi
import requests

# 与 exchange_api 保持一致（签名与 Host 依赖这些常量）
KEY = "BHbE9oCgl58NUz5oJVDUFMLJO9vGQnvdv0Lem3315wQG8laB4dGcxIXFLfDsInHTa"
deviceId = "d6ccb5916deec12a570660d326a1ba59162045e3"
androidId = "333c86058490a30b"
packageId = "com.caike.union"
version = "6.1.1"
channel = "90033"

FKS_USER_AGENT = f"{packageId}/{version}-{channel} Dalvik/2.1.0 (Linux; U; Android 12; BVL-AN16 Build/68e417b.1)"
CW_USER_AGENT = "com.caike.lomo/4.3.5 (Linux; U; Android 12; zh-cn) (official; 403005)"

API_HOST = "fks-api.lucklyworld.com"
MARKET_INDEX_PATH = "/v11/api/market/index"
# 矿石板块 childrenId；该接口返回的 turnInfo.qty 为宝石余额（与现有 GUI 逻辑一致）
GEM_CHILDREN_ID = "1-1"


def _generate_hmac_sha256(key: str, message: str) -> str:
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def _build_headers(
    user_id: str,
    token: str,
    ts: str,
    sign: str,
    content_type: str,
    user_agent: str,
) -> Dict[str, str]:
    return {
        "Host": API_HOST,
        "User-Agent": user_agent,
        "packageId": packageId,
        "version": version,
        "channel": channel,
        "deviceId": deviceId,
        "androidId": androidId,
        "userId": user_id,
        "token": token,
        "IMEI": "",
        "ts": ts,
        "sign": sign,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": content_type,
    }


def _post_signed(
    user_id: str,
    token: str,
    path: str,
    data: Dict[str, Any],
    *,
    user_agent: str,
    timeout: float,
) -> Optional[Dict[str, Any]]:
    parameter = f"uid={user_id}&version={version}"
    ts = str(round(time.time() * 1000))
    body_str = "&".join([f"{k}={quote(str(v), safe='')}" for k, v in data.items()])
    body_md5 = hashlib.md5(body_str.encode()).hexdigest()
    mes = (
        f"post|{path}|{parameter}|{ts}|"
        f"deviceId={deviceId}&androidId={androidId}&userId={user_id}&token={token}"
        f"&packageId={packageId}&version={version}&channel={channel}|{body_md5}"
    )
    sign = _generate_hmac_sha256(KEY, mes)
    url = f"https://{API_HOST}{path}?{parameter}"
    headers = _build_headers(user_id, token, ts, sign, "application/x-www-form-urlencoded", user_agent)

    try:
        r = requests.post(
            url,
            data=data,
            headers=headers,
            timeout=timeout,
            verify=certifi.where(),
        )
    except (requests.RequestException, OSError):
        return None

    try:
        text = r.text.strip() if r.text else ""
        if not text:
            return None
        out = json.loads(text)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None


def _fetch_market_index(
    user_id: str,
    token: str,
    *,
    cw: bool = False,
    children_id: str = GEM_CHILDREN_ID,
    product_type: str = "",
    extra_param: str = "",
    timeout: float = 15.0,
) -> Optional[Dict[str, Any]]:
    ua = CW_USER_AGENT if cw else FKS_USER_AGENT
    data = {
        "childrenId": str(children_id),
        "productType": str(product_type),
        "extraParam": str(extra_param),
    }
    return _post_signed(user_id, token, MARKET_INDEX_PATH, data, user_agent=ua, timeout=timeout)


def get_gem_balance(
    user_id: str,
    token: str,
    *,
    cw: bool = False,
    timeout: float = 15.0,
) -> Optional[int]:
    """
    仅返回宝石余额（非负整数）。token 失效、网络错误或业务 errorCode 时返回 None。

    :param user_id: 用户 ID
    :param token: 登录 token
    :param cw: True 表示潮玩(CW)账号 token，需使用 CW 的 User-Agent；False 为方块兽(FKS)
    """
    resp = _fetch_market_index(user_id, token, cw=cw, timeout=timeout)
    if not resp:
        return None
    if resp.get("errorCode"):
        return None
    turn = resp.get("turnInfo") or {}
    qty = turn.get("qty")
    if qty is None:
        return None
    try:
        return max(0, int(float(qty)))
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    # 示例：请替换为真实账号再测
    _uid = ""
    _tok = ""
    if _uid and _tok:
        print(get_gem_balance(_uid, _tok, cw=False))
    else:
        print("编辑 __main__ 里 _uid/_tok 后可直接运行本文件测试")
