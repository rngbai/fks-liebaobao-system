from db_mysql import *  # compatibility re-export source for extracted domain functions

def calculate_guarantee_seller_total_cost_x10(gem_amount, fee_amount_x10=DEFAULT_GUARANTEE_FEE_X10):
    gem_amount_x10 = to_x10_amount(max(0, int(gem_amount or 0)))
    fee_amount_x10 = max(0, int(fee_amount_x10 or 0))
    return gem_amount_x10 + fee_amount_x10

def calculate_guarantee_seller_total_cost(gem_amount, fee_amount=DEFAULT_GUARANTEE_FEE):
    gem_amount = max(0, int(gem_amount or 0))
    fee_amount = max(0, int(fee_amount or 0))
    return gem_amount + fee_amount

def calculate_guarantee_actual_receive_x10(gem_amount, fee_amount_x10=DEFAULT_GUARANTEE_FEE_X10):
    gem_amount_x10 = to_x10_amount(max(0, int(gem_amount or 0)))
    fee_amount_x10 = max(0, int(fee_amount_x10 or 0))
    return max(gem_amount_x10 - fee_amount_x10, 0)

def calculate_guarantee_actual_receive(gem_amount, fee_amount=DEFAULT_GUARANTEE_FEE):
    gem_amount = max(0, int(gem_amount or 0))
    fee_amount = max(0, int(fee_amount or 0))
    return max(gem_amount - fee_amount, 0)

def calculate_guarantee_total_fee_x10(fee_amount_x10=DEFAULT_GUARANTEE_FEE_X10):
    fee_amount_x10 = max(0, int(fee_amount_x10 or 0))
    return fee_amount_x10 * 2

def calculate_guarantee_total_fee(fee_amount=DEFAULT_GUARANTEE_FEE):
    fee_amount = max(0, int(fee_amount or 0))
    return fee_amount * 2

def get_guarantee_meta(status):

    return GUARANTEE_STATUS_META.get(status or GUARANTEE_STATUS_PENDING, GUARANTEE_STATUS_META[GUARANTEE_STATUS_PENDING])

