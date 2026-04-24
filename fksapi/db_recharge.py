from db_mysql import *  # compatibility re-export source for extracted domain functions

def expire_pending_recharge_orders(conn, user_id, current_ms=None):
    current_ms = int(current_ms or now_ms())
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE recharge_orders
            SET status='expired', updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s AND status='pending' AND expire_at_ms < %s
            ''',
            (user_id, current_ms)
        )
        return cursor.rowcount

def get_cancel_count(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM recharge_orders WHERE user_id=%s AND status='cancelled'", (user_id,))
        row = cursor.fetchone() or {}
    return int(row.get('total') or 0)

def fetch_pending_recharge_order(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT * FROM recharge_orders
            WHERE user_id=%s AND status='pending'
            ORDER BY created_at_ms DESC
            LIMIT 1
            ''',
            (user_id,)
        )
        return cursor.fetchone()

def serialize_pending_order(order_row):
    if not order_row:
        return None
    return {
        'id': order_row['id'],
        'amount': int(order_row.get('amount') or 0),
        'beastId': order_row.get('beast_id') or '',
        'beastNick': order_row.get('beast_nick') or '',
        'status': order_row.get('status') or 'pending',
        'createdAt': int(order_row.get('created_at_ms') or 0),
        'expireAt': int(order_row.get('expire_at_ms') or 0),
        'createdTimeText': format_ms(order_row.get('created_at_ms')),
    }

def serialize_recharge_history(order_row):
    status = order_row.get('status') or 'success'
    event_ms = order_row.get('verified_at_ms') or order_row.get('cancelled_at_ms') or order_row.get('expire_at_ms') or order_row.get('created_at_ms')
    status_map = {
        'success': {
            'statusText': '已到账',
            'statusClass': 'success',
            'desc': f"匹配到账时间 {order_row.get('matched_datetime') or ''}".strip(),
            'amountPrefix': '+'
        },
        'cancelled': {
            'statusText': '已取消',
            'statusClass': 'cancelled',
            'desc': '用户主动取消订单',
            'amountPrefix': ''
        },
        'expired': {
            'statusText': '已超时',
            'statusClass': 'expired',
            'desc': '10分钟内未完成验证',
            'amountPrefix': ''
        },
        'pending': {
            'statusText': '待验证',
            'statusClass': 'pending',
            'desc': '等待用户校验',
            'amountPrefix': ''
        },
    }
    meta = status_map.get(status, status_map['success'])
    return {
        'id': order_row['id'],
        'amount': int(order_row.get('amount') or 0),
        'status': status,
        'statusText': meta['statusText'],
        'statusClass': meta['statusClass'],
        'desc': meta['desc'],
        'amountPrefix': meta['amountPrefix'],
        'time': format_ms(event_ms),
    }

def list_recharge_history(conn, user_id, limit=20):
    limit = max(1, min(100, int(limit)))
    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT * FROM recharge_orders
            WHERE user_id=%s AND status <> 'pending'
            ORDER BY GREATEST(verified_at_ms, cancelled_at_ms, expire_at_ms, created_at_ms) DESC
            LIMIT {limit}
            ''',
            (user_id,)
        )
        rows = cursor.fetchall() or []
    return [serialize_recharge_history(row) for row in rows]

def build_recharge_state(conn, user_row, wallet_row, receiver_beast_id, receiver_beast_nick):
    expire_pending_recharge_orders(conn, user_row['id'])
    pending_order = fetch_pending_recharge_order(conn, user_row['id'])
    return {
        'user': serialize_user(user_row),
        'wallet': serialize_wallet(wallet_row),
        'recharge': {
            'cancelCount': get_cancel_count(conn, user_row['id']),
            'cancelLimit': DEFAULT_CANCEL_LIMIT,
            'pendingOrder': serialize_pending_order(pending_order),
            'history': list_recharge_history(conn, user_row['id'], 20),
            'receiverBeastId': receiver_beast_id,
            'receiverBeastNick': receiver_beast_nick,
        }
    }

def create_recharge_order(conn, user_row, amount, beast_id, beast_nick):
    amount = int(amount)
    if amount <= 0:
        raise ValueError('充值数量必须大于 0')

    expire_pending_recharge_orders(conn, user_row['id'])
    cancel_count = get_cancel_count(conn, user_row['id'])
    if cancel_count >= DEFAULT_CANCEL_LIMIT:
        raise PermissionError(f'您已累计取消 {DEFAULT_CANCEL_LIMIT} 次充值订单，当前账号已达到限制，请联系管理员处理。')

    pending_order = fetch_pending_recharge_order(conn, user_row['id'])
    if pending_order:
        return pending_order

    created_at_ms = now_ms()
    expire_at_ms = created_at_ms + 10 * 60 * 1000
    order_id = f"RC{str(beast_id)[-4:]}{str(created_at_ms)[-8:]}"

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO recharge_orders (id, user_id, amount, beast_id, beast_nick, status, created_at_ms, expire_at_ms)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s)
            ''',
            (order_id, user_row['id'], amount, beast_id, beast_nick, created_at_ms, expire_at_ms)
        )
        cursor.execute('SELECT * FROM recharge_orders WHERE id=%s LIMIT 1', (order_id,))
        return cursor.fetchone()

