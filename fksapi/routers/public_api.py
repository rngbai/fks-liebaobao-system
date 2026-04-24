from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from db_mysql import (
    FEEDBACK_SCENE_COMMUNITY_APPLY,
    build_pending_summary,
    cancel_recharge_order,
    create_feedback,
    create_guarantee_order,
    create_recharge_order,
    create_transfer_request,
    find_recharge_order,
    get_connection,
    get_or_create_user,
    list_community_profiles,
    list_public_guarantee_orders,
    mark_recharge_success,
    match_guarantee_order,
    now_ms,
    serialize_feedback_row,
    serialize_guarantee_row,
    serialize_transfer_request,
    serialize_wallet,
)
from api_game import fetch_live_gem_balance, qr_fetch_image, qr_fetch_uuid, qr_poll_and_login, QR_LOCK, QR_SESSIONS, QR_SESSION_TTL
from api_runtime import (
    DEFAULT_CANCEL_LIMIT,
    RECEIVER_BEAST_ID,
    RECEIVER_BEAST_NICK,
    check_user_active,
    load_admin_asset,
    load_upload_asset,
    make_profile,
    save_base64_image,
    to_int,
)
from fastapi_shared import (
    build_public_file_url,
    fail_payload,
    get_public_orders_cache,
    get_user_key,
    json_bytes_response,
    ok_payload,
    read_json_payload,
    service,
    set_public_orders_cache,
)
from select_rockLog import DEFAULT_VERIFY_MINUTES, TokenExpiredError, fetch_recent_sell_logs, verify_recent_recharge

public_router = APIRouter()


@public_router.get("/admin", include_in_schema=False)
@public_router.get("/admin/", include_in_schema=False)
@public_router.get("/admin/{asset_path:path}", include_in_schema=False)
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


@public_router.get("/uploads/{asset_path:path}", include_in_schema=False)
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


@public_router.get("/api/recharge/health")
def recharge_health():
    return ok_payload(
        {
            "uid": RECEIVER_BEAST_ID,
            "port": 5000,
            "receiverBeastNick": RECEIVER_BEAST_NICK,
            "cancelLimit": DEFAULT_CANCEL_LIMIT,
            "adminPath": "/admin/",
        },
        "recharge verify server is running",
    )


@public_router.get("/api/recharge/recent")
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


@public_router.get("/api/recharge/state")
def recharge_state(request: Request):
    try:
        data = service.get_recharge_state_payload(get_user_key(request))
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取充值状态失败: {exc}"))


@public_router.get("/api/user/profile")
def user_profile_get(request: Request):
    try:
        data = service.get_user_profile_payload(get_user_key(request))
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取用户资料失败: {exc}"))


@public_router.get("/api/user/balance")
def user_balance(request: Request):
    try:
        data = service.get_user_profile_payload(get_user_key(request))
        return ok_payload({"gemBalance": data["wallet"]["gemBalance"]}, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取余额失败: {exc}"))


@public_router.get("/api/user/wallet-records")
def user_wallet_records(request: Request, limit: int = Query(50)):
    limit = max(1, limit)
    try:
        payload = service.get_wallet_records_payload(get_user_key(request), limit=limit)
        return ok_payload(payload, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取宝石流水失败: {exc}"))


@public_router.get("/api/transfer/state")
def transfer_state(request: Request, limit: int = Query(20)):
    limit = max(1, limit)
    try:
        data = service.get_transfer_state_payload(get_user_key(request), limit=limit)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取转出状态失败: {exc}"))


@public_router.get("/api/guarantee/list")
def guarantee_list(request: Request, limit: int = Query(20)):
    limit = max(1, limit)
    try:
        data = service.get_guarantee_list_payload(get_user_key(request), limit=limit)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保列表失败: {exc}"))


@public_router.get("/api/guarantee/detail")
def guarantee_detail(request: Request, order_no: str = Query(""), id: str = Query("")):
    target_order_no = str(order_no or id or "").strip()
    if not target_order_no:
        return fail_payload("缺少担保单号")
    try:
        data = service.get_guarantee_detail_payload(get_user_key(request), target_order_no)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取担保单失败: {exc}"))


@public_router.get("/api/feedback/list")
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


@public_router.get("/api/promotion/my")
def promotion_my(request: Request, limit: int = Query(20)):
    limit = max(1, limit)
    try:
        data = service.get_promotion_payload(get_user_key(request), limit=limit)
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取推广信息失败: {exc}"))


@public_router.get("/api/user/pending-summary")
def pending_summary(request: Request):
    try:
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, get_user_key(request))
            data = build_pending_summary(conn, user_row["id"])
            conn.commit()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取待办摘要失败: {exc}"))


@public_router.get("/api/guarantee/public")
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


@public_router.get("/api/home/content")
def home_content():
    try:
        data = service.get_home_content_payload()
        return ok_payload(data, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"读取首页内容失败: {exc}"))


@public_router.get("/api/community")
@public_router.get("/api/community/")
def public_community(category: str | None = Query(None), sub_tab: str | None = Query(None)):
    category = str(category or "").strip() or None
    sub_tab = str(sub_tab or "").strip() or None
    try:
        with get_connection() as conn:
            rows = list_community_profiles(conn, category=category, sub_tab=sub_tab, active_only=True)
        return ok_payload({"list": rows}, "查询成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"查询社区名流失败: {exc}"))


@public_router.post("/api/promotion/bind")
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


@public_router.post("/api/user/profile")
async def user_profile_post(request: Request):
    payload = await read_json_payload(request)
    user_key = get_user_key(request, payload)
    profile = make_profile(payload, request.headers)
    try:
        data = service.get_user_profile_payload(user_key, profile)
        return ok_payload(data, "保存成功")
    except Exception as exc:
        return json_bytes_response(500, fail_payload(f"保存用户资料失败: {exc}"))


@public_router.post("/api/feedback/create")
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


@public_router.post("/api/upload/image")
async def upload_image(request: Request):
    payload = await read_json_payload(request)
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


@public_router.post("/api/recharge/create")
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


@public_router.post("/api/recharge/cancel")
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


@public_router.post("/api/recharge/verify")
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


@public_router.post("/api/guarantee/create")
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


@public_router.post("/api/guarantee/match")
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


@public_router.post("/api/transfer/create")
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


@public_router.post("/api/guarantee/seller-confirm")
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


@public_router.post("/api/guarantee/seller-reject")
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


@public_router.post("/api/guarantee/buyer-cancel-match")
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


@public_router.post("/api/guarantee/seller-cancel-pending")
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


@public_router.post("/api/guarantee/buyer-upload-proof")
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