def serialize_guarantee_row(row):
    if not row:
        return None
    raw_status = row.get('status') or GUARANTEE_STATUS_PENDING
    meta = get_guarantee_meta(raw_status)
    gem_amount = int(row.get('gem_amount') or 0)
    market_price = int(row.get('market_price') or 0)
    fee_amount_x10 = get_row_amount_x10(row, 'fee_amount')
    fee_amount = x10_to_amount(fee_amount_x10)
    seller_total_cost_x10 = calculate_guarantee_seller_total_cost_x10(gem_amount, fee_amount_x10)
    actual_receive_x10 = calculate_guarantee_actual_receive_x10(gem_amount, fee_amount_x10)
    total_fee_amount_x10 = calculate_guarantee_total_fee_x10(fee_amount_x10)
    seller_total_cost = x10_to_amount(seller_total_cost_x10)
    actual_receive = x10_to_amount(actual_receive_x10)
    total_fee_amount = x10_to_amount(total_fee_amount_x10)
    seller_confirmed = bool(row.get('seller_confirmed_at'))

    # 计算待匹配保单的过期时间戳（30分钟），用于前端显示倒计时
    created_at = row.get('created_at')
    expire_at_ms = 0
    if raw_status == GUARANTEE_STATUS_PENDING and created_at:
        try:
            created_ts = created_at.timestamp() if hasattr(created_at, 'timestamp') else float(created_at)
            expire_at_ms = int((created_ts + GUARANTEE_AUTO_CLOSE_MINUTES * 60) * 1000)
        except Exception:
            expire_at_ms = 0

    matched_at = row.get('matched_at')
    has_buyer_proof = bool(str(row.get('buyer_proof_image') or '').strip())
    abandon_proof_expire_at_ms = 0
    computed_auto_confirm_dt = None
    if raw_status == GUARANTEE_STATUS_MATCHED and isinstance(matched_at, datetime) and not seller_confirmed:
        if not has_buyer_proof:
            try:
                abandon_proof_expire_at_ms = int(matched_at.timestamp() * 1000) + GUARANTEE_MATCH_ABANDON_MINUTES * 60 * 1000
            except Exception:
                abandon_proof_expire_at_ms = 0
        else:
            computed_auto_confirm_dt = matched_at + timedelta(hours=GUARANTEE_AUTO_CONFIRM_HOURS)
    auto_confirm_src = row.get('auto_confirm_at') or computed_auto_confirm_dt
    auto_confirm_time_str = format_dt(auto_confirm_src) if auto_confirm_src else ''

    status_text = meta['text']
    status_short_text = meta['short_text']
    status_desc = meta['desc']
    if raw_status == GUARANTEE_STATUS_MATCHED and seller_confirmed:
        status_text = '自动到账中'
        status_short_text = '到账中'
        status_desc = f'卖家已确认交易完成，系统正在给买家发放宝石（到账后实收 {actual_receive}）'
    elif raw_status == GUARANTEE_STATUS_DONE:
        status_desc = f'交易已完成，买家最终实收 {actual_receive} 宝石'


    return {
        'id': row.get('order_no') or '',
        'orderNo': row.get('order_no') or '',
        'petName': row.get('pet_name') or '',
        'pet_name': row.get('pet_name') or '',
        'tradeQuantity': int(row.get('trade_quantity') or 0),
        'trade_quantity': int(row.get('trade_quantity') or 0),
        'sellerGameId': row.get('seller_game_id') or '',
        'seller_game_id': row.get('seller_game_id') or '',
        'sellerGameNick': row.get('seller_game_nick') or '',
        'seller_game_nick': row.get('seller_game_nick') or '',
        'gemAmount': gem_amount,
        'gem_amount': gem_amount,
        'marketPrice': market_price,
        'market_price': market_price,
        'expireAtMs': expire_at_ms,
        'expire_at_ms': expire_at_ms,
        'abandonProofExpireAtMs': abandon_proof_expire_at_ms,
        'abandon_proof_expire_at_ms': abandon_proof_expire_at_ms,
        'feeAmount': fee_amount,
        'fee_amount': fee_amount,
        'feeAmountX10': fee_amount_x10,
        'sellerFeeAmount': fee_amount,
        'seller_fee_amount': fee_amount,
        'sellerFeeAmountX10': fee_amount_x10,
        'buyerFeeAmount': fee_amount,
        'buyer_fee_amount': fee_amount,
        'buyerFeeAmountX10': fee_amount_x10,
        'totalFeeAmount': total_fee_amount,
        'total_fee_amount': total_fee_amount,
        'totalFeeAmountX10': total_fee_amount_x10,
        'sellerTotalCost': seller_total_cost,
        'seller_total_cost': seller_total_cost,
        'sellerTotalCostX10': seller_total_cost_x10,
        'actualReceive': actual_receive,
        'actual_receive': actual_receive,
        'actualReceiveX10': actual_receive_x10,

        'remark': row.get('remark') or '',
        'buyerTradeNote': row.get('buyer_trade_note') or '',
        'buyer_trade_note': row.get('buyer_trade_note') or '',
        'adminNote': row.get('admin_note') or '',
        'admin_note': row.get('admin_note') or '',
        'statusRaw': raw_status,
        'statusIndex': meta['index'],
        'status': meta['index'],
        'statusText': status_text,
        'statusShortText': status_short_text,
        'statusDesc': status_desc,
        'statusClass': meta['class'],
        'sellerUserId': int(row.get('seller_user_id') or 0),
        'buyerUserId': int(row.get('buyer_user_id') or 0),
        'sellerBeastId': row.get('seller_beast_id') or row.get('seller_user_beast_id') or '',
        'seller_beast_id': row.get('seller_beast_id') or row.get('seller_user_beast_id') or '',
        'sellerNickName': row.get('seller_nick_name') or '',
        'buyerBeastId': row.get('buyer_beast_id') or '',
        'buyer_beast_id': row.get('buyer_beast_id') or '',
        'buyerBeastNick': row.get('buyer_beast_nick') or row.get('buyer_user_nick_name') or '',
        'buyer_beast_nick': row.get('buyer_beast_nick') or row.get('buyer_user_nick_name') or '',
        'buyerProofImage': row.get('buyer_proof_image') or '',
        'buyer_proof_image': row.get('buyer_proof_image') or '',
        'buyerProofUploadedAt': format_dt(row.get('buyer_proof_uploaded_at')),
        'buyer_proof_uploaded_at': format_dt(row.get('buyer_proof_uploaded_at')),
        'buyerProofUploadedTime': format_dt(row.get('buyer_proof_uploaded_at')),
        'buyer_proof_uploaded_time': format_dt(row.get('buyer_proof_uploaded_at')),
        'autoConfirmTime': auto_confirm_time_str,

        'auto_confirm_time': auto_confirm_time_str,
        'sellerConfirmed': seller_confirmed,
        'seller_confirmed': seller_confirmed,
        'sellerConfirmedTime': format_dt(row.get('seller_confirmed_at')),
        'seller_confirmed_time': format_dt(row.get('seller_confirmed_at')),
        'createTime': format_dt(row.get('created_at')),
        'create_time': format_dt(row.get('created_at')),
        'matchedTime': format_dt(row.get('matched_at')),
        'matched_time': format_dt(row.get('matched_at')),
        'finishedTime': format_dt(row.get('finished_at')),
        'finished_time': format_dt(row.get('finished_at')),
    }

def apply_guarantee_auto_close(conn, order_no=None):
    """自动关闭：pending 状态超过 30 分钟未匹配的保单，宝石原路退还卖家。"""
    conditions = [
        'status=%s',
        'buyer_user_id IS NULL',
        f'created_at <= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {GUARANTEE_AUTO_CLOSE_MINUTES} MINUTE)',
    ]
    params = [GUARANTEE_STATUS_PENDING]
    if order_no:
        conditions.append('order_no=%s')
        params.append(str(order_no).strip())

    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT order_no FROM guarantee_orders WHERE {' AND '.join(conditions)}",
            tuple(params)
        )
        rows = cursor.fetchall() or []

    for row in rows:
        target_no = str((row or {}).get('order_no') or '').strip()
        if not target_no:
            continue
        try:
            _close_pending_guarantee_refund(conn, target_no)
        except Exception:
            pass

