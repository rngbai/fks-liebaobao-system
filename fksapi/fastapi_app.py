from __future__ import annotations

import base64
import json
import threading
import time
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qs, urlparse

from env_bootstrap import load_local_env

load_local_env()

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from config import token

from db_mysql import (
    FEEDBACK_SCENE_ADMIN_LAYOUT,
    FEEDBACK_SCENE_COMMUNITY_APPLY,
    approve_community_feedback,
    bind_user_inviter,
    build_game_config_payload,
    build_manage_dashboard,
    build_manage_feedback_payload,
    build_manage_guarantee_payload,
    build_manage_home_content_payload,
    build_manage_promotion_payload,
    build_manage_recharge_payload,
    build_manage_transfer_request_payload,
    build_manage_users_payload,
    build_pending_summary,
    build_transfer_state,
    cancel_recharge_order,
    complete_transfer_request,
    create_community_profile,
    create_feedback,
    create_guarantee_order,
    create_recharge_order,
    create_transfer_request,
    delete_community_profile,
    find_recharge_order,
    get_connection,
    get_or_create_user,
    import_manage_users,
    init_database_and_tables,
    list_community_profiles,
    list_public_guarantee_orders,
    mark_recharge_success,
    match_guarantee_order,
    now_ms,
    patch_game_config,
    reject_transfer_request,
    save_game_config,
    save_manage_home_content_payload,
    seller_cancel_pending_guarantee_order,
    seller_confirm_guarantee_order,
    seller_reject_guarantee_order,
    serialize_feedback_row,
    serialize_guarantee_row,
    serialize_manage_feedback_row,
    serialize_transfer_request,
    serialize_wallet,
    update_community_profile,
    update_feedback_status,
    update_user_status,
    delete_user_account,
    buyer_cancel_guarantee_match,
    buyer_upload_guarantee_proof,
)
from fastapi_service import FastAPIService
from recharge_verify_server import (
    ADMIN_PASSWORD,
    ADMIN_SESSION_LOCK,
    ADMIN_SESSIONS,
    ADMIN_SESSION_TTL_MS,
    ADMIN_USERNAME,
    DEFAULT_CANCEL_LIMIT,
    DEFAULT_VERIFY_MINUTES,
    PORT,
    RECEIVER_BEAST_ID,
    RECEIVER_BEAST_NICK,
    _QR_LOCK,
    _QR_SESSION_TTL,
    _QR_SESSIONS,
    _check_required_env,
    _fetch_live_gem_balance,
    _qr_fetch_image,
    _qr_fetch_uuid,
    _qr_poll_and_login,
    check_user_active,
    cleanup_admin_sessions,
    clear_dashboard_cache,
    create_admin_session,
    get_admin_session_record,
    get_cached_dashboard_payload,
    load_admin_asset,
    load_upload_asset,
    logger,
    make_profile,
    resolve_dashboard_date_range,
    revoke_admin_session,
    set_cached_dashboard_payload,
    to_int,
    verify_admin_login,
)
from select_rockLog import TokenExpiredError, fetch_recent_sell_logs, verify_recent_recharge


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
    except Exception as exc:  # pragma: no cover - matches legacy behavior
        raise HTTPException(status_code=400, detail=f"请求体不是合法 JSON: {exc}") from exc
    return payload or {}


def json_bytes_response(status_code: int, payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _check_required_env()
    init_database_and_tables()
    yield


app = FastAPI(
    title="FKS Recharge Verify API",
    version="4.0.0-fastapi",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "openid", "x-user-key", "x-admin-token"],
)


@app.middleware("http")
async def invalidate_caches_on_write(request: Request, call_next):
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path != "/api/manage/login":
        clear_dashboard_cache()
        clear_public_orders_cache()
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content=fail_payload(str(exc.detail or "请求失败")))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=422, content=fail_payload(f"参数校验失败: {exc.errors()}"))
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
@app.get("/admin/{asset_path:path}", include_in_schema=False)
def admin_assets(asset_path: str = ""):
    request_path = "/admin/" + asset_path if asset_path else "/admin/"
    try:
        body, content_type = load_admin_asset(request_path)
        return Response(content=body, media_type=None, headers={"Content-Type": content_type})
    except PermissionError as exc:
        return json_bytes_response(403, fail_payload(str(exc)))
    except FileNotFoundError as exc:
        return json_bytes_response(404, fail_payload(str(exc)))
    except Exception as exc:  # pragma: no cover
        return json_bytes_response(500, fail_payload(f"读取后台页面失败: {exc}"))


@app.get("/uploads/{asset_path:path}", include_in_schema=False)
def upload_assets(asset_path: str):
    request_path = f"/uploads/{asset_path}"
    try:
        body, content_type = load_upload_asset(request_path)
        return Response(content=body, media_type=None, headers={"Content-Type": content_type})
    except PermissionError as exc:
        return json_bytes_response(403, fail_payload(str(exc)))
    except FileNotFoundError as exc:
        return json_bytes_response(404, fail_payload(str(exc)))
    except Exception as exc:  # pragma: no cover
        return json_bytes_response(500, fail_payload(f"读取上传图片失败: {exc}"))


