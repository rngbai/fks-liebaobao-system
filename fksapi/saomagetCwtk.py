# -*- coding: utf-8 -*-
"""
本脚本做两件事（token 来源不同，不要混用）：

--------------------------------------------------------------------------------
【功能一】获取「潮玩宇宙」登录 token
--------------------------------------------------------------------------------
  - 方式：微信扫码 → login_cw_with_wx_code → 得到 userId + token
  - 域名：android-api.lucklyworld.com（见 CWS_CONFIG）
  - 验活：check_cw_token_expired / is_cw_token_expired（走 /api/user/info）
  - 说明：这是 com.caike.lomo 体系，与方块兽 App 的 token 不是同一套。

--------------------------------------------------------------------------------
【功能二】查「宝石」余额（fks-api 市场接口）
--------------------------------------------------------------------------------
  - 接口：POST …/v11/api/market/index（域名 fks-api.lucklyworld.com）
  - 签名：固定用 MARKET_*（包名 com.caike.union 等），与翻倍乐主程序一致
  - 重点：余额请求里 **只有 User-Agent 会随账号类型切换**，必须配对：

        · 潮玩宇宙 token（本脚本扫码拿到的）→ 必须
          get_gem_balance(..., cw=True)
          请求头 User-Agent = CW_MARKET_USER_AGENT
          （形如：com.caike.lomo/4.3.5 (Linux; …) (official; 403005)）

        · 方块兽 token（翻倍乐里方块兽登录的）→ 必须
          get_gem_balance(..., cw=False)
          请求头 User-Agent = FKS_USER_AGENT
          （形如：com.caike.union/6.1.1-90033 Dalvik/2.1.0 …）

  - 传错 cw：容易 errorCode 或查不到余额；token 与 UA 必须同属一类账号。

--------------------------------------------------------------------------------
通用注意
--------------------------------------------------------------------------------
  - 安全：token 等同登录凭证，勿外传；失效请重新扫码或重新登录。
  - 官方若改版本号，可改 CWS_CONFIG / MARKET_VERSION 或登录 paths。
  - 不依赖 fanbeiGame.py；命令行见文件末尾 _cli 用法说明。
================================================================================
"""

from __future__ import annotations

import gzip
import hashlib
import hmac
import io
import json
import random
import re
import string
import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, Optional
from urllib.parse import quote

import certifi
import requests
from lxml import etree
from PIL import Image, ImageTk

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None
    messagebox = None

# ---------------------------------------------------------------------------
# 功能一：潮玩宇宙 — 微信扫码参数 + 登录/验活配置（android-api）
# ---------------------------------------------------------------------------

CW_WX_CONFIG = {
    "appid": "wx27a18e6dcb0db741",
    "bundleid": "com.caike.lomo",
    "scope": "snsapi_userinfo",
    "state": "",
    "pass_ticket": "",
}

CWS_CONFIG = {
    "CLIENT_ID": "08729c570ebd81df2f377ed7354a165c",
    "PACKAGE_NAME": "com.caike.lomo",
    "PACKAGE_SIGN": "16e32175430a994a35b210d92fc9e4d2fa8ebb44",
    "DEVICE_NAME": "HONOR  BVL-AN16",
    "VERSION": "4.3.5",
    "CHANNEL": "official",
    "CHANNEL_CODE": "403005",
    "SUPERLINK_API_DOMAIN": "api.chaojilianjie.cn",
    "SUPERLINK_VERSION": "4.3.0",
    "TARGET_API_DOMAIN": "android-api.lucklyworld.com",
    "AUTH_ENDPOINT": "/api/auth/link",
    "USER_INFO_ENDPOINT": "/api/user/info",
    "TEST_ENCRYPT": "0",
}

# ---------------------------------------------------------------------------
# 功能二：宝石余额 — fks-api /v11/api/market/index（签名固定，仅 UA 区分账号）
# ---------------------------------------------------------------------------