def _guarantee_refund_seller_unlock_wallet(conn, order_row, order_no, refund_remark):
    """订单已置为 closed 后，将卖家锁定宝石退回可用余额并记账。"""
    seller_user_id = int(order_row.get('seller_user_id') or 0)
    gem_amount = int(order_row.get('gem_amount') or 0)
    fee_amount_x10 = get_row_amount_x10(order_row, 'fee_amount')
    total_cost_x10 = calculate_guarantee_seller_total_cost_x10(gem_amount, fee_amount_x10)

    seller_wallet = lock_wallet(conn, seller_user_id)
    balance_before_x10 = get_row_amount_x10(seller_wallet, 'gem_balance')
    locked_before_x10 = get_row_amount_x10(seller_wallet, 'locked_gems')
    balance_after_x10 = balance_before_x10 + total_cost_x10
    locked_after_x10 = max(0, locked_before_x10 - total_cost_x10)

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s,
                gem_balance_x10=%s,
                locked_gems=%s,
                locked_gems_x10=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (
                sync_legacy_int_amount(balance_after_x10),
                balance_after_x10,
                sync_legacy_int_amount(locked_after_x10),
                locked_after_x10,
                seller_user_id,
            )
        )

    remark = str(refund_remark or f'保单 {order_no} 关闭，宝石已退还')[:255]
    insert_wallet_transaction(
        conn,
        seller_user_id,
        'guarantee_refund',
        x10_to_amount(total_cost_x10),
        x10_to_amount(balance_before_x10),
        x10_to_amount(balance_after_x10),
        'guarantee_order',
        order_no,
        remark,
        change_amount_x10=total_cost_x10,
        balance_before_x10=balance_before_x10,
        balance_after_x10=balance_after_x10,
    )

def _close_pending_guarantee_refund(conn, order_no, refund_remark=None):
    """将一笔 pending 且无买家的保单关闭并退款给卖家。"""
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM guarantee_orders WHERE order_no=%s FOR UPDATE', (order_no,))
        order_row = cursor.fetchone()

    if not order_row or order_row.get('status') != GUARANTEE_STATUS_PENDING:
        return
    if int(order_row.get('buyer_user_id') or 0):
        return

    with conn.cursor() as cursor:
        cursor.execute(
            'UPDATE guarantee_orders SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE order_no=%s AND status=%s',
            (GUARANTEE_STATUS_CLOSED, order_no, GUARANTEE_STATUS_PENDING)
        )
        if cursor.rowcount <= 0:
            return

    note = refund_remark or f'保单 {order_no} 超时未匹配，宝石已退还'
    _guarantee_refund_seller_unlock_wallet(conn, order_row, order_no, note)

def apply_guarantee_matched_abandon_no_proof(conn, order_no=None):
    """已匹配、卖家未确认、且一直无交易截图超过 GUARANTEE_MATCH_ABANDON_MINUTES 分钟 → 关单退还卖家。"""
    conditions = [
        'status=%s',
        'seller_confirmed_at IS NULL',
        "(buyer_proof_image IS NULL OR TRIM(buyer_proof_image)='')",
        f'matched_at <= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {GUARANTEE_MATCH_ABANDON_MINUTES} MINUTE)',
    ]
    params = [GUARANTEE_STATUS_MATCHED]
    if order_no:
        conditions.append('order_no=%s')
        params.append(str(order_no).strip())

    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT order_no FROM guarantee_orders WHERE {' AND '.join(conditions)}",
            tuple(params)
        )
        rows = cursor.fetchall() or []

    for row in rows:
        target_no = str((row or {}).get('order_no') or '').strip()
        if not target_no:
            continue
        try:
            _close_matched_no_proof_refund(conn, target_no)
        except Exception:
            pass

def _close_matched_no_proof_refund(conn, order_no):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM guarantee_orders WHERE order_no=%s FOR UPDATE', (order_no,))
        order_row = cursor.fetchone()

    if not order_row or order_row.get('status') != GUARANTEE_STATUS_MATCHED:
        return
    if order_row.get('seller_confirmed_at'):
        return
    if str(order_row.get('buyer_proof_image') or '').strip():
        return

    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            UPDATE guarantee_orders
            SET status=%s, updated_at=CURRENT_TIMESTAMP
            WHERE order_no=%s AND status=%s
              AND seller_confirmed_at IS NULL
              AND (buyer_proof_image IS NULL OR TRIM(buyer_proof_image)='')
              AND matched_at <= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {GUARANTEE_MATCH_ABANDON_MINUTES} MINUTE)
            ''',
            (GUARANTEE_STATUS_CLOSED, order_no, GUARANTEE_STATUS_MATCHED)
        )
        if cursor.rowcount <= 0:
            return

    note = f'保单 {order_no} 匹配后{GUARANTEE_MATCH_ABANDON_MINUTES}分钟内未上传交易截图，视为放弃，宝石已退还卖家'
    _guarantee_refund_seller_unlock_wallet(conn, order_row, order_no, note)

def seller_cancel_pending_guarantee_order(conn, order_no, seller_user_row):
    """卖家取消「待匹配、尚无买家」的保单，锁定宝石立即退还。"""
    apply_guarantee_matched_abandon_no_proof(conn, order_no=order_no)
    apply_guarantee_auto_close(conn, order_no=order_no)
    order_row = find_guarantee_order_for_update(conn, order_no)
    if not order_row:
        raise ValueError('未找到担保单')
    if int(order_row.get('seller_user_id') or 0) != int(seller_user_row.get('id') or 0):
        raise PermissionError('只有卖家本人才能取消保单')
    if (order_row.get('status') or GUARANTEE_STATUS_PENDING) != GUARANTEE_STATUS_PENDING:
        raise ValueError('仅「等待买家匹配」状态的保单可取消')
    if int(order_row.get('buyer_user_id') or 0):
        raise ValueError('已有买家匹配，无法取消，请使用平台流程或联系客服')

    with conn.cursor() as cursor:
        cursor.execute(
            'UPDATE guarantee_orders SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE order_no=%s AND status=%s',
            (GUARANTEE_STATUS_CLOSED, order_no, GUARANTEE_STATUS_PENDING)
        )
        if cursor.rowcount <= 0:
            raise ValueError('取消失败，请刷新后重试')

    note = f'保单 {order_no} 卖家主动取消挂单，宝石已退还'
    _guarantee_refund_seller_unlock_wallet(conn, order_row, order_no, note)
    return find_guarantee_order(conn, order_no)

def buyer_cancel_guarantee_match(conn, order_no, buyer_user_row):
    """买家在卖家未确认前取消匹配，保单回到 pending 状态，等待新买家。"""
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM guarantee_orders WHERE order_no=%s FOR UPDATE', (order_no,))
        order_row = cursor.fetchone()

    if not order_row:
        raise ValueError('未找到担保单')

    if int(order_row.get('buyer_user_id') or 0) != int(buyer_user_row.get('id') or 0):
        raise PermissionError('只有买家本人才能取消匹配')

    current_status = order_row.get('status') or GUARANTEE_STATUS_PENDING
    if current_status != GUARANTEE_STATUS_MATCHED:
        raise ValueError('当前保单不在待确认状态，无法取消匹配')
    if order_row.get('seller_confirmed_at'):
        raise ValueError('卖家已确认交易完成，无法取消匹配')

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE guarantee_orders
            SET buyer_user_id=NULL, buyer_beast_id='', buyer_beast_nick='',
                buyer_trade_note='', buyer_proof_image='', buyer_proof_uploaded_at=NULL,
                status=%s, matched_at=NULL, seller_confirmed_at=NULL, updated_at=CURRENT_TIMESTAMP
            WHERE order_no=%s AND status=%s
            ''',
            (GUARANTEE_STATUS_PENDING, order_no, GUARANTEE_STATUS_MATCHED)
        )
        if cursor.rowcount <= 0:
            raise ValueError('取消匹配失败，请刷新后重试')

    return find_guarantee_order(conn, order_no)

