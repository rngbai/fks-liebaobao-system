from db_mysql import *  # compatibility re-export source for extracted domain functions

def generate_user_invite_code(user_id):
    user_text = str(int(user_id or 0)).zfill(6)
    return f"FKS{user_text[-10:]}"

def ensure_user_invite_code(conn, user_row):
    if not user_row:
        return ''
    current_code = str(user_row.get('invite_code') or '').strip().upper()
    if current_code:
        return current_code

    invite_code = generate_user_invite_code(user_row.get('id'))
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET invite_code=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND COALESCE(invite_code, '')=''
            """,
            (invite_code, user_row['id'])
        )
    user_row['invite_code'] = invite_code
    return invite_code

def find_user_by_invite_code(conn, invite_code):
    code = str(invite_code or '').strip().upper()
    if not code:
        return None
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE invite_code=%s LIMIT 1', (code,))
        return cursor.fetchone()

def bind_user_inviter(conn, user_row, invite_code):
    code = str(invite_code or '').strip().upper()
    if not code:
        raise ValueError('缺少推荐码')
    current_user = dict(user_row or {})
    ensure_user_invite_code(conn, current_user)
    if int(current_user.get('invited_by_user_id') or 0) > 0:
        return current_user

    inviter_row = find_user_by_invite_code(conn, code)
    if not inviter_row:
        raise ValueError('推荐码不存在，请检查后重试')
    if int(inviter_row.get('id') or 0) == int(current_user.get('id') or 0):
        raise ValueError('不能绑定自己的推荐码')

    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET invited_by_user_id=%s,
                invited_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND invited_by_user_id IS NULL
            """,
            (inviter_row['id'], current_user['id'])
        )
        cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (current_user['id'],))
        return cursor.fetchone() or current_user

def count_user_effective_invites(conn, inviter_user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            WHERE invited_by_user_id=%s AND promotion_effective_at IS NOT NULL
            """,
            (inviter_user_id,)
        )
        return int((cursor.fetchone() or {}).get('total') or 0)

def grant_promotion_reward(conn, inviter_user_id, invitee_user_id, threshold, reward_amount, remark=''):
    reward_amount = int(reward_amount or 0)
    if reward_amount <= 0:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO promotion_reward_logs (
                    user_id, invitee_user_id, reward_type, trigger_threshold, reward_amount, remark
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    inviter_user_id,
                    int(invitee_user_id or 0) or None,
                    'milestone',
                    int(threshold or 0),
                    reward_amount,
                    str(remark or '').strip()[:255],
                )
            )
    except pymysql.err.IntegrityError:
        return False

    wallet = lock_wallet(conn, inviter_user_id)
    balance_before = int(wallet.get('gem_balance') or 0)
    balance_after = balance_before + reward_amount
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s,
                total_earned=total_earned+%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (balance_after, reward_amount, inviter_user_id)
        )

    insert_wallet_transaction(
        conn,
        inviter_user_id,
        'promotion_reward',
        reward_amount,
        balance_before,
        balance_after,
        'promotion_reward',
        f'{inviter_user_id}:{threshold}',
        remark or f'推广奖励·达到 {threshold} 位有效推荐'
    )
    return True

def activate_promotion_for_user(conn, user_id):
    """标记用户为已生效推广用户（首次充值触发）。新推广机制下不再发里程碑奖励，
    里程碑奖励改为担保单完成时的 L1/L2 按单分佣。"""
    user_id = int(user_id or 0)
    if user_id <= 0:
        return None

    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE id=%s FOR UPDATE', (user_id,))
        user_row = cursor.fetchone()
    if not user_row:
        return None

    inviter_user_id = int(user_row.get('invited_by_user_id') or 0)
    if inviter_user_id <= 0 or user_row.get('promotion_effective_at'):
        return None

    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET promotion_effective_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND invited_by_user_id IS NOT NULL AND promotion_effective_at IS NULL
            """,
            (user_id,)
        )
        if cursor.rowcount <= 0:
            return None

    effective_count = count_user_effective_invites(conn, inviter_user_id)
    return {
        'inviterUserId': inviter_user_id,
        'effectiveCount': effective_count,
    }