MARKET_SIGN_KEY = "BHbE9oCgl58NUz5oJVDUFMLJO9vGQnvdv0Lem3315wQG8laB4dGcxIXFLfDsInHTa"
MARKET_DEVICE_ID = "d6ccb5916deec12a570660d326a1ba59162045e3"
MARKET_ANDROID_ID = "333c86058490a30b"
MARKET_PACKAGE_ID = "com.caike.union"
MARKET_VERSION = "6.1.1"
MARKET_CHANNEL = "90033"

# 余额接口 get_gem_balance(..., cw=False) 时使用 — 对应「方块兽」token
FKS_USER_AGENT = (
    f"{MARKET_PACKAGE_ID}/{MARKET_VERSION}-{MARKET_CHANNEL} "
    "Dalvik/2.1.0 (Linux; U; Android 12; BVL-AN16 Build/68e417b.1)"
)
# 余额接口 get_gem_balance(..., cw=True) 时使用 — 对应「潮玩宇宙」token（本脚本扫码）
CW_MARKET_USER_AGENT = "com.caike.lomo/4.3.5 (Linux; U; Android 12; zh-cn) (official; 403005)"

MARKET_API_HOST = "fks-api.lucklyworld.com"
MARKET_INDEX_PATH = "/v11/api/market/index"
GEM_CHILDREN_ID = "1-1"


def _market_hmac_sha256(key: str, message: str) -> str:
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def _market_build_headers(
    user_id: str,
    token: str,
    ts: str,
    sign: str,
    content_type: str,
    user_agent: str,
) -> Dict[str, str]:
    return {
        "Host": MARKET_API_HOST,
        "User-Agent": user_agent,
        "packageId": MARKET_PACKAGE_ID,
        "version": MARKET_VERSION,
        "channel": MARKET_CHANNEL,
        "deviceId": MARKET_DEVICE_ID,
        "androidId": MARKET_ANDROID_ID,
        "userId": user_id,
        "token": token,
        "IMEI": "",
        "ts": ts,
        "sign": sign,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": content_type,
    }


def _market_post_signed(
    user_id: str,
    token: str,
    path: str,
    data: Dict[str, Any],
    *,
    user_agent: str,
    timeout: float,
) -> Optional[Dict[str, Any]]:
    """签名仅依赖 MARKET_* 固定字段；user_agent 须与 token 类型匹配（见模块说明）。"""
    parameter = f"uid={user_id}&version={MARKET_VERSION}"
    ts = str(round(time.time() * 1000))
    body_str = "&".join([f"{k}={quote(str(v), safe='')}" for k, v in data.items()])
    body_md5 = hashlib.md5(body_str.encode()).hexdigest()
    mes = (
        f"post|{path}|{parameter}|{ts}|"
        f"deviceId={MARKET_DEVICE_ID}&androidId={MARKET_ANDROID_ID}&userId={user_id}&token={token}"
        f"&packageId={MARKET_PACKAGE_ID}&version={MARKET_VERSION}&channel={MARKET_CHANNEL}|{body_md5}"
    )
    sign = _market_hmac_sha256(MARKET_SIGN_KEY, mes)
    url = f"https://{MARKET_API_HOST}{path}?{parameter}"
    headers = _market_build_headers(user_id, token, ts, sign, "application/x-www-form-urlencoded", user_agent)

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


def fetch_market_index(
    user_id: str,
    token: str,
    *,
    cw: bool = False,
    children_id: str = GEM_CHILDREN_ID,
    product_type: str = "",
    extra_param: str = "",
    timeout: float = 15.0,
) -> Optional[Dict[str, Any]]:
    """
    请求市场 index（宝石等）。cw 决定 User-Agent，必须与 token 来源一致：
    cw=True → CW_MARKET_USER_AGENT（潮玩 token）；cw=False → FKS_USER_AGENT（方块兽 token）。
    """
    ua = CW_MARKET_USER_AGENT if cw else FKS_USER_AGENT
    data = {
        "childrenId": str(children_id),
        "productType": str(product_type),
        "extraParam": str(extra_param),
    }
    return _market_post_signed(user_id, token, MARKET_INDEX_PATH, data, user_agent=ua, timeout=timeout)