def buyer_upload_guarantee_proof(conn, order_no, buyer_user_row, buyer_proof_image=''):
    """已匹配买家补传交易截图（匹配时可不传，须在超时前补传）。"""
    apply_guarantee_matched_abandon_no_proof(conn, order_no=order_no)
    buyer_proof_image = str(buyer_proof_image or '').strip()[:255]
    if not buyer_proof_image:
        raise ValueError('请上传交易截图')
    order_row = find_guarantee_order_for_update(conn, order_no)
    if not order_row:
        raise ValueError('未找到担保单')
    if int(order_row.get('buyer_user_id') or 0) != int(buyer_user_row.get('id') or 0):
        raise PermissionError('只有匹配买家本人可上传截图')
    if (order_row.get('status') or GUARANTEE_STATUS_PENDING) != GUARANTEE_STATUS_MATCHED:
        raise ValueError('当前状态不可上传截图')
    if order_row.get('seller_confirmed_at'):
        raise ValueError('卖家已确认，无法再修改截图')

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE guarantee_orders
            SET buyer_proof_image=%s,
                buyer_proof_uploaded_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE order_no=%s AND status=%s AND buyer_user_id=%s AND seller_confirmed_at IS NULL
            ''',
            (buyer_proof_image, order_no, GUARANTEE_STATUS_MATCHED, buyer_user_row['id'])
        )
        if cursor.rowcount <= 0:
            raise ValueError('上传失败，请刷新后重试')
    return find_guarantee_order(conn, order_no)

def apply_guarantee_auto_confirm(conn, order_no=None):
    conditions = [
        'status=%s',
        'seller_confirmed_at IS NULL',
        'matched_at IS NOT NULL',
        # 无截图的单走「放弃交易」关单逻辑，不得自动确认给买家
        "(buyer_proof_image IS NOT NULL AND TRIM(buyer_proof_image)<>'')",
        f'matched_at <= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {GUARANTEE_AUTO_CONFIRM_HOURS} HOUR)',
    ]
    params = [GUARANTEE_STATUS_MATCHED]
    if order_no:
        conditions.append('order_no=%s')
        params.append(str(order_no).strip())

    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            UPDATE guarantee_orders
            SET seller_confirmed_at=DATE_ADD(matched_at, INTERVAL {GUARANTEE_AUTO_CONFIRM_HOURS} HOUR),
                updated_at=CURRENT_TIMESTAMP
            WHERE {' AND '.join(conditions)}
            ''',
            tuple(params)
        )
        return cursor.rowcount