@app.get("/api/manage/auth-check")
def manage_auth_check(request: Request):
    session = get_admin_session(request)
    if session:
        return ok_payload(
            {
                "dashboardPath": "/admin/",
                "username": session.get("username") or ADMIN_USERNAME,
                "expiresAt": session.get("expiresAt") or 0,
            },
            "验证成功",
        )
    return JSONResponse(status_code=401, content=fail_payload("后台未登录或登录已失效"))


@app.get("/api/recharge/health")
def recharge_health():
    return ok_payload(
        {
            "uid": RECEIVER_BEAST_ID,
            "port": PORT,
            "receiverBeastNick": RECEIVER_BEAST_NICK,
            "cancelLimit": DEFAULT_CANCEL_LIMIT,
            "adminPath": "/admin/",
        },
        "recharge verify server is running",
    )


@app.get("/api/recharge/recent")
def recharge_recent(minutes: int = Query(DEFAULT_VERIFY_MINUTES)):
    minutes = max(1, minutes)
    try:
        live_uid, live_tk, live_tk_type, _ = service.get_live_credentials()
        logs = fetch_recent_sell_logs(live_uid, live_tk, minutes=minutes, token_type=live_tk_type)
        return ok_payload({"minutes": minutes, "logs": logs, "count": len(logs)}, "查询成功")
    except TokenExpiredError as exc:
        return JSONResponse(status_code=401, content=fail_payload(str(exc)))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"查询失败: {exc}"))


@app.get("/api/recharge/state")
def recharge_state(request: Request):
    try:
        data = service.get_recharge_state_payload(get_user_key(request))
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取充值状态失败: {exc}"))


@app.get("/api/user/profile")
def user_profile_get(request: Request):
    try:
        data = service.get_user_profile_payload(get_user_key(request))
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取用户资料失败: {exc}"))