def find_recharge_order(conn, user_id, order_id):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM recharge_orders WHERE id=%s AND user_id=%s LIMIT 1', (order_id, user_id))
        return cursor.fetchone()

def cancel_recharge_order(conn, user_row, order_id):
    expire_pending_recharge_orders(conn, user_row['id'])
    order = find_recharge_order(conn, user_row['id'], order_id)
    if not order:
        raise ValueError('未找到充值订单')
    if order.get('status') != 'pending':
        raise ValueError('当前订单状态不允许取消')

    cancelled_at_ms = now_ms()
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE recharge_orders
            SET status='cancelled', cancelled_at_ms=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND user_id=%s AND status='pending'
            ''',
            (cancelled_at_ms, order_id, user_row['id'])
        )
        if cursor.rowcount <= 0:
            raise ValueError('取消失败，请稍后重试')

def mark_recharge_success(conn, user_row, order_row, matched_log, verify_code):
    if order_row.get('status') == 'success':
        wallet = lock_wallet(conn, user_row['id'])
        return serialize_wallet(wallet)['gemBalance']

    wallet = lock_wallet(conn, user_row['id'])
    balance_before_x10 = get_row_amount_x10(wallet, 'gem_balance')
    amount = int(order_row.get('amount') or 0)
    amount_x10 = to_x10_amount(amount)
    balance_after_x10 = balance_before_x10 + amount_x10
    verified_at_ms = now_ms()
    matched_timestamp = int(matched_log.get('timestamp') or 0)
    matched_datetime = matched_log.get('datetime') or ''

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE recharge_orders
            SET status='success', verify_code=%s, matched_datetime=%s, matched_timestamp=%s, verified_at_ms=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND user_id=%s AND status='pending'
            ''',
            (verify_code, matched_datetime, matched_timestamp, verified_at_ms, order_row['id'], user_row['id'])
        )
        if cursor.rowcount <= 0:
            cursor.execute('SELECT status FROM recharge_orders WHERE id=%s AND user_id=%s LIMIT 1', (order_row['id'], user_row['id']))
            latest = cursor.fetchone() or {}
            if latest.get('status') == 'success':
                cursor.execute('SELECT gem_balance_x10, gem_balance FROM user_wallets WHERE user_id=%s LIMIT 1', (user_row['id'],))
                wallet_row = cursor.fetchone() or {}
                return x10_to_amount(get_row_amount_x10(wallet_row, 'gem_balance') or balance_after_x10)
            raise ValueError('订单状态已变化，请刷新后重试')

        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s,
                gem_balance_x10=%s,
                total_recharged=total_recharged+%s,
                total_recharged_x10=total_recharged_x10+%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (
                sync_legacy_int_amount(balance_after_x10),
                balance_after_x10,
                amount,
                amount_x10,
                user_row['id'],
            )
        )

    insert_wallet_transaction(
        conn,
        user_row['id'],
        'recharge',
        amount,
        x10_to_amount(balance_before_x10),
        x10_to_amount(balance_after_x10),
        'recharge_order',
        order_row['id'],
        f"充值到账 #{order_row['id']}",
        change_amount_x10=amount_x10,
        balance_before_x10=balance_before_x10,
        balance_after_x10=balance_after_x10,
    )
    activate_promotion_for_user(conn, user_row['id'])
    return x10_to_amount(balance_after_x10)