def _flush_commission_pending(conn, user_id):
    """将 commission_pending_x10 中累积的整数宝石部分发放到 gem_balance。"""
    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT gem_balance, commission_pending_x10 FROM user_wallets WHERE user_id=%s FOR UPDATE',
            (user_id,)
        )
        row = cursor.fetchone()
    if not row:
        return 0
    pending = int(row.get('commission_pending_x10') or 0)
    flush = pending // 10
    if flush <= 0:
        return 0
    remain = pending % 10
    balance_before = int(row.get('gem_balance') or 0)
    balance_after = balance_before + flush
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s,
                commission_pending_x10=%s,
                total_earned=total_earned+%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (balance_after, remain, flush, user_id)
        )
    insert_wallet_transaction(
        conn, user_id, 'promotion_commission', flush,
        balance_before, balance_after,
        'promotion', '', f'推广佣金到账 {flush} 宝石'
    )
    return flush

def grant_order_commission(conn, order_row):
    """担保单完成后触发永久分佣：直推 0.3 宝石，间推 0.2 宝石，完成后秒到账。"""
    order_no = str(order_row.get('order_no') or '')
    seller_user_id = int(order_row.get('seller_user_id') or 0)
    if not order_no or seller_user_id <= 0:
        return

    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT id, invited_by_user_id FROM users WHERE id=%s LIMIT 1',
            (seller_user_id,)
        )
        seller = cursor.fetchone()
    if not seller:
        return

    l1_user_id = int(seller.get('invited_by_user_id') or 0)
    if l1_user_id <= 0:
        return

    with conn.cursor() as cursor:
        cursor.execute(
            'SELECT id, invited_by_user_id FROM users WHERE id=%s LIMIT 1',
            (l1_user_id,)
        )
        l1_user = cursor.fetchone()
    l2_user_id = int((l1_user or {}).get('invited_by_user_id') or 0)

    def _grant(recipient_id, invitee_id, rtype, amount_x10, remark_text):
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO promotion_commission_logs
                        (user_id, invitee_user_id, reward_type, order_no, reward_amount_x10, remark)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''',
                    (recipient_id, invitee_id, rtype, order_no, amount_x10, remark_text)
                )
        except pymysql.err.IntegrityError:
            return
        wallet = lock_wallet(conn, recipient_id)
        balance_before_x10 = get_row_amount_x10(wallet, 'gem_balance')
        total_earned_before_x10 = get_row_amount_x10(wallet, 'total_earned')
        balance_after_x10 = balance_before_x10 + amount_x10
        total_earned_after_x10 = total_earned_before_x10 + amount_x10
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE user_wallets
                SET gem_balance=%s,
                    gem_balance_x10=%s,
                    total_earned=%s,
                    total_earned_x10=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s
                ''',
                (
                    sync_legacy_int_amount(balance_after_x10),
                    balance_after_x10,
                    sync_legacy_int_amount(total_earned_after_x10),
                    total_earned_after_x10,
                    recipient_id,
                )
            )
            cursor.execute(
                'UPDATE promotion_commission_logs SET flushed_amount=%s WHERE user_id=%s AND order_no=%s AND reward_type=%s',
                (x10_to_amount(amount_x10), recipient_id, order_no, rtype)
            )
        insert_wallet_transaction(
            conn,
            recipient_id,
            'promotion_commission',
            x10_to_amount(amount_x10),
            x10_to_amount(balance_before_x10),
            x10_to_amount(balance_after_x10),
            'promotion',
            order_no,
            remark_text,
            change_amount_x10=amount_x10,
            balance_before_x10=balance_before_x10,
            balance_after_x10=balance_after_x10,
        )

    _grant(l1_user_id, seller_user_id, 'l1_commission', PROMO_COMMISSION_L1_X10,
           f'一级分佣·担保单#{order_no}')

    if l2_user_id > 0:
        _grant(l2_user_id, seller_user_id, 'l2_commission', PROMO_COMMISSION_L2_X10,
               f'二级分佣·担保单#{order_no}')

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT COUNT(*) AS cnt FROM promotion_commission_logs
            WHERE invitee_user_id=%s AND reward_type IN ('l1_commission','l2_commission')
              AND order_no != %s
            ''',
            (seller_user_id, order_no)
        )
        cnt = int((cursor.fetchone() or {}).get('cnt') or 0)

    if cnt == 0 and PROMO_FIRST_ORDER_BONUS > 0:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO promotion_commission_logs
                        (user_id, invitee_user_id, reward_type, order_no, reward_amount_x10, remark)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''',
                    (l1_user_id, seller_user_id, 'first_order_bonus', order_no,
                     PROMO_FIRST_ORDER_BONUS * 10, f'新人首单奖励·{order_no}')
                )
        except pymysql.err.IntegrityError:
            return
        wallet = lock_wallet(conn, l1_user_id)
        bal_before = int(wallet.get('gem_balance') or 0)
        bal_after = bal_before + PROMO_FIRST_ORDER_BONUS
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE user_wallets
                SET gem_balance=%s, total_earned=total_earned+%s, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s
                ''',
                (bal_after, PROMO_FIRST_ORDER_BONUS, l1_user_id)
            )
        insert_wallet_transaction(
            conn, l1_user_id, 'promotion_commission', PROMO_FIRST_ORDER_BONUS,
            bal_before, bal_after, 'promotion', order_no,
            f'新人首单奖励 {PROMO_FIRST_ORDER_BONUS} 宝石·{order_no}'
        )
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE promotion_commission_logs SET flushed_amount=%s WHERE user_id=%s AND order_no=%s AND reward_type=%s',
                (PROMO_FIRST_ORDER_BONUS, l1_user_id, order_no, 'first_order_bonus')
            )

def settle_monthly_promotion(conn, year_month_str):
    """月度结算：阶梯分红 + 全月Top5。year_month_str 格式 '2025-04'。
    应在月末由管理员手动触发一次，防止重复结算有幂等保护。"""
    import re
    if not re.match(r'^\d{4}-\d{2}$', str(year_month_str or '')):
        raise ValueError('year_month_str 格式应为 YYYY-MM，如 2025-04')

    results = []

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT user_id, COUNT(*) AS order_count
            FROM promotion_commission_logs
            WHERE reward_type='l1_commission'
              AND DATE_FORMAT(created_at,'%%Y-%%m') = %s
            GROUP BY user_id
            ORDER BY order_count DESC
            ''',
            (year_month_str,)
        )
        monthly_rows = cursor.fetchall() or []

    for row in monthly_rows:
        uid = int(row.get('user_id') or 0)
        order_count = int(row.get('order_count') or 0)

        extra_x10 = 0
        for rule in PROMO_TIER_RULES:
            if order_count >= rule['min_orders']:
                extra_x10 = rule['extra_x10']
                break

        if extra_x10 > 0:
            tier_order_no = f'TIER:{year_month_str}:{uid}'
            total_extra_x10 = extra_x10 * order_count
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        '''
                        INSERT INTO promotion_commission_logs
                            (user_id, invitee_user_id, reward_type, order_no, reward_amount_x10, remark)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ''',
                        (uid, uid, 'monthly_tier', tier_order_no, total_extra_x10,
                         f'{year_month_str} 月阶梯分红，{order_count} 单×{extra_x10/10:.1f} 宝石')
                    )
            except pymysql.err.IntegrityError:
                continue
            with conn.cursor() as cursor:
                cursor.execute(
                    'UPDATE user_wallets SET commission_pending_x10=commission_pending_x10+%s WHERE user_id=%s',
                    (total_extra_x10, uid)
                )
            flushed = _flush_commission_pending(conn, uid)
            if flushed:
                with conn.cursor() as cursor:
                    cursor.execute(
                        'UPDATE promotion_commission_logs SET flushed_amount=%s WHERE user_id=%s AND order_no=%s AND reward_type=%s',
                        (flushed, uid, tier_order_no, 'monthly_tier')
                    )
            results.append({'userId': uid, 'type': 'monthly_tier', 'orderCount': order_count, 'flushed': flushed})

    for rank, (row, reward) in enumerate(zip(monthly_rows[:5], PROMO_TOP5_REWARDS), 1):
        uid = int(row.get('user_id') or 0)
        order_count = int(row.get('order_count') or 0)
        top5_order_no = f'TOP5:{year_month_str}:{rank}'
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO promotion_commission_logs
                        (user_id, invitee_user_id, reward_type, order_no, reward_amount_x10, flushed_amount, remark)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (uid, uid, 'monthly_top5', top5_order_no, reward * 10, reward,
                     f'{year_month_str} 月Top{rank} 奖励 {reward} 宝石，共 {order_count} 单')
                )
        except pymysql.err.IntegrityError:
            continue
        wallet = lock_wallet(conn, uid)
        bal_before = int(wallet.get('gem_balance') or 0)
        bal_after = bal_before + reward
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE user_wallets SET gem_balance=%s, total_earned=total_earned+%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s',
                (bal_after, reward, uid)
            )
        insert_wallet_transaction(
            conn, uid, 'promotion_commission', reward, bal_before, bal_after,
            'promotion', top5_order_no,
            f'{year_month_str} 月 Top{rank} 奖励 {reward} 宝石'
        )
        results.append({'userId': uid, 'type': 'monthly_top5', 'rank': rank, 'reward': reward})

    return results