@app.get("/api/user/balance")
def user_balance(request: Request):
    try:
        data = service.get_user_profile_payload(get_user_key(request))
        return ok_payload({"gemBalance": data["wallet"]["gemBalance"]}, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取余额失败: {exc}"))


@app.get("/api/user/wallet-records")
def user_wallet_records(request: Request, limit: int = Query(50)):
    limit = max(1, limit)
    try:
        payload = service.get_wallet_records_payload(get_user_key(request), limit=limit)
        return ok_payload(payload, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取宝石流水失败: {exc}"))


@app.get("/api/transfer/state")
def transfer_state(request: Request, limit: int = Query(20)):
    limit = max(1, limit)
    try:
        data = service.get_transfer_state_payload(get_user_key(request), limit=limit)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取转出状态失败: {exc}"))


@app.get("/api/guarantee/list")
def guarantee_list(request: Request, limit: int = Query(20)):
    limit = max(1, limit)
    try:
        data = service.get_guarantee_list_payload(get_user_key(request), limit=limit)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保列表失败: {exc}"))


@app.get("/api/guarantee/detail")
def guarantee_detail(request: Request, order_no: str = Query(""), id: str = Query("")):
    target_order_no = str(order_no or id or "").strip()
    if not target_order_no:
        return fail_payload("缺少担保单号")
    try:
        data = service.get_guarantee_detail_payload(get_user_key(request), target_order_no)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保单失败: {exc}"))


@app.get("/api/feedback/list")
def feedback_list(
    request: Request,
    limit: int = Query(20),
    scene: str = Query(""),
    type: str = Query("", alias="type"),
    mine: str = Query("0"),
):
    limit = max(1, limit)
    mine_only = str(mine or "").strip().lower() in ("1", "true", "yes", "mine")
    if str(scene or "").strip().lower().replace("-", "_") == FEEDBACK_SCENE_COMMUNITY_APPLY:
        mine_only = True
    try:
        data = service.get_feedback_payload(
            get_user_key(request),
            limit=limit,
            mine_only=mine_only,
            feedback_type=str(type or "").strip() or None,
            scene=scene,
        )
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取反馈列表失败: {exc}"))


@app.get("/api/promotion/my")
def promotion_my(request: Request, limit: int = Query(20)):
    limit = max(1, limit)
    try:
        data = service.get_promotion_payload(get_user_key(request), limit=limit)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取推广信息失败: {exc}"))


@app.get("/api/user/pending-summary")
def pending_summary(request: Request):
    try:
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, get_user_key(request))
            data = build_pending_summary(conn, user_row["id"])
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取待办摘要失败: {exc}"))


@app.get("/api/guarantee/public")
def guarantee_public(limit: int = Query(20), pet_name: str | None = Query(None)):
    limit = max(1, limit)
    pet_name = str(pet_name or "").strip() or None
    cache_key = f"{limit}:{pet_name}"
    cached = get_public_orders_cache(cache_key)
    if cached is not None:
        return ok_payload({"orders": cached}, "查询成功")
    try:
        with get_connection(autocommit=False) as conn:
            orders = list_public_guarantee_orders(conn, limit=limit, pet_name=pet_name)
            conn.commit()
        set_public_orders_cache(cache_key, orders)
        return ok_payload({"orders": orders}, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取公开保单失败: {exc}"))


@app.get("/api/home/content")
def home_content():
    try:
        data = service.get_home_content_payload()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取首页内容失败: {exc}"))


@app.get("/api/manage/home-content")
def manage_home_content(_: dict[str, Any] = Depends(require_admin)):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_home_content_payload(conn)
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取首页内容管理数据失败: {exc}"))


@app.get("/api/manage/users")
def manage_users(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_users_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取用户管理数据失败: {exc}"))


@app.get("/api/manage/promotions")
def manage_promotions(
    page: int = Query(1),
    page_size: int = Query(20),
    reward_limit: int = Query(30),
    invitee_limit: int = Query(40),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_promotion_payload(
                conn,
                query=query.strip(),
                status=status.strip(),
                page=max(1, page),
                page_size=max(1, page_size),
                reward_limit=max(1, reward_limit),
                invitee_limit=max(1, invitee_limit),
            )
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取推广管理数据失败: {exc}"))


@app.get("/api/manage/recharges")
def manage_recharges(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_recharge_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取充值记录失败: {exc}"))


@app.get("/api/manage/guarantees")
def manage_guarantees(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_guarantee_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保档案失败: {exc}"))


@app.get("/api/manage/feedbacks")
def manage_feedbacks(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    type: str = Query("", alias="type"),
    scene: str = Query(""),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_feedback_payload(
                conn,
                query=query.strip(),
                status=status.strip(),
                page=max(1, page),
                page_size=max(1, page_size),
                feedback_type=str(type or "").strip() or None,
                scene=scene,
            )
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取反馈档案失败: {exc}"))


@app.get("/api/manage/pending-guarantees")
def manage_pending_guarantees(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_guarantee_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size), pending_only=True)
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保待确认列表失败: {exc}"))


@app.get("/api/manage/transfer-requests")
def manage_transfer_requests(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_transfer_request_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取用户转出申请失败: {exc}"))


@app.get("/api/manage/pending-feedbacks")
def manage_pending_feedbacks(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    type: str = Query("", alias="type"),
    scene: str = Query(""),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_feedback_payload(
                conn,
                query=query.strip(),
                status=status.strip(),
                page=max(1, page),
                page_size=max(1, page_size),
                pending_only=True,
                feedback_type=str(type or "").strip() or None,
                scene=scene,
            )
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取待处理反馈失败: {exc}"))


@app.get("/api/manage/token-config")
def manage_token_config(_: dict[str, Any] = Depends(require_admin)):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_game_config_payload(conn, RECEIVER_BEAST_ID, token, env_user_name=RECEIVER_BEAST_NICK)
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取游戏凭证失败: {exc}"))


@app.get("/api/manage/gem-balance")
def manage_gem_balance(_: dict[str, Any] = Depends(require_admin)):
    try:
        with get_connection(autocommit=False) as conn:
            uid, tk, tk_type, user_name = service.get_live_credentials(conn)
            conn.commit()
        if not uid or not tk:
            return fail_payload("游戏凭证未配置，请先在 Token 管理中设置")
        balance = _fetch_live_gem_balance(uid, tk, tk_type)
        if balance is None:
            return fail_payload("Token 已失效或游戏接口异常，请刷新 Token")
        return ok_payload(
            {
                "balance": balance,
                "userId": uid,
                "userName": user_name,
                "tokenType": tk_type,
                "cached": False,
            },
            f"宝石余额查询成功：{balance}",
        )
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"查询余额失败: {exc}"))


@app.get("/api/manage/token-config/qr-status")
def manage_qr_status(request: Request, session: str = Query(""), _: dict[str, Any] = Depends(require_admin)):
    if not session:
        return JSONResponse(status_code=400, content=fail_payload("缺少 session 参数"))
    with _QR_LOCK:
        sess = _QR_SESSIONS.get(session)
    if not sess:
        return JSONResponse(status_code=404, content=fail_payload("会话不存在或已过期"))
    status = sess.get("status", "waiting")
    if status == "success":
        try:
            with get_connection(autocommit=False) as conn:
                cfg = save_game_config(conn, sess["userId"], sess["token"], token_type="cw")
                conn.commit()
            with _QR_LOCK:
                _QR_SESSIONS.pop(session, None)
            return ok_payload({**cfg, "autoSaved": True}, "扫码登录成功，凭证已自动保存")
        except Exception as exc:
            return json_bytes_response(500, fail_payload(f"保存凭证失败: {exc}"))
    if status == "error":
        return fail_payload(sess.get("error", "登录失败"))
    if status == "timeout":
        with _QR_LOCK:
            _QR_SESSIONS.pop(session, None)
        return fail_payload("二维码已过期")
    return ok_payload({"status": "waiting"}, "等待扫码")


@app.get("/api/manage/community")
def manage_community(
    category: str | None = Query(None),
    sub_tab: str | None = Query(None),
    active_only: int = Query(0),
    _: dict[str, Any] = Depends(require_admin),
):
    try:
        with get_connection() as conn:
            rows = list_community_profiles(conn, category=category, sub_tab=sub_tab, active_only=active_only == 1)
        return ok_payload({"list": rows, "total": len(rows)}, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"查询社区名流失败: {exc}"))


@app.get("/api/community")
@app.get("/api/community/")
def public_community(category: str | None = Query(None), sub_tab: str | None = Query(None)):
    category = str(category or "").strip() or None
    sub_tab = str(sub_tab or "").strip() or None
    try:
        with get_connection() as conn:
            rows = list_community_profiles(conn, category=category, sub_tab=sub_tab, active_only=True)
        return ok_payload({"list": rows}, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"查询社区名流失败: {exc}"))


@app.get("/api/manage/dashboard")
def manage_dashboard(request: Request, limit: int = Query(20), _: dict[str, Any] = Depends(require_admin)):
    limit = max(0, limit)
    try:
        dashboard_range = resolve_dashboard_date_range(parse_qs(urlparse(str(request.url)).query))
        cached_payload = get_cached_dashboard_payload(
            dashboard_range["start_text"],
            dashboard_range["end_text"],
            limit,
        )
        if cached_payload is not None:
            return ok_payload(cached_payload, "查询成功")

        with get_connection(autocommit=False) as conn:
            data = build_manage_dashboard(
                conn,
                days=dashboard_range["day_count"],
                limit=limit,
                start_date=dashboard_range["start_text"],
                end_date=dashboard_range["end_text"],
            )
            conn.commit()
        set_cached_dashboard_payload(
            dashboard_range["start_text"],
            dashboard_range["end_text"],
            limit,
            data,
        )
        return ok_payload(data, "查询成功")
    except ValueError as exc:
        return JSONResponse(status_code=400, content=fail_payload(str(exc)))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取管理台数据失败: {exc}"))


@app.post("/api/manage/login")
async def manage_login(request: Request):
    payload = await read_json_payload(request)
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        return JSONResponse(status_code=400, content=fail_payload("请输入后台账号和密码"))
    if not verify_admin_login(username, password):
        return JSONResponse(status_code=401, content=fail_payload("后台账号或密码错误"))
    session = create_admin_session(username)
    return ok_payload(
        {
            "token": session.get("token") or "",
            "username": session.get("username") or username,
            "expiresAt": session.get("expiresAt") or 0,
        },
        "登录成功",
    )


@app.post("/api/manage/logout")
async def manage_logout(request: Request):
    revoke_admin_session(str(request.headers.get("x-admin-token") or "").strip())
    return ok_payload({}, "已退出登录")


@app.post("/api/manage/users/import")
async def manage_users_import(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    raw_text = str(payload.get("text") or payload.get("raw_text") or payload.get("content") or "").strip()
    try:
        with get_connection(autocommit=False) as conn:
            result = import_manage_users(conn, raw_text)
            latest = build_manage_users_payload(conn, page=1, page_size=20)
            conn.commit()
        return ok_payload({"result": result, "latest": latest}, "用户导入完成")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"导入用户失败: {exc}"))


@app.post("/api/manage/users/ban")
async def manage_users_ban(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    user_id = to_int(payload.get("user_id") or payload.get("userId"), 0)
    status = payload.get("status")
    if user_id <= 0:
        return fail_payload("缺少用户编号")
    try:
        with get_connection(autocommit=False) as conn:
            result = update_user_status(conn, user_id, status)
        return ok_payload(result, f"用户已{'恢复正常' if result['status'] else '拉黑'}")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"操作失败: {exc}"))


@app.post("/api/manage/users/delete")
async def manage_users_delete(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    user_id = to_int(payload.get("user_id") or payload.get("userId"), 0)
    if user_id <= 0:
        return fail_payload("缺少用户编号")
    try:
        with get_connection(autocommit=False) as conn:
            result = delete_user_account(conn, user_id)
        return ok_payload(result, f"用户 {result.get('nickName', '')} 已删除")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"删除用户失败: {exc}"))


@app.post("/api/manage/home-content")
async def manage_home_content_save(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    content_payload = payload.get("content") if isinstance(payload.get("content"), dict) else payload
    try:
        with get_connection(autocommit=False) as conn:
            data = save_manage_home_content_payload(conn, content_payload)
            conn.commit()
        return ok_payload(data, "首页内容已保存")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"保存首页内容失败: {exc}"))