def settle_confirmed_guarantee_orders(conn, order_no=None):
    conditions = [
        'status=%s',
        'seller_confirmed_at IS NOT NULL',
    ]
    params = [GUARANTEE_STATUS_MATCHED]
    if order_no:
        conditions.append('order_no=%s')
        params.append(str(order_no).strip())

    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT order_no
            FROM guarantee_orders
            WHERE {' AND '.join(conditions)}
            ORDER BY seller_confirmed_at ASC, matched_at ASC, created_at ASC
            ''' ,
            tuple(params)
        )
        rows = cursor.fetchall() or []

    settled_count = 0
    for row in rows:
        target_order_no = str((row or {}).get('order_no') or '').strip()
        if not target_order_no:
            continue
        try:
            with get_connection(autocommit=False) as tx_conn:
                complete_guarantee_transfer(tx_conn, target_order_no)
                tx_conn.commit()
            settled_count += 1
        except Exception:
            pass
    return settled_count

def find_guarantee_order(conn, order_no):
    apply_guarantee_matched_abandon_no_proof(conn, order_no=order_no)
    apply_guarantee_auto_close(conn, order_no=order_no)
    apply_guarantee_auto_confirm(conn, order_no=order_no)
    settle_confirmed_guarantee_orders(conn, order_no=order_no)
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT g.*,
                   seller.nick_name AS seller_nick_name,
                   seller.account AS seller_account,
                   seller.beast_id AS seller_user_beast_id,
                   buyer.nick_name AS buyer_user_nick_name,
                   buyer.account AS buyer_account
            FROM guarantee_orders g
            LEFT JOIN users seller ON seller.id = g.seller_user_id
            LEFT JOIN users buyer ON buyer.id = g.buyer_user_id
            WHERE g.order_no=%s
            LIMIT 1
            ''',
            (order_no,)
        )
        return cursor.fetchone()

def find_guarantee_order_for_update(conn, order_no):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM guarantee_orders WHERE order_no=%s FOR UPDATE', (order_no,))
        return cursor.fetchone()

