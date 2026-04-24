from __future__ import annotations

import base64
import threading
import time

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from db_common import get_connection, get_or_create_user
from db_community import create_community_profile, delete_community_profile, list_community_profiles, update_community_profile
from db_config import build_game_config_payload, patch_game_config, save_game_config
from db_feedback import approve_community_feedback, create_feedback, serialize_manage_feedback_row, update_feedback_status
from db_manage import (
    build_manage_dashboard,
    build_manage_feedback_payload,
    build_manage_guarantee_payload,
    build_manage_recharge_payload,
    build_manage_transfer_request_payload,
    build_manage_users_payload,
    delete_user_account,
    import_manage_users,
    update_user_status,
)
from db_home import build_manage_home_content_payload, save_manage_home_content_payload
from db_promotion import build_manage_promotion_payload
from db_transfer import complete_transfer_request, reject_transfer_request, serialize_transfer_request
from db_wallet import serialize_wallet
from db_feedback import FEEDBACK_SCENE_ADMIN_LAYOUT
from db_guarantee import serialize_guarantee_row
from api_game import QR_LOCK, QR_SESSIONS, QR_SESSION_TTL, fetch_live_gem_balance, qr_fetch_image, qr_fetch_uuid, qr_poll_and_login
from api_runtime import (
    ADMIN_USERNAME,
    RECEIVER_BEAST_ID,
    RECEIVER_BEAST_NICK,
    get_cached_dashboard_payload,
    logger,
    make_profile,
    resolve_dashboard_date_range,
    set_cached_dashboard_payload,
    to_int,
    verify_admin_login,
)
from fastapi_shared import (
    create_admin_session,
    fail_payload,
    get_admin_session,
    json_bytes_response,
    ok_payload,
    read_json_payload,
    require_admin,
    revoke_admin_session,
    service,
)

manage_router = APIRouter()


@manage_router.get("/api/manage/auth-check")
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


@manage_router.get("/api/manage/home-content")
def manage_home_content(_: dict = Depends(require_admin)):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_home_content_payload(conn)
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取首页内容管理数据失败: {exc}"))