@app.post("/api/promotion/bind")
async def promotion_bind(request: Request):
    payload = await read_json_payload(request)
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    invite_code = str(payload.get("invite_code") or payload.get("inviteCode") or payload.get("ref") or "").strip()
    try:
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            user_row = bind_user_inviter(conn, user_row, invite_code)
            data = build_promotion_payload(conn, user_row, limit=max(1, to_int(payload.get("limit"), 20)))
            conn.commit()
        return ok_payload(data, "推荐码绑定成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"绑定推荐码失败: {exc}"))


@app.post("/api/user/profile")
async def user_profile_post(request: Request):
    payload = await read_json_payload(request)
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        data = service.get_user_profile_payload(user_key, profile)
        return ok_payload(data, "保存成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"保存用户资料失败: {exc}"))


@app.post("/api/feedback/create")
async def feedback_create(request: Request):
    payload = await read_json_payload(request)
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    feedback_type = str(payload.get("type") or payload.get("feedback_type") or "其他").strip()
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or payload.get("desc") or "").strip()
    contact = str(payload.get("contact") or "").strip()
    scene = str(payload.get("scene") or "").strip()
    extra_context = {
        "category": payload.get("category"),
        "category_label": payload.get("category_label") or payload.get("categoryLabel"),
        "sub_tab": payload.get("sub_tab") or payload.get("subTab"),
    }
    limit = max(1, to_int(payload.get("limit"), 20))
    normalized_scene = str(scene or "").strip().lower().replace("-", "_")
    try:
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            feedback_row = create_feedback(
                conn,
                user_row,
                feedback_type,
                title,
                content,
                contact=contact,
                scene=scene,
                extra_context=extra_context,
            )
            data = service.get_feedback_payload(
                user_key,
                profile,
                limit=limit,
                mine_only=normalized_scene == FEEDBACK_SCENE_COMMUNITY_APPLY,
                feedback_type=feedback_type,
                scene=scene,
            )
            data["created"] = serialize_feedback_row(feedback_row, viewer_user_id=user_row["id"])
            conn.commit()
        return ok_payload(data, "反馈已提交")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"提交反馈失败: {exc}"))