def list_guarantee_orders(conn, user_id=None, role='seller', limit=20, status=None):
    apply_guarantee_matched_abandon_no_proof(conn)
    apply_guarantee_auto_close(conn)
    apply_guarantee_auto_confirm(conn)
    settle_confirmed_guarantee_orders(conn)
    limit = max(1, min(200, int(limit)))

    conditions = []
    params = []
    if user_id:
        if role == 'buyer':
            conditions.append('g.buyer_user_id=%s')
        else:
            conditions.append('g.seller_user_id=%s')
        params.append(user_id)
    if status:
        conditions.append('g.status=%s')
        params.append(status)
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''

    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT g.*,
                   seller.nick_name AS seller_nick_name,
                   seller.account AS seller_account,
                   seller.beast_id AS seller_user_beast_id,
                   buyer.nick_name AS buyer_user_nick_name,
                   buyer.account AS buyer_account
            FROM guarantee_orders g
            LEFT JOIN users seller ON seller.id = g.seller_user_id
            LEFT JOIN users buyer ON buyer.id = g.buyer_user_id
            {where_sql}
            ORDER BY g.created_at DESC
            LIMIT {limit}
            ''',
            tuple(params)
        )
        rows = cursor.fetchall() or []
    return [serialize_guarantee_row(row) for row in rows]

def create_guarantee_order(
    conn,
    user_row,
    gem_amount,
    remark='',
    fee_amount=DEFAULT_GUARANTEE_FEE,
    pet_name='',
    trade_quantity=1,
    seller_game_id='',
    seller_game_nick='',
    market_price=0,
):
    gem_amount = int(gem_amount or 0)
    market_price = max(0, int(market_price or 0))
    fee_amount_x10 = int(fee_amount or DEFAULT_GUARANTEE_FEE_X10)
    trade_quantity = max(1, int(trade_quantity or 1))
    pet_name = str(pet_name or '').strip()[:64]
    seller_game_id = str(seller_game_id or '').strip()[:32]
    seller_game_nick = str(seller_game_nick or '').strip()[:64]
    remark = str(remark or '').strip()[:255]

    if not pet_name:
        raise ValueError('请选择兽王类型')
    if gem_amount <= 0:
        raise ValueError('请输入正确的担保宝石数量')
    if fee_amount_x10 < 0:
        raise ValueError('手续费不能小于 0')
    if not seller_game_id:
        raise ValueError('请填写地球猎人ID号')
    if not seller_game_nick:
        raise ValueError('请填写地球猎人昵称')

    wallet = lock_wallet(conn, user_row['id'])
    balance_before_x10 = get_row_amount_x10(wallet, 'gem_balance')
    locked_before_x10 = get_row_amount_x10(wallet, 'locked_gems')
    total_cost_x10 = calculate_guarantee_seller_total_cost_x10(gem_amount, fee_amount_x10)
    if balance_before_x10 < total_cost_x10:
        raise ValueError(f'余额不足，当前仅有 {x10_to_amount(balance_before_x10)} 宝石，需要至少 {x10_to_amount(total_cost_x10)} 宝石')


    order_no = generate_order_no('GUA', user_row['id'])
    balance_after_x10 = balance_before_x10 - total_cost_x10
    locked_after_x10 = locked_before_x10 + total_cost_x10
    seller_beast_id = normalize_beast_id_value(user_row.get('beast_id'))

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO guarantee_orders (
                order_no, seller_user_id, seller_beast_id, pet_name, trade_quantity,
                seller_game_id, seller_game_nick, gem_amount, market_price, fee_amount, fee_amount_x10, remark, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (
                order_no,
                user_row['id'],
                seller_beast_id,
                pet_name,
                trade_quantity,
                seller_game_id,
                seller_game_nick,
                gem_amount,
                market_price,
                sync_legacy_int_amount(fee_amount_x10),
                fee_amount_x10,
                remark,
                GUARANTEE_STATUS_PENDING,
            )
        )
        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s,
                gem_balance_x10=%s,
                locked_gems=%s,
                locked_gems_x10=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (
                sync_legacy_int_amount(balance_after_x10),
                balance_after_x10,
                sync_legacy_int_amount(locked_after_x10),
                locked_after_x10,
                user_row['id']
            )
        )

    insert_wallet_transaction(
        conn,
        user_row['id'],
        'guarantee_lock',
        -x10_to_amount(total_cost_x10),
        x10_to_amount(balance_before_x10),
        x10_to_amount(balance_after_x10),
        'guarantee_order',
        order_no,
        f"担保锁定 #{order_no}（卖家实扣 {x10_to_amount(total_cost_x10)}，含手续费 {x10_to_amount(fee_amount_x10)}）",
        change_amount_x10=-total_cost_x10,
        balance_before_x10=balance_before_x10,
        balance_after_x10=balance_after_x10,
    )

    return find_guarantee_order(conn, order_no)

def match_guarantee_order(conn, order_no, buyer_user_row, buyer_beast_id, buyer_beast_nick, buyer_trade_note='', buyer_proof_image=''):

    apply_guarantee_matched_abandon_no_proof(conn, order_no=order_no)
    apply_guarantee_auto_close(conn, order_no=order_no)
    apply_guarantee_auto_confirm(conn, order_no=order_no)
    order_row = find_guarantee_order_for_update(conn, order_no)
    if not order_row:
        raise ValueError('未找到担保单')

    if int(order_row.get('seller_user_id') or 0) == int(buyer_user_row.get('id') or 0):
        raise ValueError('卖家本人不能作为买家匹配')

    current_status = order_row.get('status') or GUARANTEE_STATUS_PENDING
    if current_status == GUARANTEE_STATUS_DONE:
        raise ValueError('该担保单已完成，不能重复匹配')
    if current_status == GUARANTEE_STATUS_APPEAL:
        raise ValueError('该担保单正在申诉中，暂时不能匹配')
    if current_status == GUARANTEE_STATUS_CLOSED:
        raise ValueError('该保单已关闭（超时未匹配或已取消），无法再匹配，请联系卖家重新挂单')

    if current_status == GUARANTEE_STATUS_MATCHED:
        existing_buyer_id = int(order_row.get('buyer_user_id') or 0)
        if existing_buyer_id and existing_buyer_id != int(buyer_user_row.get('id') or 0):
            raise ValueError('该担保单已被其他买家匹配')
        if existing_buyer_id == int(buyer_user_row.get('id') or 0) and not order_row.get('seller_confirmed_at'):
            ubid = str(buyer_beast_id or buyer_user_row.get('beast_id') or '').strip()[:32]
            ubnick = str(buyer_beast_nick or buyer_user_row.get('nick_name') or '').strip()[:64]
            unote = str(buyer_trade_note or '').strip()[:255]
            uproof = str(buyer_proof_image or '').strip()[:255]
            if ubid and ubnick:
                with conn.cursor() as cursor:
                    cursor.execute(
                        '''
                        UPDATE guarantee_orders
                        SET buyer_beast_id=%s,
                            buyer_beast_nick=%s,
                            buyer_trade_note=%s,
                            buyer_proof_image=IF(TRIM(%s)='', buyer_proof_image, %s),
                            buyer_proof_uploaded_at=IF(TRIM(%s)='', buyer_proof_uploaded_at, CURRENT_TIMESTAMP),
                            updated_at=CURRENT_TIMESTAMP
                        WHERE order_no=%s AND status=%s AND buyer_user_id=%s AND seller_confirmed_at IS NULL
                        ''',
                        (ubid, ubnick, unote, uproof, uproof, uproof, order_no, GUARANTEE_STATUS_MATCHED, buyer_user_row['id'])
                    )
        return find_guarantee_order(conn, order_no)

    buyer_beast_id = str(buyer_beast_id or buyer_user_row.get('beast_id') or '').strip()[:32]
    buyer_beast_nick = str(buyer_beast_nick or buyer_user_row.get('nick_name') or '').strip()[:64]
    buyer_trade_note = str(buyer_trade_note or '').strip()[:255]
    buyer_proof_image = str(buyer_proof_image or '').strip()[:255]
    # 匹配时不再强制要求买家填写方块兽ID/昵称，买家确认卖家信息后直接匹配即可，截图须在匹配后时限内补传

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE guarantee_orders
            SET buyer_user_id=%s,
                buyer_beast_id=%s,
                buyer_beast_nick=%s,
                buyer_trade_note=%s,
                buyer_proof_image=%s,
                buyer_proof_uploaded_at=IF(TRIM(%s)='', NULL, CURRENT_TIMESTAMP),
                status=%s,
                matched_at=CURRENT_TIMESTAMP,
                seller_confirmed_at=NULL,
                updated_at=CURRENT_TIMESTAMP
            WHERE order_no=%s AND status=%s
            ''',
            (
                buyer_user_row['id'],
                buyer_beast_id,
                buyer_beast_nick,
                buyer_trade_note,
                buyer_proof_image,
                buyer_proof_image,
                GUARANTEE_STATUS_MATCHED,
                order_no,
                GUARANTEE_STATUS_PENDING,
            )
        )

        if cursor.rowcount <= 0:
            raise ValueError('匹配失败，请刷新后重试')
    return find_guarantee_order(conn, order_no)