def get_gem_balance(
    user_id: str,
    token: str,
    *,
    cw: bool = False,
    timeout: float = 15.0,
) -> Optional[int]:
    """
    返回「宝石」余额（turnInfo.qty）。失败返回 None。

    关键参数 cw（选错会导致接口报错或查不到）：
      cw=True  — 潮玩宇宙 token：请求里使用 CW_MARKET_USER_AGENT（本脚本扫码结果请传 True）。
      cw=False — 方块兽 token：请求里使用 FKS_USER_AGENT。
    """
    resp = fetch_market_index(user_id, token, cw=cw, timeout=timeout)
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


def generate_device_id() -> str:
    """登录 android-api 时用的随机 deviceId（与下方 MARKET_* 固定设备无关）。"""
    random_string = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
    return hashlib.sha1(random_string.encode()).hexdigest()


def generate_android_id() -> str:
    """登录 android-api 时用的随机 androidId。"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


# --- 功能一：微信扫码拉码、轮询 code、login_cw_with_wx_code 换潮玩 token ---


def fetch_qr_code(q: Queue, wx_config: dict | None = None) -> None:
    """后台线程：拉取微信二维码图片与 uuid，放入队列 (Image|None, str|None)。"""
    cfg = (wx_config or CW_WX_CONFIG).copy()
    try:
        headers = {
            "user-agent": (
                "Mozilla/5.0 (Linux; Android 9; PBBT00 Build/PPR1.180610.011; wv) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/70.0.3538.110 "
                "Mobile Safari/537.36 MMWEBID/3625 MicroMessenger/7.0.17.1720(0x27001134) "
                "Process/tools WeChat/arm32 NetType/4G Language/zh_CN ABI/arm64"
            ),
            "Host": "open.weixin.qq.com",
            "Connection": "Keep-Alive",
        }
        response = requests.get(
            "http://open.weixin.qq.com/connect/app/qrconnect",
            params=cfg,
            headers=headers,
            timeout=20,
        )
        if response.status_code != 200:
            q.put((None, None))
            return
        uuid_qrcode = None
        try:
            m = re.search(r'uuid:\s*"([^"]+)"', response.text or "")
            if m:
                uuid_qrcode = m.group(1)
        except Exception:
            uuid_qrcode = None
        if not uuid_qrcode:
            try:
                html = etree.HTML(response.text)
                uuid_elements = html.xpath("/html/body/div/script[1]/text()")
                if uuid_elements:
                    uuid_qrcode = uuid_elements[0].split('uuid: "')[1].split('",')[0]
            except Exception:
                uuid_qrcode = None
        if not uuid_qrcode:
            q.put((None, None))
            return
        cookies = {"__CURRENT_TOKEN__": ""}
        headers1 = {
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
            ),
            "accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,image/apng,*/*;q=0.8"
            ),
        }
        response = requests.get(
            f"https://open.weixin.qq.com/connect/qrcode/{uuid_qrcode}",
            cookies=cookies,
            headers=headers1,
            timeout=20,
        )
        if response.status_code != 200:
            q.put((None, None))
            return
        data_stream = io.BytesIO(response.content)
        roi_img = Image.open(data_stream)
        q.put((roi_img, uuid_qrcode))
    except Exception as e:
        print(f"获取二维码失败: {e}")
        q.put((None, None))


def poll_wechat_qr(uuid_qrcode: str, callback, timeout: int = 120) -> None:
    """轮询微信扫码结果；callback(status, data) status 为 success|timeout。"""
    headers = {
        "user-agent": (
            "Mozilla/5.0 (Linux; Android 9; PBBT00 Build/PPR1.180610.011; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/70.0.3538.110 "
            "Mobile Safari/537.36 MMWEBID/3625 MicroMessenger/7.0.17.1720(0x27001134) "
            "Process/tools WeChat/arm32 NetType/4G Language/zh_CN ABI/arm64"
        ),
        "Host": "long.open.weixin.qq.com",
    }
    params = {"uuid": uuid_qrcode, "f": "url", "_": int(time.time() * 1000)}
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            callback("timeout", None)
            return
        try:
            response = requests.get(
                "https://long.open.weixin.qq.com/connect/l/qrconnect",
                params=params,
                headers=headers,
                timeout=15,
            )
            ss = response.text
            if "oauth?code=" in ss:
                sss = ss.split("oauth?code=")[1].split("&")[0]
                callback("success", sss)
                return
            time.sleep(2)
        except Exception as e:
            print(f"轮询失败: {e}")
            time.sleep(2)


def login_cw_with_wx_code(code: str):
    """
    【功能一】用微信返回的 oauth code 换潮玩宇宙 userId + token（android-api 多路径重试）。
    返回: (ok, user_id, token, err_msg)
    """
    device_id = generate_device_id()
    android_id = generate_android_id()
    device_name = CWS_CONFIG.get("DEVICE_NAME") or "HONOR  BVL-AN16"
    package_id = CWS_CONFIG.get("PACKAGE_NAME") or "com.caike.lomo"
    ver = CWS_CONFIG.get("VERSION") or "4.3.5"
    ch = CWS_CONFIG.get("CHANNEL") or "official"
    ch_code = CWS_CONFIG.get("CHANNEL_CODE") or "403005"
    base = f"https://{CWS_CONFIG.get('TARGET_API_DOMAIN') or 'android-api.lucklyworld.com'}"
    paths = ["/api/auth/wx", "/v9/api/auth/wx", "/v11/api/auth/wx"]
    payloads = [
        {"credential": code},
        {"credential": code, "deviceName": device_name},
        {"code": code},
        {"code": code, "deviceName": device_name},
    ]
    headers = {
        "User-Agent": f"{package_id}/{ver} (Linux; U; Android 12; zh-cn) (official; {ch_code})",
        "packageId": package_id,
        "version": ver,
        "channel": ch,
        "Accept-Encoding": "gzip",
        "deviceId": device_id,
        "androidId": android_id,
        "IMEI": "",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": (CWS_CONFIG.get("TARGET_API_DOMAIN") or "android-api.lucklyworld.com"),
        "Connection": "Keep-Alive",
    }
    params = {"uid": "", "version": ver}
    last_err = None
    for p in paths:
        for data in payloads:
            try:
                res = requests.post(base + p, params=params, headers=headers, data=data, timeout=20)
                try:
                    j = res.json()
                except Exception:
                    j = None
                if isinstance(j, dict):
                    token = j.get("token")
                    user_id = j.get("userId")
                    if isinstance(j.get("data"), dict) and (not token or not user_id):
                        token = token or j["data"].get("token")
                        user_id = user_id or j["data"].get("userId")
                    if token and user_id:
                        return True, user_id, token, None
                last_err = f"{res.status_code} {res.text}".strip()
            except Exception as e:
                last_err = str(e)
    return False, None, None, last_err or "登录失败"


def _parse_user_info_response(resp: requests.Response):
    """尝试解析用户信息 JSON（支持 gzip）。"""
    try:
        return resp.json()
    except Exception:
        try:
            raw = gzip.decompress(resp.content)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None


def check_cw_token_expired(user_id, token: str, timeout: float = 15.0) -> dict:
    """
    【功能一】检测潮玩 token 是否仍有效：POST android-api …/api/user/info。

    返回 dict:
      - expired: bool | None  — True 表示已失效；None 表示无法判断
      - valid: bool | None    — True 表示仍可用（与 expired 互斥说明）
      - http_status: int
      - message: str
      - data: 解析后的 JSON（若有）
    """
    uid = str(user_id).strip()
    tok = (token or "").strip()
    out = {
        "expired": None,
        "valid": None,
        "http_status": 0,
        "message": "",
        "data": None,
    }
    if not uid or not tok:
        out["expired"] = True
        out["valid"] = False
        out["message"] = "userId 或 token 为空"
        return out

    device_id = generate_device_id()
    android_id = generate_android_id()
    domain = CWS_CONFIG.get("TARGET_API_DOMAIN") or "android-api.lucklyworld.com"
    ver = CWS_CONFIG.get("VERSION") or "4.3.5"

    base_headers = {
        "User-Agent": (
            f"{CWS_CONFIG['PACKAGE_NAME']}/{CWS_CONFIG['VERSION']} "
            f"(Linux; U; Android 12; zh-cn) ({CWS_CONFIG['CHANNEL']}; {CWS_CONFIG['CHANNEL_CODE']})"
        ),
        "packageId": CWS_CONFIG["PACKAGE_NAME"],
        "version": ver,
        "Channel": CWS_CONFIG["CHANNEL"],
        "deviceId": device_id,
        "androidId": android_id,
        "IMEI": "",
        "test-encrypt": CWS_CONFIG.get("TEST_ENCRYPT", "0"),
        "Host": domain,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    headers = base_headers.copy()
    headers["token"] = tok
    headers["uid"] = uid
    headers["DEVICEID"] = device_id
    headers["ANDROIDID"] = android_id
    headers["oaid"] = ""
    headers["Content-Length"] = "0"

    path = CWS_CONFIG.get("USER_INFO_ENDPOINT") or "/api/user/info"
    url = f"https://{domain}{path}"
    params = {"uid": uid, "version": ver}

    try:
        resp = requests.post(
            url,
            params=params,
            headers=headers,
            data="",
            timeout=timeout,
            verify=certifi.where(),
        )
        out["http_status"] = resp.status_code
        data = _parse_user_info_response(resp)
        out["data"] = data

        if resp.status_code == 401:
            out["expired"] = True
            out["valid"] = False
            out["message"] = "HTTP 401，token 可能已失效"
            return out

        if isinstance(data, dict):
            err_code = data.get("errorCode") or data.get("code")
            msg = (data.get("message") or data.get("msg") or "").strip()
            if err_code == 401 or "请重新登录" in msg or "重新登录" in msg:
                out["expired"] = True
                out["valid"] = False
                out["message"] = msg or "服务端提示需重新登录"
                return out
            if "userId" in data or (isinstance(data.get("data"), dict) and data["data"].get("userId")):
                out["expired"] = False
                out["valid"] = True
                out["message"] = "token 可用"
                return out
            if err_code not in (None, 0) and err_code != 200:
                out["expired"] = True
                out["valid"] = False
                out["message"] = msg or f"业务码 {err_code}"
                return out

        if resp.status_code == 200 and data is not None:
            out["expired"] = False
            out["valid"] = True
            out["message"] = "请求成功（请结合 data 字段自行确认）"
            return out

        out["expired"] = None
        out["valid"] = None
        out["message"] = f"无法判断: HTTP {resp.status_code}"
        return out
    except Exception as e:
        out["message"] = str(e)
        out["expired"] = None
        out["valid"] = None
        return out


def is_cw_token_expired(user_id, token: str, timeout: float = 15.0) -> bool:
    """
    【功能一】简化为 bool：已失效/无法判断则 True（保守），仍有效则 False。
    """
    r = check_cw_token_expired(user_id, token, timeout=timeout)
    if r.get("expired") is True:
        return True
    if r.get("valid") is True:
        return False
    return True


def run_cw_qr_login_gui():
    """
    【功能一】图形界面：扫码登录潮玩宇宙，控制台输出 userId / token；
    随后用【功能二】、cw=True 试查宝石余额（见 get_gem_balance）。
    """
    if tk is None or messagebox is None:
        raise RuntimeError("需要 tkinter 与 PIL 才能使用图形扫码")

    root = tk.Tk()
    root.withdraw()

    def update_ui():
        try:
            try:
                img, uuid_qrcode = q.get_nowait()
            except Empty:
                root.after(100, update_ui)
                return
            if img is None or uuid_qrcode is None:
                messagebox.showerror("错误", "生成二维码失败，请稍后重试")
                root.quit()
                return
            qr_window = tk.Toplevel(root)
            qr_window.title("潮玩宇宙微信扫码登录")
            qr_window.geometry(f"{img.size[0]}x{img.size[1] + 50}")
            qr_photo = ImageTk.PhotoImage(img)
            label = tk.Label(qr_window, image=qr_photo)
            label.photo = qr_photo
            label.pack()
            tk.Label(qr_window, text="等待扫码...", font=("Arial", 12)).pack()

            def timeout_callback():
                try:
                    if qr_window.winfo_exists():
                        messagebox.showwarning("超时", "二维码已过期，请重新生成")
                        qr_window.destroy()
                except tk.TclError:
                    pass

            qr_window.after(120000, timeout_callback)

            def qr_poll_callback(status, data):
                try:
                    if status == "timeout":
                        if qr_window.winfo_exists():
                            messagebox.showwarning("超时", "二维码已过期，请重新生成")
                            qr_window.destroy()
                        return
                    if status != "success" or not data:
                        return
                    print("扫码成功，正在登录潮玩宇宙...")
                    ok, cw_uid, cw_token, err = login_cw_with_wx_code(data)
                    if not ok:
                        messagebox.showerror("失败", err or "潮玩宇宙登录失败")
                        if qr_window.winfo_exists():
                            qr_window.destroy()
                        return
                    print(f"潮玩宇宙登录成功！userId={cw_uid}")
                    print(f"token={cw_token}")
                    # 余额走 fks market；潮玩 token 必须 cw=True（UA 为 CW_MARKET_USER_AGENT）
                    gem = get_gem_balance(str(cw_uid), cw_token, cw=True)
                    if gem is not None:
                        print(f"宝石余额(市场接口, UA=潮玩): {gem}")
                    else:
                        print("宝石余额: 查询失败（网络/业务码，或确认 cw=True 与潮玩 token 一致）")
                    messagebox.showinfo("成功", "登录成功，token 已打印到控制台")
                    if qr_window.winfo_exists():
                        qr_window.destroy()
                    root.quit()
                except tk.TclError:
                    pass

            threading.Thread(target=poll_wechat_qr, args=(uuid_qrcode, qr_poll_callback), daemon=True).start()
        except Exception as e:
            if str(e):
                print(f"更新UI失败: {e}")
            root.after(100, update_ui)

    q: Queue = Queue()
    threading.Thread(target=fetch_qr_code, args=(q, CW_WX_CONFIG), daemon=True).start()
    root.after(100, update_ui)
    root.mainloop()


def _cli():
    import sys

    print(__doc__)
    print(
        "命令行：\n"
        "  python saomagetCwtk.py\n"
        "      → 扫码获取潮玩 token\n"
        "  python saomagetCwtk.py check <userId> <token>\n"
        "      → 验活（功能一，android-api）\n"
        "  python saomagetCwtk.py balance <userId> <token> [cw|fks]\n"
        "      → 宝石余额（功能二）；默认 cw=潮玩 UA，传 fks 则用方块兽 UA\n"
    )
    if len(sys.argv) > 1:
        cmd = sys.argv[1].strip().lower()
        if cmd == "check" and len(sys.argv) >= 4:
            uid, tok = sys.argv[2], sys.argv[3]
            r = check_cw_token_expired(uid, tok)
            print(json.dumps(r, ensure_ascii=False, indent=2))
            sys.exit(0 if r.get("valid") else 1)
        if cmd in ("balance", "gem") and len(sys.argv) >= 4:
            uid, tok = sys.argv[2], sys.argv[3]
            cw = True
            if len(sys.argv) >= 5 and sys.argv[4].strip().lower() in ("0", "fks", "false"):
                cw = False
            g = get_gem_balance(uid, tok, cw=cw)
            print(json.dumps({"gem": g, "cw": cw}, ensure_ascii=False))
            sys.exit(0 if g is not None else 1)
        print("用法见上方。balance 默认使用潮玩 UA(cw)；方块兽 token 请加参数 fks。")
        sys.exit(1)

    run_cw_qr_login_gui()


if __name__ == "__main__":
    _cli()