@app.post("/api/upload/image")
async def upload_image(request: Request):
    payload = await read_json_payload(request)
    from recharge_verify_server import save_base64_image

    image_base64 = str(payload.get("image_base64") or payload.get("imageBase64") or "").strip()
    image_name = str(payload.get("image_name") or payload.get("imageName") or "").strip()
    folder = str(payload.get("folder") or "guarantee-proof").strip().lower() or "guarantee-proof"
    try:
        relative_url = save_base64_image(image_base64, image_name=image_name, folder=folder)
        return ok_payload(
            {
                "url": build_public_file_url(request, relative_url),
                "path": relative_url,
            },
            "上传成功",
        )
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"上传图片失败: {exc}"))


@app.post("/api/recharge/create")
async def recharge_create(request: Request):
    payload = await read_json_payload(request)
    amount = to_int(payload.get("amount"), 0)
    if amount <= 0:
        return fail_payload("请输入正确的转入数量")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            check_user_active(user_row)
            live_uid, _, _, live_user_name = service.get_live_credentials(conn)
            beast_id = str(live_uid or payload.get("beast_id") or RECEIVER_BEAST_ID).strip()
            beast_nick = str(live_user_name or payload.get("beast_nick") or RECEIVER_BEAST_NICK).strip()
            create_recharge_order(conn, user_row, amount, beast_id, beast_nick)
            data = service.build_live_recharge_state(conn, user_row, wallet_row)
            conn.commit()
        return ok_payload(data, "订单已创建")
    except PermissionError as exc:
        return fail_payload(str(exc))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"创建充值订单失败: {exc}"))


@app.post("/api/recharge/cancel")
async def recharge_cancel(request: Request):
    payload = await read_json_payload(request)
    order_id = str(payload.get("order_id") or "").strip()
    if not order_id:
        return fail_payload("缺少 order_id")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            cancel_recharge_order(conn, user_row, order_id)
            data = service.build_live_recharge_state(conn, user_row, wallet_row)
            conn.commit()
        return ok_payload(data, "订单已取消")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"取消订单失败: {exc}"))


@app.post("/api/recharge/verify")
async def recharge_verify(request: Request):
    payload = await read_json_payload(request)
    order_id = str(payload.get("order_id") or "").strip()
    verify_code = str(payload.get("verify_code") or "").strip()
    expire_minutes = max(1, to_int(payload.get("expire_minutes"), DEFAULT_VERIFY_MINUTES))
    if not order_id:
        return fail_payload("缺少 order_id")
    if len(verify_code) != 4:
        return fail_payload("请输入时间后4位数字")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            order_row = find_recharge_order(conn, user_row["id"], order_id)
            if not order_row:
                return fail_payload("未找到充值订单")

            current_ms = now_ms()
            if order_row.get("status") == "pending" and current_ms > int(order_row.get("expire_at_ms") or 0):
                conn.cursor().execute(
                    "UPDATE recharge_orders SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE id=%s AND user_id=%s AND status='pending'",
                    (order_id, user_row["id"]),
                )
                data = service.build_live_recharge_state(conn, user_row, wallet_row)
                conn.commit()
                return fail_payload("订单已超时失效", data=data)

            if order_row.get("status") == "success":
                data = service.build_live_recharge_state(conn, user_row, wallet_row)
                matched = {
                    "datetime": order_row.get("matched_datetime") or "",
                    "timestamp": int(order_row.get("matched_timestamp") or 0),
                }
                conn.commit()
                return ok_payload(
                    {
                        **data,
                        "matched": matched,
                        "newBalance": serialize_wallet(wallet_row)["gemBalance"],
                    },
                    "该订单已校验成功",
                )

            live_uid, live_tk, live_tk_type, _ = service.get_live_credentials(conn)
            result = verify_recent_recharge(
                live_uid,
                live_tk,
                amount=order_row["amount"],
                verify_code=verify_code,
                created_after_ms=order_row["created_at_ms"],
                expire_minutes=expire_minutes,
                token_type=live_tk_type,
            )
            if not result.get("ok"):
                conn.commit()
                return fail_payload(result.get("message") or "未匹配到对应记录")

            matched_log = result.get("matched") or {}
            new_balance = mark_recharge_success(conn, user_row, order_row, matched_log, verify_code)
            wallet_row["gem_balance"] = new_balance
            data = service.build_live_recharge_state(conn, user_row, wallet_row)
            conn.commit()
            return ok_payload(
                {
                    **data,
                    "matched": matched_log,
                    "newBalance": new_balance,
                },
                "校验成功",
            )
    except TokenExpiredError as exc:
        return JSONResponse(status_code=401, content=fail_payload(str(exc)))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"校验失败: {exc}"))


