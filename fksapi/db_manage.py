from db_mysql import *  # compatibility re-export source for extracted domain functions

def serialize_manage_recharge_row(row):
    status = row.get('status') or 'pending'
    meta = RECHARGE_STATUS_META.get(status, RECHARGE_STATUS_META['pending'])
    event_time = row.get('created_at')
    if status == 'success' and row.get('verified_at_ms'):
        event_time = datetime.fromtimestamp(int(row.get('verified_at_ms') or 0) / 1000)
    return {
        'id': row.get('id') or '',
        'userNickName': row.get('user_nick_name') or '方块兽玩家',
        'account': row.get('user_account') or '',
        'beastId': normalize_beast_id_value(row.get('user_beast_id')),
        'amount': int(row.get('amount') or 0),
        'status': status,
        'statusText': meta['text'],
        'statusClass': meta['class'],
        'verifyCode': row.get('verify_code') or '',
        'matchedTime': row.get('matched_datetime') or '',
        'time': format_dt(event_time),
    }

def serialize_manage_transfer_request_row(row):
    payload = serialize_transfer_request(row) or {}
    payload.update({
        'userNickName': row.get('user_nick_name') or '方块兽玩家',
        'account': row.get('user_account') or '',
        'beastId': normalize_beast_id_value(row.get('beast_id') or row.get('user_beast_id')),
    })
    return payload

def parse_manage_user_status(value, default=1):
    text = str(value or '').strip()
    if not text:
        return int(default or 1)
    if text in ('0', 'false', 'False', '禁用', '停用', '冻结'):
        return 0
    if text in ('1', 'true', 'True', '正常', '启用', '有效'):
        return 1
    try:
        return 1 if int(text) > 0 else 0
    except (TypeError, ValueError):
        return int(default or 1)

def get_manage_user_status_meta(status_value):
    return {
        'value': 1 if int(status_value or 0) > 0 else 0,
        'text': '正常' if int(status_value or 0) > 0 else '停用',
        'class': 'success' if int(status_value or 0) > 0 else 'danger',
    }

def get_user_source_text(user_row):
    user_key = str((user_row or {}).get('user_key') or '').strip()
    return '后台导入' if user_key.startswith('import_') else '小程序'

def serialize_manage_user_row(row):
    status_meta = get_manage_user_status_meta(row.get('status'))
    invited_count = int(row.get('invited_count') or 0)
    effective_invited_count = int(row.get('effective_invited_count') or 0)
    reward_count = int(row.get('reward_count') or 0)
    reward_amount = int(row.get('reward_amount') or 0)
    return {
        'id': int(row.get('id') or 0),
        'userKey': row.get('user_key') or '',
        'sourceText': get_user_source_text(row),
        'nickName': row.get('nick_name') or '方块兽玩家',
        'avatarUrl': row.get('avatar_url') or '',
        'account': row.get('account') or '',
        'beastId': normalize_beast_id_value(row.get('beast_id')),
        'phone': row.get('phone') or '',
        'email': row.get('email') or '',
        'status': status_meta['value'],
        'statusText': status_meta['text'],
        'statusClass': status_meta['class'],
        'inviteCode': row.get('invite_code') or '',
        'invitedByUserId': int(row.get('invited_by_user_id') or 0),
        'invitedByNickName': row.get('inviter_nick_name') or '',
        'invitedByInviteCode': row.get('inviter_invite_code') or '',
        'invitedAt': format_dt(row.get('invited_at')),
        'promotionEffectiveAt': format_dt(row.get('promotion_effective_at')),
        'wallet': {
            'gemBalance': int(row.get('gem_balance') or 0),
            'lockedGems': int(row.get('locked_gems') or 0),
            'totalRecharged': int(row.get('total_recharged') or 0),
            'totalSpent': int(row.get('total_spent') or 0),
            'totalEarned': int(row.get('total_earned') or 0),
        },
        'stats': {
            'guaranteeTotal': int(row.get('guarantee_total') or 0),
            'guaranteeDone': int(row.get('guarantee_done') or 0),
            'invitedCount': invited_count,
            'effectiveInvitedCount': effective_invited_count,
            'rewardCount': reward_count,
            'rewardAmount': reward_amount,
        },
        'createdTime': format_dt(row.get('created_at')),
        'updatedTime': format_dt(row.get('updated_at')),
    }