def serialize_manage_promotion_user_row(row):
    invited_count = int(row.get('invited_count') or 0)
    effective_invited_count = int(row.get('effective_invited_count') or 0)
    reward_amount = x10_to_amount(row.get('total_reward_amount_x10') or row.get('total_reward_amount') or 0)
    reward_count = int(row.get('reward_count') or 0)
    pending_invited_count = max(invited_count - effective_invited_count, 0)
    if reward_amount > 0:
        status_text = '已奖励'
        status_class = 'success'
    elif effective_invited_count > 0:
        status_text = '已生效'
        status_class = 'info'
    elif invited_count > 0:
        status_text = '待转化'
        status_class = 'warning'
    else:
        status_text = '未开始'
        status_class = 'neutral'
    return {
        'userId': int(row.get('id') or 0),
        'nickName': row.get('nick_name') or '方块兽玩家',
        'account': row.get('account') or '',
        'beastId': normalize_beast_id_value(row.get('beast_id')),
        'inviteCode': row.get('invite_code') or '',
        'invitedCount': invited_count,
        'effectiveInviteCount': effective_invited_count,
        'pendingInviteCount': pending_invited_count,
        'rewardCount': reward_count,
        'totalRewardAmount': reward_amount,
        'effectiveRate': round((effective_invited_count * 100 / invited_count), 1) if invited_count else 0,
        'latestInvitedTime': format_dt(row.get('latest_invited_at')),
        'latestRewardTime': format_dt(row.get('latest_reward_at')),
        'statusText': status_text,
        'statusClass': status_class,
        'createdTime': format_dt(row.get('created_at')),
    }