@app.post("/api/guarantee/create")
async def guarantee_create(request: Request):
    payload = await read_json_payload(request)
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    gem_amount = to_int(payload.get("gem_amount") or payload.get("amount"), 0)
    market_price = to_int(payload.get("market_price") or payload.get("marketPrice"), 0)
    remark = str(payload.get("remark") or "").strip()
    pet_name = str(payload.get("pet_name") or payload.get("petName") or "").strip()
    trade_quantity = max(1, to_int(payload.get("trade_quantity") or payload.get("tradeQuantity"), 1))
    seller_game_id = str(payload.get("seller_game_id") or payload.get("sellerGameId") or "").strip()
    seller_game_nick = str(payload.get("seller_game_nick") or payload.get("sellerGameNick") or "").strip()
    try:
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            check_user_active(user_row)
            order_row = create_guarantee_order(
                conn,
                user_row,
                gem_amount,
                remark=remark,
                pet_name=pet_name,
                trade_quantity=trade_quantity,
                seller_game_id=seller_game_id,
                seller_game_nick=seller_game_nick,
                market_price=market_price,
            )
            wallet_row = get_or_create_user(conn, user_key, profile)[1]
            conn.commit()
        return ok_payload({"order": serialize_guarantee_row(order_row), "wallet": serialize_wallet(wallet_row)}, "担保单已创建")
    except PermissionError as exc:
        return fail_payload(str(exc))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"创建担保单失败: {exc}"))


@app.post("/api/guarantee/match")
async def guarantee_match(request: Request):
    payload = await read_json_payload(request)
    order_no = str(payload.get("order_no") or payload.get("orderId") or "").strip()
    if not order_no:
        return fail_payload("缺少担保单号")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            buyer_user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = match_guarantee_order(
                conn,
                order_no,
                buyer_user_row,
                str(payload.get("buyer_beast_id") or payload.get("buyerBeastId") or "").strip(),
                str(payload.get("buyer_beast_nick") or payload.get("buyerBeastNick") or "").strip(),
                buyer_trade_note=str(payload.get("buyer_trade_note") or payload.get("buyerTradeNote") or "").strip(),
                buyer_proof_image=str(payload.get("buyer_proof_image") or payload.get("buyerProofImage") or "").strip(),
            )
            conn.commit()
        return ok_payload({"order": serialize_guarantee_row(order_row), "viewerRole": "buyer", "canMatch": False}, "匹配成功，等待卖家确认")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"买家匹配失败: {exc}"))


@app.post("/api/transfer/create")
async def transfer_create(request: Request):
    payload = await read_json_payload(request)
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    request_amount = to_int(payload.get("amount") or payload.get("request_amount"), 0)
    user_note = str(payload.get("remark") or payload.get("user_note") or "").strip()
    try:
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            check_user_active(user_row)
            request_row = create_transfer_request(conn, user_row, request_amount, user_note=user_note)
            wallet_row = get_or_create_user(conn, user_key, profile)[1]
            data = build_transfer_state(conn, user_row, wallet_row, limit=20)
            conn.commit()
        return ok_payload({**data, "request": serialize_transfer_request(request_row)}, "转出申请已提交")
    except PermissionError as exc:
        return fail_payload(str(exc))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"提交转出申请失败: {exc}"))


@app.post("/api/guarantee/seller-confirm")
async def guarantee_seller_confirm(request: Request):
    payload = await read_json_payload(request)
    order_no = str(payload.get("order_no") or payload.get("orderId") or "").strip()
    if not order_no:
        return fail_payload("缺少担保单号")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            seller_user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = seller_confirm_guarantee_order(conn, order_no, seller_user_row)
            conn.commit()
        return ok_payload({"order": serialize_guarantee_row(order_row), "viewerRole": "seller", "canMatch": False}, "卖家已确认，系统已按双边手续费规则自动给买家结算到账")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"卖家确认失败: {exc}"))


@app.post("/api/guarantee/seller-reject")
async def guarantee_seller_reject(request: Request):
    payload = await read_json_payload(request)
    order_no = str(payload.get("order_no") or payload.get("orderId") or "").strip()
    reject_reason = str(payload.get("reason") or payload.get("reject_reason") or "").strip()
    if not order_no:
        return fail_payload("缺少担保单号")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            seller_user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = seller_reject_guarantee_order(conn, order_no, seller_user_row, reject_reason)
            conn.commit()
        return ok_payload({"order": serialize_guarantee_row(order_row), "viewerRole": "seller", "canMatch": False}, "已拒绝确认，订单已进入申诉状态，等待后台人工仲裁")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"拒绝确认失败: {exc}"))


