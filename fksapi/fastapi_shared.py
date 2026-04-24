from __future__ import annotations

import json
import threading
import time
from typing import Any

from env_bootstrap import load_local_env

load_local_env()

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from fastapi_service import FastAPIService
from recharge_verify_server import (
    ADMIN_USERNAME,
    PORT,
    _check_required_env,
    clear_dashboard_cache,
    cleanup_admin_sessions,
    create_admin_session,
    get_admin_session_record,
    revoke_admin_session,
)

service = FastAPIService()
_PUBLIC_ORDERS_CACHE: dict[str, dict[str, Any]] = {}
_PUBLIC_ORDERS_CACHE_TTL = 10
_PUBLIC_ORDERS_CACHE_LOCK = threading.Lock()


def get_public_orders_cache(key: str):
    with _PUBLIC_ORDERS_CACHE_LOCK:
        entry = _PUBLIC_ORDERS_CACHE.get(key)
        if entry and time.time() < entry["exp"]:
            return entry["data"]
        return None


def set_public_orders_cache(key: str, data: Any) -> None:
    with _PUBLIC_ORDERS_CACHE_LOCK:
        _PUBLIC_ORDERS_CACHE[key] = {"data": data, "exp": time.time() + _PUBLIC_ORDERS_CACHE_TTL}


def clear_public_orders_cache() -> None:
    with _PUBLIC_ORDERS_CACHE_LOCK:
        _PUBLIC_ORDERS_CACHE.clear()


def ok_payload(data: Any = None, message: str = "success") -> dict[str, Any]:
    return {"ok": True, "message": message, "data": data if data is not None else {}}


def fail_payload(message: str, data: Any = None) -> dict[str, Any]:
    return {"ok": False, "message": message, "data": data if data is not None else {}}


def json_bytes_response(status_code: int, payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload)


def build_public_file_url(request: Request, relative_url: str) -> str:
    forwarded_proto = str(request.headers.get("x-forwarded-proto") or "").strip().split(",")[0].strip().lower()
    if forwarded_proto in ("http", "https"):
        scheme = forwarded_proto
    else:
        forwarded = str(request.headers.get("forwarded") or "").strip()
        proto = ""
        if forwarded:
            for segment in forwarded.split(";"):
                if "proto=" in segment.lower():
                    proto = segment.split("=", 1)[1].strip().lower()
                    break
        if proto in ("http", "https"):
            scheme = proto
        elif str(request.headers.get("x-forwarded-ssl") or "").strip().lower() == "on":
            scheme = "https"
        elif str(request.headers.get("front-end-https") or "").strip().lower() == "on":
            scheme = "https"
        else:
            scheme = request.url.scheme or "http"
    host = str(request.headers.get("host") or f"127.0.0.1:{PORT}").strip()
    return f"{scheme}://{host}{relative_url}"


def get_user_key(request: Request, payload: dict[str, Any] | None = None) -> str:
    payload = payload or {}
    return (
        request.headers.get("x-user-key")
        or request.headers.get("openid")
        or payload.get("user_key")
        or payload.get("openid")
        or request.query_params.get("user_key")
        or request.query_params.get("openid")
        or "local_debug_user"
    )


def get_admin_session(request: Request) -> dict[str, Any] | None:
    cleanup_admin_sessions()
    session_token = str(request.headers.get("x-admin-token") or "").strip()
    session = get_admin_session_record(session_token)
    if not session:
        return None
    return {
        "token": session_token,
        "username": session.get("username") or ADMIN_USERNAME,
        "expiresAt": int(session.get("expiresAt") or 0),
    }


def require_admin(request: Request) -> dict[str, Any]:
    session = get_admin_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="后台未登录或登录已失效")
    return session


async def read_json_payload(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"请求体不是合法 JSON: {exc}") from exc
    return payload or {}


__all__ = [
    "_check_required_env",
    "build_public_file_url",
    "clear_dashboard_cache",
    "clear_public_orders_cache",
    "create_admin_session",
    "fail_payload",
    "get_admin_session",
    "get_public_orders_cache",
    "get_user_key",
    "json_bytes_response",
    "ok_payload",
    "read_json_payload",
    "require_admin",
    "revoke_admin_session",
    "service",
    "set_public_orders_cache",
]