def serialize_manage_promotion_reward_row(row):
    reward_amount_x10 = int(
        row.get('reward_amount_x10')
        if row.get('reward_amount_x10') is not None
        else to_x10_amount(row.get('reward_amount') or 0)
    )
    return {
        'id': int(row.get('id') or 0),
        'userId': int(row.get('user_id') or 0),
        'nickName': row.get('user_nick_name') or '方块兽玩家',
        'account': row.get('user_account') or '',
        'beastId': normalize_beast_id_value(row.get('user_beast_id')),
        'inviteCode': row.get('user_invite_code') or '',
        'inviteeUserId': int(row.get('invitee_user_id') or 0),
        'inviteeNickName': row.get('invitee_nick_name') or '',
        'inviteeBeastId': normalize_beast_id_value(row.get('invitee_beast_id')),
        'rewardType': row.get('reward_type') or 'milestone',
        'triggerThreshold': int(row.get('trigger_threshold') or 0),
        'rewardAmount': x10_to_amount(reward_amount_x10),
        'rewardAmountX10': reward_amount_x10,
        'orderNo': row.get('order_no') or '',
        'flushedAmount': x10_to_amount(
            int(row.get('flushed_amount_x10') or to_x10_amount(row.get('flushed_amount') or 0))
        ),
        'remark': row.get('remark') or '',
        'createdTime': format_dt(row.get('created_at')),
    }

def serialize_manage_invitee_row(row):
    is_effective = bool(row.get('promotion_effective_at'))
    return {
        'userId': int(row.get('id') or 0),
        'nickName': row.get('nick_name') or '方块兽玩家',
        'account': row.get('account') or '',
        'beastId': normalize_beast_id_value(row.get('beast_id')),
        'invitedAt': format_dt(row.get('invited_at')),
        'promotionEffectiveAt': format_dt(row.get('promotion_effective_at')),
        'inviterUserId': int(row.get('inviter_user_id') or row.get('invited_by_user_id') or 0),
        'inviterNickName': row.get('inviter_nick_name') or '',
        'inviterInviteCode': row.get('inviter_invite_code') or '',
        'statusText': '已生效' if is_effective else '待转化',
        'statusClass': 'success' if is_effective else 'warning',
        'createdTime': format_dt(row.get('created_at')),
    }