@app.post("/api/guarantee/buyer-cancel-match")
async def guarantee_buyer_cancel_match(request: Request):
    payload = await read_json_payload(request)
    order_no = str(payload.get("order_no") or payload.get("orderId") or "").strip()
    if not order_no:
        return fail_payload("缺少担保单号")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            buyer_user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = buyer_cancel_guarantee_match(conn, order_no, buyer_user_row)
            conn.commit()
        return ok_payload({"order": serialize_guarantee_row(order_row), "viewerRole": "guest", "canMatch": True}, "已取消匹配，保单重新开放")
    except PermissionError as exc:
        return fail_payload(str(exc))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"取消匹配失败: {exc}"))


@app.post("/api/guarantee/seller-cancel-pending")
async def guarantee_seller_cancel_pending(request: Request):
    payload = await read_json_payload(request)
    order_no = str(payload.get("order_no") or payload.get("orderId") or "").strip()
    if not order_no:
        return fail_payload("缺少担保单号")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            seller_user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = seller_cancel_pending_guarantee_order(conn, order_no, seller_user_row)
            wallet_row = get_or_create_user(conn, user_key, profile)[1]
            conn.commit()
        return ok_payload({"order": serialize_guarantee_row(order_row), "wallet": serialize_wallet(wallet_row), "viewerRole": "seller", "canMatch": False}, "已取消挂单，锁定宝石已退还")
    except PermissionError as exc:
        return fail_payload(str(exc))
    except ValueError as exc:
        return fail_payload(str(exc))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"取消挂单失败: {exc}"))


@app.post("/api/guarantee/buyer-upload-proof")
async def guarantee_buyer_upload_proof(request: Request):
    payload = await read_json_payload(request)
    order_no = str(payload.get("order_no") or payload.get("orderId") or "").strip()
    buyer_proof_image = str(payload.get("buyer_proof_image") or payload.get("buyerProofImage") or "").strip()
    if not order_no:
        return fail_payload("缺少担保单号")
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        with get_connection(autocommit=False) as conn:
            buyer_user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = buyer_upload_guarantee_proof(conn, order_no, buyer_user_row, buyer_proof_image=buyer_proof_image)
            conn.commit()
        return ok_payload({"order": serialize_guarantee_row(order_row), "viewerRole": "buyer", "canMatch": False}, "交易截图已提交")
    except PermissionError as exc:
        return fail_payload(str(exc))
    except ValueError as exc:
        return fail_payload(str(exc))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"上传截图失败: {exc}"))


@app.post("/api/manage/transfer-request/complete")
async def manage_transfer_complete(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    request_id = str(payload.get("request_id") or payload.get("requestId") or "").strip()
    admin_note = str(payload.get("admin_note") or payload.get("adminNote") or "后台已完成用户转出").strip()
    if not request_id:
        return fail_payload("缺少转出申请单号")
    try:
        with get_connection(autocommit=False) as conn:
            request_row = complete_transfer_request(conn, request_id, admin_note=admin_note)
            conn.commit()
        return ok_payload({"request": serialize_transfer_request(request_row)}, "已记录用户转出完成")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"记录用户转出失败: {exc}"))


@app.post("/api/manage/transfer-request/reject")
async def manage_transfer_reject(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    request_id = str(payload.get("request_id") or payload.get("requestId") or "").strip()
    admin_note = str(payload.get("admin_note") or payload.get("adminNote") or "后台已拒绝本次转出申请").strip()
    if not request_id:
        return fail_payload("缺少转出申请单号")
    try:
        with get_connection(autocommit=False) as conn:
            request_row = reject_transfer_request(conn, request_id, admin_note=admin_note)
            conn.commit()
        return ok_payload({"request": serialize_transfer_request(request_row)}, "已拒绝用户转出申请")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"拒绝用户转出失败: {exc}"))


@app.post("/api/manage/token-config")
async def manage_token_config_save(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    has_user_id = ("userId" in payload) or ("user_id" in payload)
    has_user_name = ("userName" in payload) or ("user_name" in payload)
    has_token = "token" in payload
    has_token_type = ("tokenType" in payload) or ("token_type" in payload)
    new_user_id = str(payload.get("userId") or payload.get("user_id") or "").strip() if has_user_id else None
    new_user_name = str(payload.get("userName") or payload.get("user_name") or "").strip() if has_user_name else None
    new_token = str(payload.get("token") or "").strip() if has_token else None
    new_token_type = str(payload.get("tokenType") or payload.get("token_type") or "").strip().lower() if has_token_type else None
    if not (has_user_id or has_user_name or has_token or has_token_type):
        return fail_payload("请至少提交一个需要更新的字段")
    try:
        with get_connection(autocommit=False) as conn:
            data = patch_game_config(
                conn,
                user_id=new_user_id,
                token=new_token,
                token_type=new_token_type,
                user_name=new_user_name,
            )
            conn.commit()
        logger.info(
            f"[admin] 游戏凭证已更新 userId={data.get('userId') or '-'} "
            f"userName={data.get('userName') or '-'} tokenType={data.get('tokenType') or '-'}"
        )
        return ok_payload(data, "游戏凭证已更新（支持部分修改），立即生效无需重启")
    except ValueError as exc:
        return fail_payload(str(exc))
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"保存游戏凭证失败: {exc}"))


