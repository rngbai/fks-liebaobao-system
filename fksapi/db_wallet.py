from db_mysql import *  # compatibility re-export source for extracted domain functions

def build_liebaobao_id(user_row):
    user_row = user_row or {}
    user_id = int(user_row.get('id') or 0)
    if user_id > 0:
        return f"LBB{user_id:06d}"
    user_key = str(user_row.get('user_key') or '').strip()
    if user_key:
        return f"LBB-{user_key[-8:].upper()}"
    return ''

def serialize_user(user_row):
    return {
        'id': int(user_row['id']),
        'nickName': user_row.get('nick_name') or '方块兽玩家',
        'avatarUrl': user_row.get('avatar_url') or '',
        'account': user_row.get('account') or '',
        'beastId': normalize_beast_id_value(user_row.get('beast_id')),
        'phone': user_row.get('phone') or '',
        'liebaobaoId': build_liebaobao_id(user_row),
        'email': user_row.get('email') or '',
        'inviteCode': user_row.get('invite_code') or '',
        'invitedByUserId': int(user_row.get('invited_by_user_id') or 0),
        'invitedAt': format_dt(user_row.get('invited_at')),
        'promotionEffectiveAt': format_dt(user_row.get('promotion_effective_at')),
    }

def serialize_wallet(wallet_row):
    gem_balance_x10 = get_row_amount_x10(wallet_row, 'gem_balance')
    locked_gems_x10 = get_row_amount_x10(wallet_row, 'locked_gems')
    total_recharged_x10 = get_row_amount_x10(wallet_row, 'total_recharged')
    total_spent_x10 = get_row_amount_x10(wallet_row, 'total_spent')
    total_earned_x10 = get_row_amount_x10(wallet_row, 'total_earned')
    return {
        'gemBalance': x10_to_amount(gem_balance_x10),
        'gemBalanceX10': gem_balance_x10,
        'lockedGems': x10_to_amount(locked_gems_x10),
        'lockedGemsX10': locked_gems_x10,
        'totalRecharged': x10_to_amount(total_recharged_x10),
        'totalSpent': x10_to_amount(total_spent_x10),
        'totalEarned': x10_to_amount(total_earned_x10),
    }

def insert_wallet_transaction(
    conn,
    user_id,
    biz_type,
    change_amount,
    balance_before,
    balance_after,
    ref_type='',
    ref_id='',
    remark='',
    change_amount_x10=None,
    balance_before_x10=None,
    balance_after_x10=None,
):
    change_amount_x10 = int(change_amount_x10 if change_amount_x10 is not None else to_x10_amount(change_amount))
    balance_before_x10 = int(balance_before_x10 if balance_before_x10 is not None else to_x10_amount(balance_before))
    balance_after_x10 = int(balance_after_x10 if balance_after_x10 is not None else to_x10_amount(balance_after))
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO wallet_transactions (
                user_id, biz_type, change_amount, change_amount_x10,
                balance_before, balance_before_x10,
                balance_after, balance_after_x10,
                ref_type, ref_id, remark
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (
                user_id,
                biz_type,
                sync_legacy_int_amount(change_amount_x10),
                change_amount_x10,
                sync_legacy_int_amount(balance_before_x10),
                balance_before_x10,
                sync_legacy_int_amount(balance_after_x10),
                balance_after_x10,
                ref_type,
                ref_id,
                remark[:255],
            )
        )
        return int(cursor.lastrowid)

def lock_wallet(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM user_wallets WHERE user_id=%s FOR UPDATE', (user_id,))
        wallet = cursor.fetchone()
        if not wallet:
            cursor.execute('INSERT INTO user_wallets (user_id) VALUES (%s)', (user_id,))
            cursor.execute('SELECT * FROM user_wallets WHERE user_id=%s FOR UPDATE', (user_id,))
            wallet = cursor.fetchone()
        return wallet

def list_wallet_records(conn, user_id, limit=50):
    limit = max(1, min(200, int(limit)))
    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT * FROM wallet_transactions
            WHERE user_id=%s
            ORDER BY id DESC
            LIMIT {limit}
            ''',
            (user_id,)
        )
        rows = cursor.fetchall() or []

    result = []
    for row in rows:
        amount = int(row.get('change_amount') or 0)
        result.append({
            'id': int(row['id']),
            'bizType': row.get('biz_type') or '',
            'desc': row.get('remark') or row.get('biz_type') or '',
            'time': format_dt(row.get('created_at')),
            'amount': amount,
        })
    return result

def build_user_stats(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) AS total FROM guarantee_orders WHERE seller_user_id=%s', (user_id,))
        guarantee_total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute("SELECT COUNT(*) AS total FROM guarantee_orders WHERE seller_user_id=%s AND status=%s", (user_id, GUARANTEE_STATUS_DONE))
        guarantee_done = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute(
            "SELECT COALESCE(SUM(change_amount_x10), 0) AS total_x10 FROM wallet_transactions WHERE user_id=%s AND change_amount_x10 > 0 AND biz_type <> 'recharge'",
            (user_id,)
        )
        earned_gem = x10_to_amount((cursor.fetchone() or {}).get('total_x10') or 0)
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            WHERE invited_by_user_id=%s AND promotion_effective_at IS NOT NULL
            """,
            (user_id,)
        )
        recommend_count = int((cursor.fetchone() or {}).get('total') or 0)
    return {
        'guaranteeTotal': guarantee_total,
        'guaranteeDone': guarantee_done,
        'recommendCount': recommend_count,
        'earnedGem': earned_gem,
    }