def build_manage_user_summary(conn):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS total_users,
                   SUM(CASE WHEN status > 0 THEN 1 ELSE 0 END) AS active_users,
                   SUM(CASE WHEN COALESCE(beast_id, '') <> '' AND beast_id NOT LIKE 'BEAST_%' THEN 1 ELSE 0 END) AS bound_beast_users,
                   SUM(CASE WHEN created_at >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 7 DAY) THEN 1 ELSE 0 END) AS recent_new_users
            FROM users
            """
        )
        user_row = cursor.fetchone() or {}
        cursor.execute(
            """
            SELECT COALESCE(SUM(gem_balance), 0) AS total_balance,
                   COALESCE(SUM(locked_gems), 0) AS total_locked,
                   COALESCE(SUM(total_recharged), 0) AS total_recharged,
                   COALESCE(SUM(total_spent), 0) AS total_spent,
                   COALESCE(SUM(total_earned), 0) AS total_earned
            FROM user_wallets
            """
        )
        wallet_row = cursor.fetchone() or {}
    return {
        'totalUsers': int(user_row.get('total_users') or 0),
        'activeUsers': int(user_row.get('active_users') or 0),
        'boundBeastUsers': int(user_row.get('bound_beast_users') or 0),
        'recentNewUsers': int(user_row.get('recent_new_users') or 0),
        'totalBalance': int(wallet_row.get('total_balance') or 0),
        'totalLockedGems': int(wallet_row.get('total_locked') or 0),
        'totalRecharged': int(wallet_row.get('total_recharged') or 0),
        'totalSpent': int(wallet_row.get('total_spent') or 0),
        'totalEarned': int(wallet_row.get('total_earned') or 0),
    }

def build_manage_users_payload(conn, query='', status=None, page=1, page_size=20):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    keyword = str(query or '').strip()

    conditions = []
    params = []
    if keyword:
        like_text = f"%{keyword}%"
        conditions.append(
            "(u.nick_name LIKE %s OR u.account LIKE %s OR u.beast_id LIKE %s OR u.phone LIKE %s OR u.email LIKE %s OR u.invite_code LIKE %s OR u.user_key LIKE %s)"
        )
        params.extend([like_text, like_text, like_text, like_text, like_text, like_text, like_text])
    if status not in (None, '', 'all'):
        conditions.append('u.status=%s')
        params.append(parse_manage_user_status(status))

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    count_sql = f"SELECT COUNT(*) AS total FROM users u {where_sql}"
    list_sql = f'''
        SELECT u.*,
               inviter.nick_name AS inviter_nick_name,
               inviter.invite_code AS inviter_invite_code,
               COALESCE(w.gem_balance, 0) AS gem_balance,
               COALESCE(w.locked_gems, 0) AS locked_gems,
               COALESCE(w.total_recharged, 0) AS total_recharged,
               COALESCE(w.total_spent, 0) AS total_spent,
               COALESCE(w.total_earned, 0) AS total_earned,
               COALESCE(g.guarantee_total, 0) AS guarantee_total,
               COALESCE(g.guarantee_done, 0) AS guarantee_done,
               COALESCE(inv.invited_count, 0) AS invited_count,
               COALESCE(inv.effective_invited_count, 0) AS effective_invited_count,
               COALESCE(reward.reward_count, 0) AS reward_count,
               COALESCE(reward.reward_amount, 0) AS reward_amount
        FROM users u
        LEFT JOIN users inviter ON inviter.id = u.invited_by_user_id
        LEFT JOIN user_wallets w ON w.user_id = u.id
        LEFT JOIN (
            SELECT seller_user_id AS user_id,
                   COUNT(*) AS guarantee_total,
                   SUM(CASE WHEN status=%s THEN 1 ELSE 0 END) AS guarantee_done
            FROM guarantee_orders
            GROUP BY seller_user_id
        ) g ON g.user_id = u.id
        LEFT JOIN (
            SELECT invited_by_user_id AS user_id,
                   COUNT(*) AS invited_count,
                   SUM(CASE WHEN promotion_effective_at IS NOT NULL THEN 1 ELSE 0 END) AS effective_invited_count
            FROM users
            WHERE invited_by_user_id IS NOT NULL
            GROUP BY invited_by_user_id
        ) inv ON inv.user_id = u.id
        LEFT JOIN (
            SELECT user_id,
                   COUNT(*) AS reward_count,
                   COALESCE(SUM(reward_amount), 0) AS reward_amount
            FROM promotion_reward_logs
            GROUP BY user_id
        ) reward ON reward.user_id = u.id
        {where_sql}
        ORDER BY u.created_at DESC, u.id DESC
        LIMIT {page_size} OFFSET {offset}
    '''

    with conn.cursor() as cursor:
        cursor.execute(count_sql, tuple(params))
        total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute(list_sql, (GUARANTEE_STATUS_DONE, *params))
        rows = cursor.fetchall() or []

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        'summary': build_manage_user_summary(conn),
        'pagination': {
            'page': page,
            'pageSize': page_size,
            'total': total,
            'totalPages': total_pages,
        },
        'list': [serialize_manage_user_row(row) for row in rows],
    }

def split_manage_import_columns(line):
    normalized = str(line or '').replace('\t', ',').replace('，', ',').replace('|', ',').replace(';', ',')
    return [item.strip() for item in normalized.split(',')]

def find_manage_user_for_import(conn, account='', beast_id='', phone='', email=''):
    with conn.cursor() as cursor:
        if account:
            cursor.execute('SELECT * FROM users WHERE account=%s LIMIT 1', (account,))
            row = cursor.fetchone()
            if row:
                return row
        if beast_id:
            cursor.execute('SELECT * FROM users WHERE beast_id=%s LIMIT 1', (beast_id,))
            row = cursor.fetchone()
            if row:
                return row
        if phone:
            cursor.execute('SELECT * FROM users WHERE phone=%s LIMIT 1', (phone,))
            row = cursor.fetchone()
            if row:
                return row
        if email:
            cursor.execute('SELECT * FROM users WHERE email=%s LIMIT 1', (email,))
            row = cursor.fetchone()
            if row:
                return row
    return None

def update_user_status(conn, user_id, status, admin_note=''):
    """设置用户状态：1=正常, 0=拉黑(停用)"""
    user_id = int(user_id or 0)
    if user_id <= 0:
        raise ValueError('缺少有效的用户编号')
    new_status = 1 if int(status or 0) > 0 else 0
    with conn.cursor() as cursor:
        cursor.execute('SELECT id, nick_name, status FROM users WHERE id=%s', (user_id,))
        user = cursor.fetchone()
        if not user:
            raise ValueError('未找到该用户')
        cursor.execute(
            'UPDATE users SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s',
            (new_status, user_id)
        )
        conn.commit()
    meta = get_manage_user_status_meta(new_status)
    return {'userId': user_id, 'status': meta['value'], 'statusText': meta['text'], 'statusClass': meta['class']}

def delete_user_account(conn, user_id):
    """彻底删除用户及关联数据（不可逆）"""
    user_id = int(user_id or 0)
    if user_id <= 0:
        raise ValueError('缺少有效的用户编号')
    with conn.cursor() as cursor:
        cursor.execute('SELECT id, nick_name FROM users WHERE id=%s', (user_id,))
        user = cursor.fetchone()
        if not user:
            raise ValueError('未找到该用户')
        cursor.execute('DELETE FROM wallet_transactions WHERE user_id=%s', (user_id,))
        cursor.execute('DELETE FROM user_wallets WHERE user_id=%s', (user_id,))
        cursor.execute('DELETE FROM recharge_orders WHERE user_id=%s', (user_id,))
        cursor.execute('DELETE FROM transfer_requests WHERE user_id=%s', (user_id,))
        cursor.execute('DELETE FROM feedbacks WHERE user_id=%s', (user_id,))
        cursor.execute('DELETE FROM users WHERE id=%s', (user_id,))
        conn.commit()
    return {'userId': user_id, 'nickName': user.get('nick_name') or ''}

def import_manage_users(conn, raw_text=''):
    text = str(raw_text or '').strip()
    if not text:
        raise ValueError('请先粘贴需要导入的用户内容')

    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_list = []
    preview_rows = []
    base_ts = now_ms()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines, start=1):
        columns = split_manage_import_columns(line)
        if not columns:
            skipped_count += 1
            continue
        header_text = ''.join(columns[:3])
        if index == 1 and any(keyword in header_text for keyword in ('账号', '昵称', '方块', '手机', '邮箱', '状态')):
            continue

        account = str(columns[0] if len(columns) > 0 else '').strip()
        nick_name = str(columns[1] if len(columns) > 1 else '').strip()
        beast_id = str(columns[2] if len(columns) > 2 else '').strip()
        phone = str(columns[3] if len(columns) > 3 else '').strip()
        email = str(columns[4] if len(columns) > 4 else '').strip()
        status_value = parse_manage_user_status(columns[5] if len(columns) > 5 else 1)

        if not any([account, nick_name, beast_id, phone, email]):
            skipped_count += 1
            continue

        try:
            matched_user = find_manage_user_for_import(conn, account=account, beast_id=beast_id, phone=phone, email=email)
            if matched_user:
                updates = []
                params = []
                field_pairs = [
                    ('nick_name', nick_name[:64]),
                    ('account', account[:64]),
                    ('beast_id', beast_id[:32]),
                    ('phone', phone[:32]),
                    ('email', email[:128]),
                ]
                for column_name, value in field_pairs:
                    if value and value != str(matched_user.get(column_name) or ''):
                        updates.append(f"{column_name}=%s")
                        params.append(value)
                if int(matched_user.get('status') or 0) != status_value:
                    updates.append('status=%s')
                    params.append(status_value)
                if updates:
                    params.append(matched_user['id'])
                    with conn.cursor() as cursor:
                        cursor.execute(f"UPDATE users SET {', '.join(updates)}, updated_at=CURRENT_TIMESTAMP WHERE id=%s", tuple(params))
                        cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (matched_user['id'],))
                        matched_user = cursor.fetchone() or matched_user
                    updated_count += 1
                else:
                    skipped_count += 1
                ensure_user_invite_code(conn, matched_user)
                if len(preview_rows) < 12:
                    preview_rows.append(serialize_manage_user_row(matched_user))
                continue

            user_key = f"import_{base_ts}_{index}"
            safe_nick_name = nick_name[:64] or account[:64] or beast_id[:32] or f'导入用户{index}'
            safe_account = account[:64] or f'import_user_{str(base_ts)[-6:]}_{index}'
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO users (user_key, openid, nick_name, avatar_url, account, beast_id, phone, email, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (
                        user_key,
                        None,
                        safe_nick_name,
                        '',
                        safe_account,
                        beast_id[:32],
                        phone[:32],
                        email[:128],
                        status_value,
                    )
                )
                user_id = cursor.lastrowid
                cursor.execute('INSERT INTO user_wallets (user_id) VALUES (%s)', (user_id,))
                cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (user_id,))
                created_user = cursor.fetchone() or {}
            ensure_user_invite_code(conn, created_user)
            created_count += 1
            if len(preview_rows) < 12:
                preview_rows.append(serialize_manage_user_row(created_user))
        except Exception as exc:
            error_list.append({
                'line': index,
                'raw': line,
                'message': str(exc),
            })

    return {
        'createdCount': created_count,
        'updatedCount': updated_count,
        'skippedCount': skipped_count,
        'errorCount': len(error_list),
        'errors': error_list[:20],
        'preview': preview_rows,
    }

def build_manage_pagination(page, page_size, total):
    total = int(total or 0)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        'page': page,
        'pageSize': page_size,
        'total': total,
        'totalPages': total_pages,
    }

def build_manage_recharge_payload(conn, query='', status='all', page=1, page_size=20):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    keyword = str(query or '').strip()
    normalized_status = str(status or 'all').strip() or 'all'

    conditions = []
    params = []
    if keyword:
        like_text = f"%{keyword}%"
        conditions.append(
            "(r.id LIKE %s OR u.nick_name LIKE %s OR u.account LIKE %s OR u.beast_id LIKE %s OR r.verify_code LIKE %s OR r.matched_datetime LIKE %s)"
        )
        params.extend([like_text, like_text, like_text, like_text, like_text, like_text])
    if normalized_status not in ('', 'all'):
        conditions.append('r.status=%s')
        params.append(normalized_status)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    count_sql = f'''
        SELECT COUNT(*) AS total
        FROM recharge_orders r
        LEFT JOIN users u ON u.id = r.user_id
        {where_sql}
    '''
    list_sql = f'''
        SELECT r.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
        FROM recharge_orders r
        LEFT JOIN users u ON u.id = r.user_id
        {where_sql}
        ORDER BY CASE WHEN COALESCE(r.verified_at_ms, 0) > 0 THEN 0 ELSE 1 END,
                 r.verified_at_ms DESC,
                 r.created_at DESC,
                 r.id DESC
        LIMIT {page_size} OFFSET {offset}
    '''

    with conn.cursor() as cursor:
        cursor.execute(count_sql, tuple(params))
        total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute(list_sql, tuple(params))
        rows = cursor.fetchall() or []

    return {
        'pagination': build_manage_pagination(page, page_size, total),
        'list': [serialize_manage_recharge_row(row) for row in rows],
    }

def build_manage_transfer_request_payload(conn, query='', status='all', page=1, page_size=20, pending_only=False):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    keyword = str(query or '').strip()
    normalized_status = str(status or 'all').strip() or 'all'

    conditions = []
    params = []
    if pending_only:
        conditions.append('t.status=%s')
        params.append(TRANSFER_REQUEST_STATUS_PENDING)
    elif normalized_status not in ('', 'all'):
        conditions.append('t.status=%s')
        params.append(normalized_status)
    if keyword:
        like_text = f"%{keyword}%"
        conditions.append(
            "(t.id LIKE %s OR u.nick_name LIKE %s OR u.account LIKE %s OR COALESCE(t.beast_id, u.beast_id, '') LIKE %s OR t.beast_nick LIKE %s OR t.user_note LIKE %s OR t.admin_note LIKE %s)"
        )
        params.extend([like_text, like_text, like_text, like_text, like_text, like_text, like_text])

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    count_sql = f'''
        SELECT COUNT(*) AS total
        FROM gem_transfer_requests t
        LEFT JOIN users u ON u.id = t.user_id
        {where_sql}
    '''
    list_sql = f'''
        SELECT t.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
        FROM gem_transfer_requests t
        LEFT JOIN users u ON u.id = t.user_id
        {where_sql}
        ORDER BY COALESCE(t.processed_at, t.created_at) DESC, t.id DESC
        LIMIT {page_size} OFFSET {offset}
    '''

    with conn.cursor() as cursor:
        cursor.execute(count_sql, tuple(params))
        total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute(list_sql, tuple(params))
        rows = cursor.fetchall() or []

    return {
        'pagination': build_manage_pagination(page, page_size, total),
        'list': [serialize_manage_transfer_request_row(row) for row in rows],
    }

def build_manage_feedback_payload(conn, query='', status='all', page=1, page_size=20, pending_only=False, feedback_type=None, scene=''):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    keyword = str(query or '').strip()
    normalized_status = str(status or 'all').strip() or 'all'
    scoped_scene = normalize_feedback_scene(scene)
    scoped_type = normalize_feedback_type(feedback_type, scoped_scene) if (feedback_type or scoped_scene) else None
    if scoped_scene == FEEDBACK_SCENE_ADMIN_LAYOUT and not (feedback_type or '').strip():
        scoped_type = None

    conditions = []
    params = []
    if pending_only:
        conditions.append('f.status=%s')
        params.append(FEEDBACK_STATUS_PENDING)
    elif normalized_status not in ('', 'all'):
        conditions.append('f.status=%s')
        params.append(normalized_status)
    if scoped_type:
        conditions.append('f.feedback_type=%s')
        params.append(scoped_type)
    if scoped_scene:
        conditions.append('f.scene=%s')
        params.append(scoped_scene)
    else:
        conditions.append('(f.scene IS NULL OR f.scene=%s)')
        params.append('')
    if keyword:
        like_text = f"%{keyword}%"
        conditions.append(
            "(CAST(f.id AS CHAR) LIKE %s OR f.title LIKE %s OR f.content LIKE %s OR f.feedback_type LIKE %s OR f.target_category_label LIKE %s OR f.target_sub_tab LIKE %s OR u.nick_name LIKE %s OR u.account LIKE %s OR u.beast_id LIKE %s OR f.contact LIKE %s OR f.admin_reply LIKE %s)"
        )
        params.extend([like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text])

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    count_sql = f'''
        SELECT COUNT(*) AS total
        FROM user_feedback f
        LEFT JOIN users u ON u.id = f.user_id
        {where_sql}
    '''
    list_sql = f'''
        SELECT f.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
        FROM user_feedback f
        LEFT JOIN users u ON u.id = f.user_id
        {where_sql}
        ORDER BY COALESCE(f.handled_at, f.created_at) DESC, f.id DESC
        LIMIT {page_size} OFFSET {offset}
    '''

    with conn.cursor() as cursor:
        cursor.execute(count_sql, tuple(params))
        total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute(list_sql, tuple(params))
        rows = cursor.fetchall() or []

    return {
        'pagination': build_manage_pagination(page, page_size, total),
        'list': [serialize_manage_feedback_row(row) for row in rows],
    }

def build_manage_guarantee_payload(conn, query='', status='all', page=1, page_size=20, pending_only=False):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    keyword = str(query or '').strip()
    normalized_status = str(status or 'all').strip() or 'all'

    apply_guarantee_matched_abandon_no_proof(conn)
    apply_guarantee_auto_close(conn)
    apply_guarantee_auto_confirm(conn)
    settle_confirmed_guarantee_orders(conn)

    conditions = []
    params = []
    if pending_only:
        conditions.append('g.status=%s')
        conditions.append('g.seller_confirmed_at IS NULL')
        params.append(GUARANTEE_STATUS_MATCHED)

    elif normalized_status not in ('', 'all'):
        conditions.append('g.status=%s')
        params.append(normalized_status)
    if keyword:
        like_text = f"%{keyword}%"
        conditions.append(
            "(g.order_no LIKE %s OR g.pet_name LIKE %s OR seller.nick_name LIKE %s OR seller.account LIKE %s OR g.seller_game_nick LIKE %s OR g.seller_game_id LIKE %s OR buyer.nick_name LIKE %s OR buyer.account LIKE %s OR g.buyer_beast_nick LIKE %s OR g.buyer_beast_id LIKE %s OR g.admin_note LIKE %s OR g.remark LIKE %s)"
        )
        params.extend([like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text])

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    count_sql = f'''
        SELECT COUNT(*) AS total
        FROM guarantee_orders g
        LEFT JOIN users seller ON seller.id = g.seller_user_id
        LEFT JOIN users buyer ON buyer.id = g.buyer_user_id
        {where_sql}
    '''
    list_sql = f'''
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
        ORDER BY COALESCE(g.finished_at, g.seller_confirmed_at, g.matched_at, g.created_at) DESC,
                 g.id DESC
        LIMIT {page_size} OFFSET {offset}
    '''

    with conn.cursor() as cursor:
        cursor.execute(count_sql, tuple(params))
        total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute(list_sql, tuple(params))
        rows = cursor.fetchall() or []

    return {
        'pagination': build_manage_pagination(page, page_size, total),
        'list': [serialize_guarantee_row(row) for row in rows],
    }

def _parse_manage_dashboard_date(value, label):
    text = str(value or '').strip()
    if not text:
        raise ValueError(f'{label}不能为空')
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError(f'{label}格式应为 YYYY-MM-DD') from exc

def build_manage_dashboard(conn, days=7, limit=20, start_date=None, end_date=None):
    limit = max(0, min(100, int(limit)))

    if start_date or end_date:
        if not start_date or not end_date:
            raise ValueError('开始日期和结束日期必须同时提供')
        oldest_date = _parse_manage_dashboard_date(start_date, '开始日期')
        latest_date = _parse_manage_dashboard_date(end_date, '结束日期')
    else:
        days = max(1, min(93, int(days)))
        latest_date = datetime.now().date()
        oldest_date = latest_date - timedelta(days=days - 1)

    if oldest_date > latest_date:
        raise ValueError('开始日期不能晚于结束日期')

    days = (latest_date - oldest_date).days + 1
    if days > 93:
        raise ValueError('日期范围不能超过 93 天')

    oldest_text = oldest_date.strftime('%Y-%m-%d')
    latest_text = latest_date.strftime('%Y-%m-%d')

    apply_guarantee_matched_abandon_no_proof(conn)
    apply_guarantee_auto_close(conn)
    apply_guarantee_auto_confirm(conn)
    settle_confirmed_guarantee_orders(conn)

    with conn.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) AS total FROM users')
        user_count = int((cursor.fetchone() or {}).get('total') or 0)

        cursor.execute('SELECT COALESCE(SUM(gem_balance_x10), 0) AS total_balance_x10, COALESCE(SUM(locked_gems_x10), 0) AS total_locked_x10 FROM user_wallets')
        wallet_summary = cursor.fetchone() or {}

        cursor.execute("SELECT COALESCE(SUM(reward_amount_x10), 0) AS total_x10 FROM promotion_commission_logs")
        promo_reward_summary = cursor.fetchone() or {}

        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total_recharged FROM recharge_orders WHERE status='success'")
        plat_recharge = cursor.fetchone() or {}
        cursor.execute("SELECT COALESCE(SUM(actual_amount_x10), 0) AS total_transferred_x10 FROM gem_transfer_requests WHERE status=%s", (TRANSFER_REQUEST_STATUS_DONE,))
        plat_transfer = cursor.fetchone() or {}

        cursor.execute("SELECT COUNT(*) AS total_count, COALESCE(SUM(amount), 0) AS total_amount FROM recharge_orders WHERE status='success'")
        recharge_summary = cursor.fetchone() or {}

        cursor.execute("SELECT COUNT(*) AS total_count FROM recharge_orders")
        recharge_record_summary = cursor.fetchone() or {}

        cursor.execute('SELECT COUNT(*) AS total_count FROM user_feedback')
        feedback_summary = cursor.fetchone() or {}

        cursor.execute("SELECT COUNT(*) AS total_count FROM guarantee_orders")
        guarantee_record_summary = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(fee_amount_x10 * 2), 0) AS total_fee_amount_x10
            FROM guarantee_orders
            WHERE status=%s
            """,
            (GUARANTEE_STATUS_DONE,)
        )
        guarantee_fee_summary = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(fee_amount_x10), 0) AS total_fee_amount_x10
            FROM gem_transfer_requests
            WHERE status=%s
            """,
            (TRANSFER_REQUEST_STATUS_DONE,)
        )
        transfer_fee_summary = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(amount), 0) AS total_amount
            FROM recharge_orders
            WHERE status='success'
              AND verified_at_ms > 0
              AND DATE(FROM_UNIXTIME(verified_at_ms / 1000)) BETWEEN %s AND %s
            """,
            (oldest_text, latest_text)
        )
        range_recharge = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(GREATEST((gem_amount * 10) - fee_amount_x10, 0)), 0) AS total_amount_x10,
                   COALESCE(SUM(fee_amount_x10 * 2), 0) AS total_fee_amount_x10
            FROM guarantee_orders
            WHERE status=%s
              AND finished_at IS NOT NULL
              AND DATE(finished_at) BETWEEN %s AND %s
            """,
            (GUARANTEE_STATUS_DONE, oldest_text, latest_text)
        )
        range_guarantee_transfer = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(actual_amount_x10), 0) AS total_amount_x10,
                   COALESCE(SUM(fee_amount_x10), 0) AS total_fee_amount_x10
            FROM gem_transfer_requests
            WHERE status=%s
              AND processed_at IS NOT NULL
              AND DATE(processed_at) BETWEEN %s AND %s
            """,
            (TRANSFER_REQUEST_STATUS_DONE, oldest_text, latest_text)
        )
        range_user_transfer = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count
            FROM user_feedback
            WHERE DATE(created_at) BETWEEN %s AND %s
              AND COALESCE(scene, '') != %s
            """,
            (oldest_text, latest_text, FEEDBACK_SCENE_COMMUNITY_APPLY)
        )
        range_feedback = cursor.fetchone() or {}


        cursor.execute(
            "SELECT COUNT(*) AS total_count FROM guarantee_orders WHERE status=%s AND seller_confirmed_at IS NOT NULL",
            (GUARANTEE_STATUS_MATCHED,)
        )
        pending_transfer = cursor.fetchone() or {}

        cursor.execute(
            "SELECT COUNT(*) AS total_count FROM gem_transfer_requests WHERE status=%s",
            (TRANSFER_REQUEST_STATUS_PENDING,)
        )
        pending_withdraw = cursor.fetchone() or {}

        cursor.execute(
            "SELECT COUNT(*) AS total_count FROM user_feedback WHERE status=%s AND COALESCE(scene, '') != %s",
            (FEEDBACK_STATUS_PENDING, FEEDBACK_SCENE_COMMUNITY_APPLY)
        )
        pending_feedback = cursor.fetchone() or {}
        cursor.execute(
            "SELECT COUNT(*) AS total_count FROM user_feedback WHERE status=%s AND COALESCE(scene, '') = %s",
            (FEEDBACK_STATUS_PENDING, FEEDBACK_SCENE_COMMUNITY_APPLY)
        )
        pending_community_apply = cursor.fetchone() or {}


        cursor.execute(
            "SELECT COUNT(*) AS total_count FROM guarantee_orders WHERE status=%s",
            (GUARANTEE_STATUS_DONE,)
        )
        guarantee_done = cursor.fetchone() or {}

        if limit > 0:
            cursor.execute(
                f'''
                SELECT r.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
                FROM recharge_orders r
                LEFT JOIN users u ON u.id = r.user_id
                ORDER BY r.created_at DESC
                LIMIT {limit}
                '''
            )
            recharge_rows = cursor.fetchall() or []

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
                WHERE g.status=%s AND g.seller_confirmed_at IS NOT NULL
                ORDER BY g.seller_confirmed_at DESC, g.matched_at DESC, g.created_at DESC
                LIMIT {limit}
                ''',
                (GUARANTEE_STATUS_MATCHED,)
            )
            pending_transfer_rows = cursor.fetchall() or []

            cursor.execute(
                f'''
                SELECT t.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
                FROM gem_transfer_requests t
                LEFT JOIN users u ON u.id = t.user_id
                WHERE t.status=%s
                ORDER BY t.created_at DESC
                LIMIT {limit}
                ''',
                (TRANSFER_REQUEST_STATUS_PENDING,)
            )
            pending_withdraw_rows = cursor.fetchall() or []

            cursor.execute(
                f'''
                SELECT f.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
                FROM user_feedback f
                LEFT JOIN users u ON u.id = f.user_id
                WHERE f.status=%s
                ORDER BY f.created_at DESC, f.id DESC
                LIMIT {limit}
                ''',
                (FEEDBACK_STATUS_PENDING,)
            )
            pending_feedback_rows = cursor.fetchall() or []

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
                ORDER BY g.created_at DESC
                LIMIT {limit}
                '''
            )
            guarantee_rows = cursor.fetchall() or []

            cursor.execute(
                f'''
                SELECT f.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
                FROM user_feedback f
                LEFT JOIN users u ON u.id = f.user_id
                ORDER BY f.created_at DESC, f.id DESC
                LIMIT {limit}
                '''
            )
            feedback_rows = cursor.fetchall() or []
        else:
            recharge_rows = []
            pending_transfer_rows = []
            pending_withdraw_rows = []
            pending_feedback_rows = []
            guarantee_rows = []
            feedback_rows = []

        cursor.execute(
            '''
            SELECT DATE(FROM_UNIXTIME(verified_at_ms / 1000)) AS stat_date,
                   COUNT(*) AS recharge_count,
                   COALESCE(SUM(amount), 0) AS recharge_amount
            FROM recharge_orders
            WHERE status='success'
              AND verified_at_ms > 0
              AND DATE(FROM_UNIXTIME(verified_at_ms / 1000)) BETWEEN %s AND %s
            GROUP BY DATE(FROM_UNIXTIME(verified_at_ms / 1000))
            ''',
            (oldest_text, latest_text)
        )
        recharge_daily_rows = cursor.fetchall() or []

        cursor.execute(
            '''
            SELECT DATE(created_at) AS stat_date,
                   COUNT(*) AS created_count
            FROM guarantee_orders
            WHERE DATE(created_at) BETWEEN %s AND %s
            GROUP BY DATE(created_at)
            ''',
            (oldest_text, latest_text)
        )
        guarantee_created_rows = cursor.fetchall() or []

        cursor.execute(
            '''
            SELECT DATE(created_at) AS stat_date,
                   COUNT(*) AS feedback_count
            FROM user_feedback
            WHERE DATE(created_at) BETWEEN %s AND %s
              AND COALESCE(scene, '') != %s
            GROUP BY DATE(created_at)
            ''',
            (oldest_text, latest_text, FEEDBACK_SCENE_COMMUNITY_APPLY)
        )
        feedback_created_rows = cursor.fetchall() or []


        cursor.execute(
            '''
            SELECT DATE(finished_at) AS stat_date,
                   COUNT(*) AS transfer_count,
                   COALESCE(SUM(GREATEST((gem_amount * 10) - fee_amount_x10, 0)), 0) AS transfer_amount_x10,
                   COALESCE(SUM(fee_amount_x10 * 2), 0) AS fee_amount_x10
            FROM guarantee_orders
            WHERE status=%s
              AND finished_at IS NOT NULL
              AND DATE(finished_at) BETWEEN %s AND %s
            GROUP BY DATE(finished_at)
            ''',
            (GUARANTEE_STATUS_DONE, oldest_text, latest_text)
        )
        guarantee_done_rows = cursor.fetchall() or []

        cursor.execute(
            '''
            SELECT DATE(processed_at) AS stat_date,
                   COUNT(*) AS transfer_count,
                   COALESCE(SUM(actual_amount_x10), 0) AS transfer_amount_x10,
                   COALESCE(SUM(fee_amount_x10), 0) AS fee_amount_x10
            FROM gem_transfer_requests
            WHERE status=%s
              AND processed_at IS NOT NULL
              AND DATE(processed_at) BETWEEN %s AND %s
            GROUP BY DATE(processed_at)
            ''',
            (TRANSFER_REQUEST_STATUS_DONE, oldest_text, latest_text)
        )
        transfer_request_done_rows = cursor.fetchall() or []

    daily_map = {}
    for offset in range(days):
        current_day = oldest_date + timedelta(days=offset)
        key = current_day.strftime('%Y-%m-%d')
        daily_map[key] = {
            'date': key,
            'rechargeCount': 0,
            'rechargeAmount': 0,
            'guaranteeCreatedCount': 0,
            'feedbackCount': 0,
            'transferCount': 0,
            'transferAmount': 0,
            'guaranteeFeeAmount': 0,
            'withdrawFeeAmount': 0,
            'platformFeeAmount': 0,
        }

    for row in recharge_daily_rows:
        key = str(row.get('stat_date'))
        if key in daily_map:
            daily_map[key]['rechargeCount'] = int(row.get('recharge_count') or 0)
            daily_map[key]['rechargeAmount'] = int(row.get('recharge_amount') or 0)

    for row in guarantee_created_rows:
        key = str(row.get('stat_date'))
        if key in daily_map:
            daily_map[key]['guaranteeCreatedCount'] = int(row.get('created_count') or 0)

    for row in feedback_created_rows:
        key = str(row.get('stat_date'))
        if key in daily_map:
            daily_map[key]['feedbackCount'] = int(row.get('feedback_count') or 0)

    for row in guarantee_done_rows:
        key = str(row.get('stat_date'))
        if key in daily_map:
            daily_map[key]['transferCount'] += int(row.get('transfer_count') or 0)
            daily_map[key]['transferAmount'] += x10_to_amount(row.get('transfer_amount_x10') or 0)
            daily_map[key]['guaranteeFeeAmount'] += x10_to_amount(row.get('fee_amount_x10') or 0)
            daily_map[key]['platformFeeAmount'] += x10_to_amount(row.get('fee_amount_x10') or 0)

    for row in transfer_request_done_rows:
        key = str(row.get('stat_date'))
        if key in daily_map:
            daily_map[key]['transferCount'] += int(row.get('transfer_count') or 0)
            daily_map[key]['transferAmount'] += x10_to_amount(row.get('transfer_amount_x10') or 0)
            daily_map[key]['withdrawFeeAmount'] += x10_to_amount(row.get('fee_amount_x10') or 0)
            daily_map[key]['platformFeeAmount'] += x10_to_amount(row.get('fee_amount_x10') or 0)

    pending_transfer_count = int(pending_transfer.get('total_count') or 0)
    pending_withdraw_count = int(pending_withdraw.get('total_count') or 0)
    pending_feedback_count = int(pending_feedback.get('total_count') or 0)
    pending_community_apply_count = int(pending_community_apply.get('total_count') or 0)

    snapshot = {
        'rechargeCount': int(range_recharge.get('total_count') or 0),
        'rechargeAmount': int(range_recharge.get('total_amount') or 0),
        'transferCount': int(range_guarantee_transfer.get('total_count') or 0) + int(range_user_transfer.get('total_count') or 0),
        'transferAmount': x10_to_amount(range_guarantee_transfer.get('total_amount_x10') or 0) + x10_to_amount(range_user_transfer.get('total_amount_x10') or 0),
        'guaranteeFeeAmount': x10_to_amount(range_guarantee_transfer.get('total_fee_amount_x10') or 0),
        'withdrawFeeAmount': x10_to_amount(range_user_transfer.get('total_fee_amount_x10') or 0),
        'platformFeeAmount': x10_to_amount(range_guarantee_transfer.get('total_fee_amount_x10') or 0) + x10_to_amount(range_user_transfer.get('total_fee_amount_x10') or 0),
        'feedbackCount': int(range_feedback.get('total_count') or 0),
    }

    return {
        'range': {
            'startDate': oldest_text,
            'endDate': latest_text,
            'dayCount': days,
        },
        'totals': {
            'userCount': user_count,
            'walletBalance': x10_to_amount(wallet_summary.get('total_balance_x10') or 0),
            'lockedGems': x10_to_amount(wallet_summary.get('total_locked_x10') or 0),
            'totalRechargeCount': int(recharge_summary.get('total_count') or 0),
            'totalRechargeAmount': int(recharge_summary.get('total_amount') or 0),
            'rechargeRecordCount': int(recharge_record_summary.get('total_count') or 0),
            'completedGuaranteeCount': int(guarantee_done.get('total_count') or 0),
            'guaranteeRecordCount': int(guarantee_record_summary.get('total_count') or 0),
            'totalFeedbackCount': int(feedback_summary.get('total_count') or 0),
            'feedbackRecordCount': int(feedback_summary.get('total_count') or 0),
            'totalGuaranteeFeeAmount': x10_to_amount(guarantee_fee_summary.get('total_fee_amount_x10') or 0),
            'totalWithdrawFeeAmount': x10_to_amount(transfer_fee_summary.get('total_fee_amount_x10') or 0),
            'totalPlatformFeeAmount': x10_to_amount(guarantee_fee_summary.get('total_fee_amount_x10') or 0) + x10_to_amount(transfer_fee_summary.get('total_fee_amount_x10') or 0),
            'pendingTransferCount': pending_transfer_count,
            'pendingWithdrawCount': pending_withdraw_count,
            'pendingFeedbackCount': pending_feedback_count,
            'communityApplyPendingCount': pending_community_apply_count,
            'pendingActionCount': pending_transfer_count + pending_withdraw_count + pending_feedback_count + pending_community_apply_count,
            'totalPromotionReward': x10_to_amount(promo_reward_summary.get('total_x10') or 0),

            'platformAccountBalance': max(0, int(plat_recharge.get('total_recharged') or 0) - x10_to_amount(plat_transfer.get('total_transferred_x10') or 0)),
            'allUsersWalletBalance': x10_to_amount(wallet_summary.get('total_balance_x10') or 0),
        },
        'snapshot': snapshot,
        'today': snapshot,
        'dailyFlow': list(daily_map.values()),
        'rechargeList': [serialize_manage_recharge_row(row) for row in recharge_rows],
        'pendingTransferList': [serialize_guarantee_row(row) for row in pending_transfer_rows],
        'pendingWithdrawList': [serialize_manage_transfer_request_row(row) for row in pending_withdraw_rows],
        'pendingFeedbackList': [serialize_manage_feedback_row(row) for row in pending_feedback_rows],
        'guaranteeList': [serialize_guarantee_row(row) for row in guarantee_rows],
        'feedbackList': [serialize_manage_feedback_row(row) for row in feedback_rows],
    }



# ──────────────────────────────────────────────
#  游戏凭证管理（Token / UserId）
# ──────────────────────────────────────────────
