from db_mysql import *  # compatibility re-export source for extracted domain functions

def get_transfer_request_meta(status):

    return TRANSFER_REQUEST_STATUS_META.get(status or TRANSFER_REQUEST_STATUS_PENDING, TRANSFER_REQUEST_STATUS_META[TRANSFER_REQUEST_STATUS_PENDING])

def calculate_transfer_out_fee(amount):
    amount = max(0, int(amount or 0))
    return max(0, amount * DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS // 10000)

def serialize_transfer_request(row):

    if not row:
        return None
    meta = get_transfer_request_meta(row.get('status'))
    request_amount_x10 = get_row_amount_x10(row, 'request_amount')
    fee_amount_x10 = get_row_amount_x10(row, 'fee_amount')
    actual_amount_x10 = get_row_amount_x10(row, 'actual_amount')
    return {
        'id': row.get('id') or '',
        'requestAmount': x10_to_amount(request_amount_x10),
        'request_amount': x10_to_amount(request_amount_x10),
        'requestAmountX10': request_amount_x10,
        'feeAmount': x10_to_amount(fee_amount_x10),
        'fee_amount': x10_to_amount(fee_amount_x10),
        'feeAmountX10': fee_amount_x10,
        'actualAmount': x10_to_amount(actual_amount_x10),
        'actual_amount': x10_to_amount(actual_amount_x10),
        'actualAmountX10': actual_amount_x10,
        'feeRateText': f"{DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS / 100:.1f}%",
        'beastId': normalize_beast_id_value(row.get('beast_id')),
        'beastNick': row.get('beast_nick') or '',
        'userNote': row.get('user_note') or '',
        'adminNote': row.get('admin_note') or '',
        'status': row.get('status') or TRANSFER_REQUEST_STATUS_PENDING,
        'statusText': meta['text'],
        'statusDesc': meta['desc'],
        'statusClass': meta['class'],
        'createTime': format_dt(row.get('created_at')),
        'processedTime': format_dt(row.get('processed_at')),
    }

def find_transfer_request(conn, request_id):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM gem_transfer_requests WHERE id=%s LIMIT 1', (request_id,))
        return cursor.fetchone()

def find_transfer_request_for_update(conn, request_id):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM gem_transfer_requests WHERE id=%s FOR UPDATE', (request_id,))
        return cursor.fetchone()

def find_pending_transfer_request(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT * FROM gem_transfer_requests
            WHERE user_id=%s AND status=%s
            ORDER BY created_at DESC
            LIMIT 1
            ''',
            (user_id, TRANSFER_REQUEST_STATUS_PENDING)
        )
        return cursor.fetchone()

def count_today_transfer_requests(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT COUNT(*) AS total
            FROM gem_transfer_requests
            WHERE user_id=%s
              AND DATE(created_at)=CURDATE()
              AND status NOT IN (%s, %s)
            ''',
            (user_id, TRANSFER_REQUEST_STATUS_CANCELLED, TRANSFER_REQUEST_STATUS_REJECTED)
        )
        row = cursor.fetchone() or {}
    return int(row.get('total') or 0)

def list_transfer_requests(conn, user_id, limit=20):
    limit = max(1, min(100, int(limit)))
    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT * FROM gem_transfer_requests
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT {limit}
            ''',
            (user_id,)
        )
        rows = cursor.fetchall() or []
    return [serialize_transfer_request(row) for row in rows]

def build_transfer_state(conn, user_row, wallet_row, limit=20):
    pending_row = find_pending_transfer_request(conn, user_row['id'])
    today_count = count_today_transfer_requests(conn, user_row['id'])
    return {
        'user': serialize_user(user_row),
        'wallet': serialize_wallet(wallet_row),
        'transfer': {
            'dailyLimit': DEFAULT_TRANSFER_OUT_DAILY_LIMIT,
            'feeBasisPoints': DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS,
            'feeRateText': f"{DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS / 100:.1f}%",
            'todayCount': today_count,
            'canCreate': bool(normalize_beast_id_value(user_row.get('beast_id'))) and not pending_row and today_count < DEFAULT_TRANSFER_OUT_DAILY_LIMIT,
            'pendingRequest': serialize_transfer_request(pending_row),
            'history': list_transfer_requests(conn, user_row['id'], limit),
        }
    }

def create_transfer_request(conn, user_row, request_amount, user_note=''):
    request_amount = int(request_amount or 0)
    if request_amount <= 0:
        raise ValueError('请输入正确的转出数量')

    beast_id = normalize_beast_id_value(user_row.get('beast_id'))
    if not beast_id:
        raise ValueError('请先绑定方块兽ID')

    pending_row = find_pending_transfer_request(conn, user_row['id'])
    if pending_row:
        raise ValueError('您已有待处理的转出申请，请等待后台完成后再发起新的申请')

    today_count = count_today_transfer_requests(conn, user_row['id'])
    if today_count >= DEFAULT_TRANSFER_OUT_DAILY_LIMIT:
        raise ValueError('每个账号每天只能申请 10 次转出')

    wallet = lock_wallet(conn, user_row['id'])
    balance_before_x10 = get_row_amount_x10(wallet, 'gem_balance')
    locked_before_x10 = get_row_amount_x10(wallet, 'locked_gems')
    request_amount_x10 = to_x10_amount(request_amount)
    if balance_before_x10 < request_amount_x10:
        raise ValueError(f'宝石余额不足，当前仅有 {x10_to_amount(balance_before_x10)} 宝石')

    fee_amount = calculate_transfer_out_fee(request_amount)
    actual_amount = max(request_amount - fee_amount, 0)
    fee_amount_x10 = to_x10_amount(fee_amount)
    actual_amount_x10 = to_x10_amount(actual_amount)
    request_id = generate_order_no('TX', user_row['id'])
    balance_after_x10 = balance_before_x10 - request_amount_x10
    locked_after_x10 = locked_before_x10 + request_amount_x10

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO gem_transfer_requests (
                id, user_id, beast_id, beast_nick, request_amount, request_amount_x10, fee_amount, fee_amount_x10, actual_amount, actual_amount_x10,
                fee_basis_points, status, user_note
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (
                request_id,
                user_row['id'],
                beast_id,
                (user_row.get('nick_name') or '方块兽玩家')[:64],
                request_amount,
                request_amount_x10,
                fee_amount,
                fee_amount_x10,
                actual_amount,
                actual_amount_x10,
                DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS,
                TRANSFER_REQUEST_STATUS_PENDING,
                str(user_note or '').strip()[:255],
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
                user_row['id'],
            )
        )

    insert_wallet_transaction(
        conn,
        user_row['id'],
        'transfer_out_lock',
        -request_amount,
        x10_to_amount(balance_before_x10),
        x10_to_amount(balance_after_x10),
        'transfer_request',
        request_id,
        f"提交转出申请 #{request_id}",
        change_amount_x10=-request_amount_x10,
        balance_before_x10=balance_before_x10,
        balance_after_x10=balance_after_x10,
    )
    return find_transfer_request(conn, request_id)

def complete_transfer_request(conn, request_id, admin_note=''):
    request_row = find_transfer_request_for_update(conn, request_id)
    if not request_row:
        raise ValueError('未找到转出申请')

    current_status = request_row.get('status') or TRANSFER_REQUEST_STATUS_PENDING
    if current_status == TRANSFER_REQUEST_STATUS_DONE:
        return find_transfer_request(conn, request_id)
    if current_status != TRANSFER_REQUEST_STATUS_PENDING:
        raise ValueError('当前转出申请不是待处理状态')

    user_id = int(request_row.get('user_id') or 0)
    request_amount = int(request_row.get('request_amount') or 0)
    request_amount_x10 = get_row_amount_x10(request_row, 'request_amount')
    wallet = lock_wallet(conn, user_id)
    locked_before_x10 = get_row_amount_x10(wallet, 'locked_gems')
    if locked_before_x10 < request_amount_x10:
        raise ValueError('锁定宝石不足，无法完成转出，请检查数据')

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE gem_transfer_requests
            SET status=%s,
                admin_note=%s,
                processed_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND status=%s
            ''',
            (
                TRANSFER_REQUEST_STATUS_DONE,
                str(admin_note or '').strip()[:255],
                request_id,
                TRANSFER_REQUEST_STATUS_PENDING,
            )
        )
        if cursor.rowcount <= 0:
            raise ValueError('记录转出完成失败，请刷新后重试')
        cursor.execute(
            '''
            UPDATE user_wallets
            SET locked_gems=%s,
                locked_gems_x10=%s,
                total_spent=total_spent+%s,
                total_spent_x10=total_spent_x10+%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (
                sync_legacy_int_amount(locked_before_x10 - request_amount_x10),
                locked_before_x10 - request_amount_x10,
                request_amount,
                request_amount_x10,
                user_id,
            )
        )
    return find_transfer_request(conn, request_id)

def reject_transfer_request(conn, request_id, admin_note=''):
    request_row = find_transfer_request_for_update(conn, request_id)
    if not request_row:
        raise ValueError('未找到转出申请')

    current_status = request_row.get('status') or TRANSFER_REQUEST_STATUS_PENDING
    if current_status == TRANSFER_REQUEST_STATUS_DONE:
        raise ValueError('该转出申请已完成，无法拒绝')
    if current_status != TRANSFER_REQUEST_STATUS_PENDING:
        return find_transfer_request(conn, request_id)

    user_id = int(request_row.get('user_id') or 0)
    request_amount = int(request_row.get('request_amount') or 0)
    request_amount_x10 = get_row_amount_x10(request_row, 'request_amount')
    wallet = lock_wallet(conn, user_id)
    balance_before_x10 = get_row_amount_x10(wallet, 'gem_balance')
    locked_before_x10 = get_row_amount_x10(wallet, 'locked_gems')
    if locked_before_x10 < request_amount_x10:
        raise ValueError('锁定宝石不足，无法拒绝转出，请检查数据')
    balance_after_x10 = balance_before_x10 + request_amount_x10

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE gem_transfer_requests
            SET status=%s,
                admin_note=%s,
                processed_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND status=%s
            ''',
            (
                TRANSFER_REQUEST_STATUS_REJECTED,
                str(admin_note or '').strip()[:255],
                request_id,
                TRANSFER_REQUEST_STATUS_PENDING,
            )
        )
        if cursor.rowcount <= 0:
            raise ValueError('拒绝转出失败，请刷新后重试')
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
                sync_legacy_int_amount(locked_before_x10 - request_amount_x10),
                locked_before_x10 - request_amount_x10,
                user_id,
            )
        )

    insert_wallet_transaction(
        conn,
        user_id,
        'transfer_out_unlock',
        request_amount,
        x10_to_amount(balance_before_x10),
        x10_to_amount(balance_after_x10),
        'transfer_request',
        request_id,
        f"后台已拒绝转出申请 #{request_id}，解锁 {request_amount} 宝石",
        change_amount_x10=request_amount_x10,
        balance_before_x10=balance_before_x10,
        balance_after_x10=balance_after_x10,
    )
    return find_transfer_request(conn, request_id)