@app.post("/api/manage/token-config/qr-start")
async def manage_token_qr_start(_: dict[str, Any] = Depends(require_admin)):
    try:
        q_uuid = _qr_fetch_uuid()
        img_bytes = _qr_fetch_image(q_uuid)
        img_b64 = base64.b64encode(img_bytes).decode()
        session_id = __import__("secrets").token_urlsafe(16)
        expires_at = time.time() + _QR_SESSION_TTL
        with _QR_LOCK:
            now_ts = time.time()
            for sid in list(_QR_SESSIONS.keys()):
                if _QR_SESSIONS[sid].get("expires_at", 0) < now_ts:
                    _QR_SESSIONS.pop(sid, None)
            _QR_SESSIONS[session_id] = {
                "status": "waiting",
                "qrUuid": q_uuid,
                "expires_at": expires_at,
            }
        threading.Thread(target=_qr_poll_and_login, args=(session_id, q_uuid), daemon=True).start()
        return ok_payload(
            {
                "sessionId": session_id,
                "qrImage": f"data:image/jpeg;base64,{img_b64}",
                "expiresIn": _QR_SESSION_TTL,
            },
            "二维码已生成",
        )
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"生成二维码失败: {exc}"))


@app.post("/api/manage/community")
async def manage_community_create(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    try:
        with get_connection() as conn:
            row = create_community_profile(conn, payload)
            conn.commit()
        return ok_payload({"profile": row}, "名流已添加")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"添加名流失败: {exc}"))


@app.post("/api/manage/community/{profile_id}")
async def manage_community_update(profile_id: str, request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    action = payload.get("_action", "")
    try:
        with get_connection() as conn:
            if action == "delete":
                delete_community_profile(conn, profile_id)
                conn.commit()
                return ok_payload({}, "已删除")
            row = update_community_profile(conn, profile_id, payload)
            conn.commit()
            return ok_payload({"profile": row}, "已更新")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"操作名流失败: {exc}"))


@app.post("/api/manage/layout-feedback")
async def manage_layout_feedback(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()
    contact = str(payload.get("contact") or "").strip()
    page_url = str(payload.get("page_url") or payload.get("pageUrl") or "").strip()
    feedback_type = str(payload.get("type") or payload.get("feedback_type") or "网址排版").strip()[:32] or "网址排版"
    if page_url:
        content = f"页面/位置：{page_url}\n\n{content}"
    ops_user_key = "ops_layout_feedback_bot"
    profile = {"nickName": "后台排版登记", "account": "layout-ops"}
    try:
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, ops_user_key, profile)
            feedback_row = create_feedback(
                conn,
                user_row,
                feedback_type,
                title,
                content,
                contact=contact,
                scene=FEEDBACK_SCENE_ADMIN_LAYOUT,
            )
            conn.commit()
        return ok_payload({"feedback": serialize_manage_feedback_row(feedback_row)}, "已记录排版问题")
    except Exception as exc:
        return fail_payload(str(exc))


@app.post("/api/manage/promotion/settle-monthly")
async def manage_promotion_settle(_: dict[str, Any] = Depends(require_admin)):
    return fail_payload("月度结算入口已停用，当前平台仅保留永久分佣规则，奖励会在担保完成后自动到账")


@app.post("/api/manage/guarantee-transfer")
async def manage_guarantee_transfer(_: dict[str, Any] = Depends(require_admin)):
    return fail_payload("担保单已改为系统自动到账，无需后台手动转出；只有用户主动发起转出申请时才需要人工处理")


@app.post("/api/manage/feedback/update-status")
async def manage_feedback_update_status(request: Request, _: dict[str, Any] = Depends(require_admin)):
    payload = await read_json_payload(request)
    feedback_id = to_int(payload.get("feedback_id") or payload.get("feedbackId") or payload.get("id"), 0)
    status = str(payload.get("status") or "").strip()
    admin_reply = str(payload.get("admin_reply") or payload.get("adminReply") or "").strip()
    approve_to_profile = str(payload.get("approve_to_profile") or payload.get("approveToProfile") or "").strip().lower() in ("1", "true", "yes")
    if feedback_id <= 0:
        return fail_payload("缺少反馈编号")
    try:
        with get_connection(autocommit=False) as conn:
            if approve_to_profile:
                profile_payload = payload.get("profile") or {}
                approved = approve_community_feedback(conn, feedback_id, profile_payload, admin_reply=admin_reply)
                conn.commit()
                return ok_payload(
                    {
                        "feedback": serialize_manage_feedback_row(approved["feedback"]),
                        "profile": approved["profile"],
                    },
                    "认证申请已通过并加入名流列表",
                )
            feedback_row = update_feedback_status(conn, feedback_id, status, admin_reply=admin_reply)
            conn.commit()
            return ok_payload({"feedback": serialize_manage_feedback_row(feedback_row)}, "反馈状态已更新")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"更新反馈状态失败: {exc}"))


@app.get("/api/{rest_of_path:path}", include_in_schema=False)
def not_found_api(rest_of_path: str):
    return JSONResponse(status_code=404, content=fail_payload("接口不存在"))