@manage_router.get("/api/manage/users")
def manage_users(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_users_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取用户管理数据失败: {exc}"))


@manage_router.get("/api/manage/promotions")
def manage_promotions(
    page: int = Query(1),
    page_size: int = Query(20),
    reward_limit: int = Query(30),
    invitee_limit: int = Query(40),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict = Depends(require_admin),
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


@manage_router.get("/api/manage/recharges")
def manage_recharges(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_recharge_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取充值记录失败: {exc}"))


@manage_router.get("/api/manage/guarantees")
def manage_guarantees(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_guarantee_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保档案失败: {exc}"))


@manage_router.get("/api/manage/feedbacks")
def manage_feedbacks(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    type: str = Query("", alias="type"),
    scene: str = Query(""),
    _: dict = Depends(require_admin),
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


@manage_router.get("/api/manage/pending-guarantees")
def manage_pending_guarantees(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_guarantee_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size), pending_only=True)
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保待确认列表失败: {exc}"))


@manage_router.get("/api/manage/transfer-requests")
def manage_transfer_requests(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    _: dict = Depends(require_admin),
):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_manage_transfer_request_payload(conn, query=query.strip(), status=status.strip(), page=max(1, page), page_size=max(1, page_size))
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取用户转出申请失败: {exc}"))


@manage_router.get("/api/manage/pending-feedbacks")
def manage_pending_feedbacks(
    page: int = Query(1),
    page_size: int = Query(20),
    query: str = Query(""),
    status: str = Query("all"),
    type: str = Query("", alias="type"),
    scene: str = Query(""),
    _: dict = Depends(require_admin),
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


@manage_router.get("/api/manage/token-config")
def manage_token_config(_: dict = Depends(require_admin)):
    try:
        with get_connection(autocommit=False) as conn:
            data = build_game_config_payload(conn, RECEIVER_BEAST_ID, __import__("config").token, env_user_name=RECEIVER_BEAST_NICK)
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取游戏凭证失败: {exc}"))


@manage_router.get("/api/manage/gem-balance")
def manage_gem_balance(_: dict = Depends(require_admin)):
    try:
        with get_connection(autocommit=False) as conn:
            uid, tk, tk_type, user_name = service.get_live_credentials(conn)
            conn.commit()
        if not uid or not tk:
            return fail_payload("游戏凭证未配置，请先在 Token 管理中设置")
        balance = fetch_live_gem_balance(uid, tk, tk_type)
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


@manage_router.get("/api/manage/token-config/qr-status")
def manage_qr_status(request: Request, session: str = Query(""), _: dict = Depends(require_admin)):
    if not session:
        return JSONResponse(status_code=400, content=fail_payload("缺少 session 参数"))
    with QR_LOCK:
        sess = QR_SESSIONS.get(session)
    if not sess:
        return JSONResponse(status_code=404, content=fail_payload("会话不存在或已过期"))
    status = sess.get("status", "waiting")
    if status == "success":
        try:
            with get_connection(autocommit=False) as conn:
                cfg = save_game_config(conn, sess["userId"], sess["token"], token_type="cw")
                conn.commit()
            with QR_LOCK:
                QR_SESSIONS.pop(session, None)
            return ok_payload({**cfg, "autoSaved": True}, "扫码登录成功，凭证已自动保存")
        except Exception as exc:
            return json_bytes_response(500, fail_payload(f"保存凭证失败: {exc}"))
    if status == "error":
        return fail_payload(sess.get("error", "登录失败"))
    if status == "timeout":
        with QR_LOCK:
            QR_SESSIONS.pop(session, None)
        return fail_payload("二维码已过期")
    return ok_payload({"status": "waiting"}, "等待扫码")


@manage_router.get("/api/manage/community")
def manage_community(
    category: str | None = Query(None),
    sub_tab: str | None = Query(None),
    active_only: int = Query(0),
    _: dict = Depends(require_admin),
):
    try:
        with get_connection() as conn:
            rows = list_community_profiles(conn, category=category, sub_tab=sub_tab, active_only=active_only == 1)
        return ok_payload({"list": rows, "total": len(rows)}, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"查询社区名流失败: {exc}"))


@manage_router.get("/api/manage/dashboard")
def manage_dashboard(request: Request, limit: int = Query(20), _: dict = Depends(require_admin)):
    limit = max(0, limit)
    try:
        params = {
            key: request.query_params.getlist(key)
            for key in request.query_params.keys()
        }
        dashboard_range = resolve_dashboard_date_range(params)
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


@manage_router.post("/api/manage/login")
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


@manage_router.post("/api/manage/logout")
async def manage_logout(request: Request):
    revoke_admin_session(str(request.headers.get("x-admin-token") or "").strip())
    return ok_payload({}, "已退出登录")


@manage_router.post("/api/manage/users/import")
async def manage_users_import(request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/users/ban")
async def manage_users_ban(request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/users/delete")
async def manage_users_delete(request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/home-content")
async def manage_home_content_save(request: Request, _: dict = Depends(require_admin)):
    payload = await read_json_payload(request)
    content_payload = payload.get("content") if isinstance(payload.get("content"), dict) else payload
    try:
        with get_connection(autocommit=False) as conn:
            data = save_manage_home_content_payload(conn, content_payload)
            conn.commit()
        return ok_payload(data, "首页内容已保存")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"保存首页内容失败: {exc}"))


@manage_router.post("/api/manage/transfer-request/complete")
async def manage_transfer_complete(request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/transfer-request/reject")
async def manage_transfer_reject(request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/token-config")
async def manage_token_config_save(request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/token-config/qr-start")
async def manage_token_qr_start(_: dict = Depends(require_admin)):
    try:
        q_uuid = qr_fetch_uuid()
        img_bytes = qr_fetch_image(q_uuid)
        img_b64 = base64.b64encode(img_bytes).decode()
        session_id = __import__("secrets").token_urlsafe(16)
        expires_at = time.time() + QR_SESSION_TTL
        with QR_LOCK:
            now_ts = time.time()
            for sid in list(QR_SESSIONS.keys()):
                if QR_SESSIONS[sid].get("expires_at", 0) < now_ts:
                    QR_SESSIONS.pop(sid, None)
            QR_SESSIONS[session_id] = {
                "status": "waiting",
                "qrUuid": q_uuid,
                "expires_at": expires_at,
            }
        threading.Thread(target=qr_poll_and_login, args=(session_id, q_uuid), daemon=True).start()
        return ok_payload(
            {
                "sessionId": session_id,
                "qrImage": f"data:image/jpeg;base64,{img_b64}",
                "expiresIn": QR_SESSION_TTL,
            },
            "二维码已生成",
        )
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"生成二维码失败: {exc}"))


@manage_router.post("/api/manage/community")
async def manage_community_create(request: Request, _: dict = Depends(require_admin)):
    payload = await read_json_payload(request)
    try:
        with get_connection() as conn:
            row = create_community_profile(conn, payload)
            conn.commit()
        return ok_payload({"profile": row}, "名流已添加")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"添加名流失败: {exc}"))


@manage_router.post("/api/manage/community/{profile_id}")
async def manage_community_update(profile_id: str, request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/layout-feedback")
async def manage_layout_feedback(request: Request, _: dict = Depends(require_admin)):
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


@manage_router.post("/api/manage/promotion/settle-monthly")
async def manage_promotion_settle(_: dict = Depends(require_admin)):
    return fail_payload("月度结算入口已停用，当前平台仅保留永久分佣规则，奖励会在担保完成后自动到账")


@manage_router.post("/api/manage/guarantee-transfer")
async def manage_guarantee_transfer(_: dict = Depends(require_admin)):
    return fail_payload("担保单已改为系统自动到账，无需后台手动转出；只有用户主动发起转出申请时才需要人工处理")


@manage_router.post("/api/manage/feedback/update-status")
async def manage_feedback_update_status(request: Request, _: dict = Depends(require_admin)):
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