def seller_confirm_guarantee_order(conn, order_no, seller_user_row):
    apply_guarantee_auto_confirm(conn, order_no=order_no)
    order_row = find_guarantee_order_for_update(conn, order_no)
    if not order_row:
        raise ValueError('未找到担保单')

    if int(order_row.get('seller_user_id') or 0) != int(seller_user_row.get('id') or 0):
        raise PermissionError('只有卖家本人才能确认交易完成')

    current_status = order_row.get('status') or GUARANTEE_STATUS_PENDING
    if current_status == GUARANTEE_STATUS_DONE:
        return find_guarantee_order(conn, order_no)
    if current_status != GUARANTEE_STATUS_MATCHED:
        raise ValueError('当前保单还未进入待卖家确认状态')
    if not int(order_row.get('buyer_user_id') or 0):
        raise ValueError('当前保单还没有买家匹配')
    if order_row.get('seller_confirmed_at'):
        return find_guarantee_order(conn, order_no)
    if not str(order_row.get('buyer_proof_image') or '').strip():
        raise ValueError('买家尚未上传交易截图，请待买家上传后再确认')

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE guarantee_orders
            SET seller_confirmed_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE order_no=%s AND status=%s AND seller_confirmed_at IS NULL
            ''',
            (order_no, GUARANTEE_STATUS_MATCHED)
        )
        if cursor.rowcount <= 0:
            raise ValueError('确认失败，请刷新后重试')
    return complete_guarantee_transfer(conn, order_no)

def seller_reject_guarantee_order(conn, order_no, seller_user_row, reject_reason=''):
    apply_guarantee_auto_confirm(conn, order_no=order_no)
    order_row = find_guarantee_order_for_update(conn, order_no)
    if not order_row:
        raise ValueError('未找到担保单')

    if int(order_row.get('seller_user_id') or 0) != int(seller_user_row.get('id') or 0):
        raise PermissionError('只有卖家本人才能拒绝确认')

    current_status = order_row.get('status') or GUARANTEE_STATUS_PENDING
    if current_status == GUARANTEE_STATUS_DONE:
        raise ValueError('担保单已完成，无法拒绝')
    if current_status == GUARANTEE_STATUS_APPEAL:
        raise ValueError('担保单已在申诉中')
    if current_status != GUARANTEE_STATUS_MATCHED:
        raise ValueError('当前保单还未进入待卖家确认状态')

    reason = str(reject_reason or '卖家拒绝确认，申请人工仲裁').strip()[:255]
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE guarantee_orders
            SET status=%s,
                appeal_reason=%s,
                admin_note=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE order_no=%s AND status=%s
            ''',
            (
                GUARANTEE_STATUS_APPEAL,
                reason,
                f'卖家拒绝确认: {reason}',
                order_no,
                GUARANTEE_STATUS_MATCHED,
            )
        )
        if cursor.rowcount <= 0:
            raise ValueError('拒绝失败，请刷新后重试')
    return find_guarantee_order(conn, order_no)