def list_user_promotion_invitees(conn, inviter_user_id, limit=20):
    limit = max(1, min(100, int(limit or 20)))
    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT u.*
            FROM users u
            WHERE u.invited_by_user_id=%s
            ORDER BY COALESCE(u.promotion_effective_at, u.invited_at, u.created_at) DESC, u.id DESC
            LIMIT {limit}
            ''',
            (inviter_user_id,)
        )
        rows = cursor.fetchall() or []
    return [
        {
            'id': int(row.get('id') or 0),
            'nick': row.get('nick_name') or '方块兽玩家',
            'time': format_dt(row.get('invited_at')),
            'status': 1 if row.get('promotion_effective_at') else 0,
            'beastId': normalize_beast_id_value(row.get('beast_id')),
            'account': row.get('account') or '',
            'promotionEffectiveAt': format_dt(row.get('promotion_effective_at')),
        }
        for row in rows
    ]

def build_promotion_payload(conn, user_row, limit=20):
    user_id = int((user_row or {}).get('id') or 0)
    if user_id <= 0:
        raise ValueError('缺少有效用户')
    ensure_user_invite_code(conn, user_row)
    safe_limit = max(1, min(100, int(limit or 20)))
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (user_id,))
        latest_user = cursor.fetchone() or user_row
        inviter_user_id = int(latest_user.get('invited_by_user_id') or 0)
        inviter_user = None
        if inviter_user_id > 0:
            cursor.execute('SELECT id, nick_name, invite_code FROM users WHERE id=%s LIMIT 1', (inviter_user_id,))
            inviter_user = cursor.fetchone() or None
        cursor.execute(
            """
            SELECT COUNT(*) AS invited_count,
                   SUM(CASE WHEN promotion_effective_at IS NOT NULL THEN 1 ELSE 0 END) AS effective_invited_count
            FROM users
            WHERE invited_by_user_id=%s
            """,
            (user_id,)
        )
        invited_row = cursor.fetchone() or {}
        cursor.execute(
            """
            SELECT COUNT(*) AS reward_count,
                   COALESCE(SUM(reward_amount_x10), 0) AS reward_amount_x10
            FROM promotion_commission_logs
            WHERE user_id=%s
            """,
            (user_id,)
        )
        reward_row = cursor.fetchone() or {}
        cursor.execute(
            (
                "SELECT r.*, invitee.nick_name AS invitee_nick_name, invitee.beast_id AS invitee_beast_id "
                "FROM promotion_commission_logs r "
                "LEFT JOIN users invitee ON invitee.id = r.invitee_user_id "
                "WHERE r.user_id=%s "
                "ORDER BY r.created_at DESC, r.id DESC "
                f"LIMIT {safe_limit}"
            ),
            (user_id,)
        )
        reward_rows = cursor.fetchall() or []

    invited_count = int(invited_row.get('invited_count') or 0)
    effective_invited_count = int(invited_row.get('effective_invited_count') or 0)
    reward_amount = x10_to_amount(reward_row.get('reward_amount_x10') or 0)
    reward_count = int(reward_row.get('reward_count') or 0)
    rules = [
        {'label': '直推永久分佣', 'rewardDesc': '每单 +0.3 宝石，担保完成后秒到账'},
        {'label': '间推永久分佣', 'rewardDesc': '每单 +0.2 宝石，担保完成后秒到账'},
    ]
    return {
        'user': serialize_user(latest_user),
        'promotion': {
            'inviteCode': latest_user.get('invite_code') or '',
            'sharePath': f"/pages/index/index?ref={latest_user.get('invite_code') or ''}",
            'inviterUserId': inviter_user_id,
            'inviterNickName': (inviter_user or {}).get('nick_name') or '',
            'inviterInviteCode': (inviter_user or {}).get('invite_code') or '',
            'canBindInviter': inviter_user_id <= 0,
            'totalInvited': invited_count,
            'effectiveInvited': effective_invited_count,
            'pendingInvited': max(invited_count - effective_invited_count, 0),
            'totalRewardAmount': reward_amount,
            'rewardCount': reward_count,
            'rules': rules,
            'invitees': list_user_promotion_invitees(conn, user_id, limit=limit),
            'rewardLogs': [serialize_manage_promotion_reward_row(row) for row in reward_rows],
        },
    }

def build_manage_promotion_payload(conn, query='', status='all', page=1, page_size=20, reward_limit=30, invitee_limit=40):

    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    reward_limit = max(1, min(100, int(reward_limit or 30)))
    invitee_limit = max(1, min(100, int(invitee_limit or 40)))
    keyword = str(query or '').strip()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS invitee_total,
                   SUM(CASE WHEN promotion_effective_at IS NOT NULL THEN 1 ELSE 0 END) AS effective_total
            FROM users
            WHERE invited_by_user_id IS NOT NULL
            """
        )
        invitee_summary = cursor.fetchone() or {}
        cursor.execute(
            """
            SELECT COUNT(DISTINCT invited_by_user_id) AS inviter_total
            FROM users
            WHERE invited_by_user_id IS NOT NULL
            """
        )
        inviter_summary = cursor.fetchone() or {}
        cursor.execute(
            """
            SELECT COUNT(*) AS reward_count,
                   COALESCE(SUM(reward_amount), 0) AS reward_amount
            FROM promotion_reward_logs
            """
        )
        reward_summary = cursor.fetchone() or {}
        cursor.execute(
            """
            SELECT COUNT(*) AS recent_effective_count
            FROM users
            WHERE promotion_effective_at IS NOT NULL
              AND promotion_effective_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 7 DAY)
            """
        )
        recent_summary = cursor.fetchone() or {}

    conditions = ["(COALESCE(inv.invited_count, 0) > 0 OR COALESCE(reward.reward_count, 0) > 0)"]
    params = []
    if keyword:
        like_text = f"%{keyword}%"
        conditions.append(
            "(u.nick_name LIKE %s OR u.account LIKE %s OR u.beast_id LIKE %s OR u.invite_code LIKE %s)"
        )
        params.extend([like_text, like_text, like_text, like_text])
    status = str(status or 'all').strip()
    if status == 'rewarded':
        conditions.append('COALESCE(reward.reward_count, 0) > 0')
    elif status == 'effective':
        conditions.append('COALESCE(inv.effective_invited_count, 0) > 0')
    elif status == 'pending':
        conditions.append('COALESCE(inv.invited_count, 0) > COALESCE(inv.effective_invited_count, 0)')
    elif status == 'invited':
        conditions.append('COALESCE(inv.invited_count, 0) > 0')

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    count_sql = f'''
        SELECT COUNT(*) AS total
        FROM users u
        LEFT JOIN (
            SELECT invited_by_user_id AS user_id,
                   COUNT(*) AS invited_count,
                   SUM(CASE WHEN promotion_effective_at IS NOT NULL THEN 1 ELSE 0 END) AS effective_invited_count,
                   MAX(invited_at) AS latest_invited_at
            FROM users
            WHERE invited_by_user_id IS NOT NULL
            GROUP BY invited_by_user_id
        ) inv ON inv.user_id = u.id
        LEFT JOIN (
            SELECT user_id,
                   COUNT(*) AS reward_count,
                   COALESCE(SUM(reward_amount_x10), 0) AS total_reward_amount_x10,
                   MAX(created_at) AS latest_reward_at
            FROM promotion_commission_logs
            GROUP BY user_id
        ) reward ON reward.user_id = u.id
        {where_sql}
    '''
    list_sql = f'''
        SELECT u.*,
               COALESCE(inv.invited_count, 0) AS invited_count,
               COALESCE(inv.effective_invited_count, 0) AS effective_invited_count,
               inv.latest_invited_at,
               COALESCE(reward.reward_count, 0) AS reward_count,
               COALESCE(reward.total_reward_amount_x10, 0) AS total_reward_amount_x10,
               reward.latest_reward_at
        FROM users u
        LEFT JOIN (
            SELECT invited_by_user_id AS user_id,
                   COUNT(*) AS invited_count,
                   SUM(CASE WHEN promotion_effective_at IS NOT NULL THEN 1 ELSE 0 END) AS effective_invited_count,
                   MAX(invited_at) AS latest_invited_at
            FROM users
            WHERE invited_by_user_id IS NOT NULL
            GROUP BY invited_by_user_id
        ) inv ON inv.user_id = u.id
        LEFT JOIN (
            SELECT user_id,
                   COUNT(*) AS reward_count,
                   COALESCE(SUM(reward_amount_x10), 0) AS total_reward_amount_x10,
                   MAX(created_at) AS latest_reward_at
            FROM promotion_commission_logs
            GROUP BY user_id
        ) reward ON reward.user_id = u.id
        {where_sql}
        ORDER BY COALESCE(inv.effective_invited_count, 0) DESC,
                 COALESCE(reward.total_reward_amount_x10, 0) DESC,
                 COALESCE(inv.invited_count, 0) DESC,
                 u.id DESC
        LIMIT {page_size} OFFSET {offset}
    '''

    with conn.cursor() as cursor:
        cursor.execute(count_sql, tuple(params))
        total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute(list_sql, tuple(params))
        promotion_rows = cursor.fetchall() or []
        cursor.execute(
            f'''
            SELECT r.*,
                   user_u.nick_name AS user_nick_name,
                   user_u.account AS user_account,
                   user_u.beast_id AS user_beast_id,
                   user_u.invite_code AS user_invite_code,
                   invitee.nick_name AS invitee_nick_name,
                   invitee.beast_id AS invitee_beast_id
            FROM promotion_commission_logs r
            LEFT JOIN users user_u ON user_u.id = r.user_id
            LEFT JOIN users invitee ON invitee.id = r.invitee_user_id
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT {reward_limit}
            '''
        )
        reward_rows = cursor.fetchall() or []
        invitee_conditions = ['u.invited_by_user_id IS NOT NULL']
        invitee_params = []
        if keyword:
            like_text = f"%{keyword}%"
            invitee_conditions.append(
                "(u.nick_name LIKE %s OR u.account LIKE %s OR u.beast_id LIKE %s OR inviter.nick_name LIKE %s OR inviter.invite_code LIKE %s)"
            )
            invitee_params.extend([like_text, like_text, like_text, like_text, like_text])
        if status == 'effective':
            invitee_conditions.append('u.promotion_effective_at IS NOT NULL')
        elif status == 'pending':
            invitee_conditions.append('u.promotion_effective_at IS NULL')
        invitee_where_sql = f"WHERE {' AND '.join(invitee_conditions)}"
        cursor.execute(
            f'''
            SELECT u.*,
                   inviter.id AS inviter_user_id,
                   inviter.nick_name AS inviter_nick_name,
                   inviter.invite_code AS inviter_invite_code
            FROM users u
            LEFT JOIN users inviter ON inviter.id = u.invited_by_user_id
            {invitee_where_sql}
            ORDER BY COALESCE(u.promotion_effective_at, u.invited_at, u.created_at) DESC, u.id DESC
            LIMIT {invitee_limit}
            ''',
            tuple(invitee_params)
        )
        invitee_rows = cursor.fetchall() or []

    invitee_total = int(invitee_summary.get('invitee_total') or 0)
    effective_total = int(invitee_summary.get('effective_total') or 0)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        'summary': {
            'totalInviters': int(inviter_summary.get('inviter_total') or 0),
            'totalInvitees': invitee_total,
            'effectiveInvitees': effective_total,
            'pendingInvitees': max(invitee_total - effective_total, 0),
            'rewardCount': int(reward_summary.get('reward_count') or 0),
            'totalRewardAmount': x10_to_amount(reward_summary.get('reward_amount_x10') or 0),
            'recentEffectiveCount': int(recent_summary.get('recent_effective_count') or 0),
            'conversionRate': round((effective_total * 100 / invitee_total), 1) if invitee_total else 0,
        },
        'rules': [
            {'label': '直推永久分佣', 'rewardDesc': '每单 +0.3 宝石，担保完成后秒到账'},
            {'label': '间推永久分佣', 'rewardDesc': '每单 +0.2 宝石，担保完成后秒到账'},
        ],
        'pagination': {
            'page': page,
            'pageSize': page_size,
            'total': total,
            'totalPages': total_pages,
        },
        'list': [serialize_manage_promotion_user_row(row) for row in promotion_rows],
        'rewardList': [serialize_manage_promotion_reward_row(row) for row in reward_rows],
        'inviteeList': [serialize_manage_invitee_row(row) for row in invitee_rows],
    }