def list_public_guarantee_orders(conn, limit=20, pet_name=None):
    apply_guarantee_matched_abandon_no_proof(conn)
    apply_guarantee_auto_close(conn)
    apply_guarantee_auto_confirm(conn)
    settle_confirmed_guarantee_orders(conn)
    limit = max(1, min(100, int(limit)))

    conditions = ['g.status=%s']
    params = [GUARANTEE_STATUS_PENDING]
    if pet_name:
        conditions.append('g.pet_name=%s')
        params.append(pet_name)
    where_sql = f"WHERE {' AND '.join(conditions)}"

    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT g.*,
                   seller.nick_name AS seller_nick_name,
                   seller.account AS seller_account,
                   seller.beast_id AS seller_user_beast_id,
                   buyer.nick_name AS buyer_user_nick_name,
                   buyer.account AS buyer_account
            FROM guarantee_orders g
            LEFT JOIN users seller ON seller.id = g.seller_user_id
            LEFT JOIN users buyer ON buyer.id = g.buyer_user_id
            {where_sql}
            ORDER BY g.created_at DESC
            LIMIT {limit}
            ''',
            tuple(params)
        )
        rows = cursor.fetchall() or []
    return [serialize_guarantee_row(row) for row in rows]

def build_pending_summary(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS c FROM guarantee_orders WHERE seller_user_id=%s AND status=%s",
            (user_id, GUARANTEE_STATUS_MATCHED)
        )
        pending_confirm = int((cursor.fetchone() or {}).get('c') or 0)

        cursor.execute(
            "SELECT COUNT(*) AS c FROM guarantee_orders WHERE seller_user_id=%s AND status=%s AND buyer_user_id IS NULL",
            (user_id, GUARANTEE_STATUS_PENDING)
        )
        pending_match = int((cursor.fetchone() or {}).get('c') or 0)

        cursor.execute(
            "SELECT COUNT(*) AS c FROM guarantee_orders WHERE buyer_user_id=%s AND status=%s",
            (user_id, GUARANTEE_STATUS_MATCHED)
        )
        waiting_seller = int((cursor.fetchone() or {}).get('c') or 0)

        cursor.execute(
            "SELECT COUNT(*) AS c FROM gem_transfer_requests WHERE user_id=%s AND status='pending'",
            (user_id,)
        )
        pending_transfer = int((cursor.fetchone() or {}).get('c') or 0)

        cursor.execute(
            "SELECT COUNT(*) AS c FROM user_messages WHERE user_id=%s AND is_read=0",
            (user_id,)
        )
        unread_messages = int((cursor.fetchone() or {}).get('c') or 0)

    total = pending_confirm + pending_match + waiting_seller + pending_transfer
    return {
        'total': total,
        'pendingConfirm': pending_confirm,
        'pendingMatch': pending_match,
        'waitingSeller': waiting_seller,
        'pendingTransfer': pending_transfer,
        'unreadMessages': unread_messages,
    }

def complete_guarantee_transfer(conn, order_no, admin_note=''):
    order_row = find_guarantee_order_for_update(conn, order_no)
    if not order_row:
        raise ValueError('担保单不存在')

    current_status = order_row.get('status') or GUARANTEE_STATUS_PENDING
    if current_status == GUARANTEE_STATUS_DONE:
        return find_guarantee_order(conn, order_no)
    if current_status != GUARANTEE_STATUS_MATCHED:
        raise ValueError('当前担保单状态不支持完成结算')
    if not order_row.get('seller_confirmed_at'):
        raise ValueError('卖家尚未确认交易完成')

    seller_user_id = int(order_row.get('seller_user_id') or 0)
    buyer_user_id = int(order_row.get('buyer_user_id') or 0)
    if buyer_user_id <= 0:
        raise ValueError('当前担保单尚未匹配买家')

    gem_amount = int(order_row.get('gem_amount') or 0)
    fee_amount_x10 = get_row_amount_x10(order_row, 'fee_amount')
    total_cost_x10 = calculate_guarantee_seller_total_cost_x10(gem_amount, fee_amount_x10)
    actual_receive_x10 = calculate_guarantee_actual_receive_x10(gem_amount, fee_amount_x10)
    total_cost = x10_to_amount(total_cost_x10)
    actual_receive = x10_to_amount(actual_receive_x10)

    wallet_ids = [seller_user_id] if seller_user_id == buyer_user_id else sorted({seller_user_id, buyer_user_id})
    wallet_map = {uid: lock_wallet(conn, uid) for uid in wallet_ids}

    seller_wallet = wallet_map[seller_user_id]
    buyer_wallet = wallet_map[buyer_user_id]
    locked_before_x10 = get_row_amount_x10(seller_wallet, 'locked_gems')
    if locked_before_x10 < total_cost_x10:
        raise ValueError('卖家锁定宝石不足，无法完成结算')

    seller_balance_before_x10 = get_row_amount_x10(seller_wallet, 'gem_balance')
    buyer_balance_before_x10 = get_row_amount_x10(buyer_wallet, 'gem_balance')
    buyer_balance_after_x10 = buyer_balance_before_x10 + actual_receive_x10
    buyer_fee_amount = x10_to_amount(int(order_row.get('buyer_fee_amount_x10') or fee_amount_x10 or 0))
    seller_fee_amount = x10_to_amount(int(order_row.get('seller_fee_amount_x10') or fee_amount_x10 or 0))
    final_admin_note = str(
        admin_note or f'系统已按规则给买家到账 {actual_receive} 宝石，买卖双方各扣 {x10_to_amount(fee_amount_x10)} 宝石手续费'
    ).strip()[:255]

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE guarantee_orders
            SET status=%s,
                admin_note=%s,
                finished_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE order_no=%s AND status=%s AND seller_confirmed_at IS NOT NULL
            ''',
            (
                GUARANTEE_STATUS_DONE,
                final_admin_note,
                order_no,
                GUARANTEE_STATUS_MATCHED,
            )
        )
        if cursor.rowcount <= 0:
            raise ValueError('担保单状态已变化，请刷新后重试')
        cursor.execute(
            '''
            UPDATE user_wallets
            SET locked_gems=%s,
                locked_gems_x10=%s,
                total_spent=%s,
                total_spent_x10=total_spent_x10+%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (
                sync_legacy_int_amount(locked_before_x10 - total_cost_x10),
                locked_before_x10 - total_cost_x10,
                sync_legacy_int_amount(total_cost_x10),
                total_cost_x10,
                seller_user_id,
            )
        )
        if actual_receive_x10 > 0:
            cursor.execute(
                '''
                UPDATE user_wallets
                SET gem_balance=%s,
                    gem_balance_x10=%s,
                    total_earned=%s,
                    total_earned_x10=total_earned_x10+%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s
                ''',
                (
                    sync_legacy_int_amount(buyer_balance_after_x10),
                    buyer_balance_after_x10,
                    sync_legacy_int_amount(actual_receive_x10),
                    actual_receive_x10,
                    buyer_user_id,
                )
            )

    insert_wallet_transaction(
        conn,
        seller_user_id,
        'guarantee_complete',
        0,
        x10_to_amount(seller_balance_before_x10),
        x10_to_amount(seller_balance_before_x10),
        'guarantee_order',
        order_no,
        f'担保完成 #{order_no}，买家实收 {actual_receive} 宝石，平台总手续费 {seller_fee_amount + buyer_fee_amount} 宝石',
        change_amount_x10=0,
        balance_before_x10=seller_balance_before_x10,
        balance_after_x10=seller_balance_before_x10,
    )

    if actual_receive_x10 > 0:
        insert_wallet_transaction(
            conn,
            buyer_user_id,
            'guarantee_receive',
            actual_receive,
            x10_to_amount(buyer_balance_before_x10),
            x10_to_amount(buyer_balance_after_x10),
            'guarantee_order',
            order_no,
            f'担保到账 #{order_no}，实收 {actual_receive} 宝石（已扣买家手续费 {buyer_fee_amount} 宝石）',
            change_amount_x10=actual_receive_x10,
            balance_before_x10=buyer_balance_before_x10,
            balance_after_x10=buyer_balance_after_x10,
        )

    try:
        grant_order_commission(conn, order_row)
    except Exception:
        pass

    return find_guarantee_order(conn, order_no)
