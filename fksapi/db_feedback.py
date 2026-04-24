from db_mysql import *  # compatibility re-export source for extracted domain functions

def get_feedback_meta(status):
    return FEEDBACK_STATUS_META.get(status or FEEDBACK_STATUS_PENDING, FEEDBACK_STATUS_META[FEEDBACK_STATUS_PENDING])

def normalize_feedback_scene(scene=''):
    return str(scene or '').strip().lower().replace('-', '_')

def normalize_feedback_type(feedback_type, scene=''):
    normalized_scene = normalize_feedback_scene(scene)
    if normalized_scene == FEEDBACK_SCENE_COMMUNITY_APPLY:
        return FEEDBACK_TYPE_COMMUNITY_APPLY
    return str(feedback_type or '其他').strip()[:32] or '其他'

def get_feedback_daily_limit(feedback_type=''):
    normalized_type = str(feedback_type or '').strip()
    return int(FEEDBACK_TYPE_DAILY_LIMITS.get(normalized_type, DEFAULT_FEEDBACK_DAILY_LIMIT))

def build_feedback_context_text(scene='', extra_context=None):
    normalized_scene = normalize_feedback_scene(scene)
    if normalized_scene != FEEDBACK_SCENE_COMMUNITY_APPLY:
        return ''
    source = extra_context or {}
    category_label = str(source.get('category_label') or source.get('categoryLabel') or source.get('category') or '').strip()
    sub_tab = str(source.get('sub_tab') or source.get('subTab') or '').strip()
    lines = ['申请场景：社区名流认证']
    if category_label:
        lines.append(f'主分类：{category_label}')
    if sub_tab:
        lines.append(f'子分类：{sub_tab}')
    return '\n'.join(lines)

def append_feedback_context(content, scene='', extra_context=None):
    base_content = str(content or '').strip()
    context_text = build_feedback_context_text(scene=scene, extra_context=extra_context)
    if not context_text:
        return base_content[:500]
    suffix = f'【系统附加信息】\n{context_text}'
    if suffix in base_content:
        return base_content[:500]
    merged = f'{base_content}\n\n{suffix}' if base_content else suffix
    return merged[:500].rstrip()

def serialize_feedback_row(row, viewer_user_id=None):

    if not row:
        return None
    status = row.get('status') or FEEDBACK_STATUS_PENDING
    meta = get_feedback_meta(status)
    current_user_id = int(viewer_user_id or 0)
    owner_user_id = int(row.get('user_id') or 0)
    is_mine = current_user_id > 0 and current_user_id == owner_user_id
    return {
        'id': int(row.get('id') or 0),
        'type': row.get('feedback_type') or '其他',
        'title': row.get('title') or '',
        'content': row.get('content') or '',
        'contact': (row.get('contact') or '') if is_mine else '',
        'status': status,
        'statusText': meta['text'],
        'statusDesc': meta['desc'],
        'statusClass': meta['class'],
        'adminReply': row.get('admin_reply') or '',
        'userNickName': row.get('user_nick_name') or '方块兽玩家',
        'isMine': is_mine,
        'time': format_dt(row.get('created_at')),
        'handledTime': format_dt(row.get('handled_at')),
    }

def find_feedback_entry(conn, feedback_id):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT f.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
            FROM user_feedback f
            LEFT JOIN users u ON u.id = f.user_id
            WHERE f.id=%s
            LIMIT 1
            ''',
            (int(feedback_id),)
        )
        return cursor.fetchone()

def find_feedback_entry_for_update(conn, feedback_id):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM user_feedback WHERE id=%s FOR UPDATE', (int(feedback_id),))
        return cursor.fetchone()

def count_today_feedbacks(conn, user_id, feedback_type=None):
    conditions = ['user_id=%s', 'DATE(created_at)=CURDATE()']
    params = [user_id]
    if feedback_type:
        conditions.append('feedback_type=%s')
        params.append(str(feedback_type))
    where_sql = ' AND '.join(conditions)
    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT COUNT(*) AS total
            FROM user_feedback
            WHERE {where_sql}
            ''',
            tuple(params)
        )
        row = cursor.fetchone() or {}
    return int(row.get('total') or 0)

def list_feedback_entries(conn, limit=20, user_id=None, status=None, feedback_type=None):
    limit = max(1, min(100, int(limit)))
    conditions = []
    params = []
    if user_id:
        conditions.append('f.user_id=%s')
        params.append(int(user_id))
    if status:
        conditions.append('f.status=%s')
        params.append(str(status))
    if feedback_type:
        conditions.append('f.feedback_type=%s')
        params.append(str(feedback_type))
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''

    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT f.*, u.nick_name AS user_nick_name, u.account AS user_account, u.beast_id AS user_beast_id
            FROM user_feedback f
            LEFT JOIN users u ON u.id = f.user_id
            {where_sql}
            ORDER BY f.created_at DESC, f.id DESC
            LIMIT {limit}
            ''',
            tuple(params)
        )
        return cursor.fetchall() or []

def create_feedback(conn, user_row, feedback_type, title, content, contact='', scene='', extra_context=None):
    normalized_scene = normalize_feedback_scene(scene)
    feedback_type = normalize_feedback_type(feedback_type, normalized_scene)
    title = str(title or '').strip()[:120]
    content = str(content or '').strip()[:500]
    contact = str(contact or '').strip()[:64]
    extra_context = extra_context or {}
    target_category = str(extra_context.get('category') or '').strip()[:32]
    target_category_label = str(extra_context.get('category_label') or '').strip()[:64]
    target_sub_tab = str(extra_context.get('sub_tab') or '').strip()[:64]
    content = append_feedback_context(content, scene=normalized_scene, extra_context=extra_context)

    if len(title) < 2:
        raise ValueError('请填写反馈标题')

    min_content_length = 10 if normalized_scene == FEEDBACK_SCENE_COMMUNITY_APPLY else 5
    if len(content) < min_content_length:
        if normalized_scene == FEEDBACK_SCENE_COMMUNITY_APPLY:
            raise ValueError('申请认证请尽量写详细一点，至少 10 个字')
        raise ValueError('请尽量详细描述问题，至少 5 个字')

    if normalized_scene == FEEDBACK_SCENE_COMMUNITY_APPLY and len(contact) < 2:
        raise ValueError('申请认证请填写联系方式，方便审核联系')

    type_daily_limit = get_feedback_daily_limit(feedback_type)
    type_today_count = count_today_feedbacks(conn, user_row['id'], feedback_type=feedback_type)
    if normalized_scene != FEEDBACK_SCENE_ADMIN_LAYOUT:
        if type_today_count >= type_daily_limit:
            if feedback_type == FEEDBACK_TYPE_COMMUNITY_APPLY:
                raise ValueError(f'社区名流认证申请每天最多提交 {type_daily_limit} 次，请明天再试')
            raise ValueError(f'该类型反馈每天最多提交 {type_daily_limit} 次，请明天再试')

        today_count = count_today_feedbacks(conn, user_row['id'])
        if today_count >= DEFAULT_FEEDBACK_DAILY_LIMIT:
            raise ValueError(f'每天最多提交 {DEFAULT_FEEDBACK_DAILY_LIMIT} 次反馈，请明天再试')

    with conn.cursor() as cursor:

        cursor.execute(
            '''
            INSERT INTO user_feedback (
                user_id, feedback_type, title, content, contact,
                scene, target_category, target_category_label, target_sub_tab, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (
                user_row['id'],
                feedback_type,
                title,
                content,
                contact,
                normalized_scene,
                target_category,
                target_category_label,
                target_sub_tab,
                FEEDBACK_STATUS_PENDING,
            )
        )
        feedback_id = cursor.lastrowid

    return find_feedback_entry(conn, feedback_id)

def update_feedback_status(conn, feedback_id, status, admin_reply=''):
    feedback_id = int(feedback_id or 0)
    if feedback_id <= 0:
        raise ValueError('缺少有效的反馈编号')

    status = str(status or '').strip() or FEEDBACK_STATUS_PENDING
    if status not in FEEDBACK_STATUS_META:
        raise ValueError('反馈状态不合法')

    feedback_row = find_feedback_entry_for_update(conn, feedback_id)
    if not feedback_row:
        raise ValueError('未找到反馈记录')

    reply_text = str(admin_reply or '').strip()
    if not reply_text and status == FEEDBACK_STATUS_ADOPTED:
        reply_text = '该反馈已采纳，我们会尽快安排处理。'
    elif not reply_text and status == FEEDBACK_STATUS_COMPLETED:
        reply_text = '该反馈已处理完成，感谢你的建议。'
    elif not reply_text and status == FEEDBACK_STATUS_REJECTED:
        reply_text = '该反馈已收到，但当前版本暂不处理。'

    handled_at_sql = 'NULL' if status == FEEDBACK_STATUS_PENDING else 'CURRENT_TIMESTAMP'

    with conn.cursor() as cursor:
        cursor.execute(
            f'''
            UPDATE user_feedback
            SET status=%s,
                admin_reply=%s,
                handled_at={handled_at_sql},
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            ''',
            (status, reply_text[:255], feedback_id)
        )

    return find_feedback_entry(conn, feedback_id)

def approve_community_feedback(conn, feedback_id, profile_payload, admin_reply=''):
    feedback_id = int(feedback_id or 0)
    if feedback_id <= 0:
        raise ValueError('缺少有效的反馈编号')

    feedback_row = find_feedback_entry_for_update(conn, feedback_id)
    if not feedback_row:
        raise ValueError('未找到反馈记录')
    if normalize_feedback_scene(feedback_row.get('scene')) != FEEDBACK_SCENE_COMMUNITY_APPLY:
        raise ValueError('该记录不是名流认证申请')
    if (feedback_row.get('status') or FEEDBACK_STATUS_PENDING) != FEEDBACK_STATUS_PENDING:
        raise ValueError('该认证申请已处理，不能重复通过')
    if int(feedback_row.get('linked_profile_id') or 0) > 0:
        raise ValueError('该认证申请已关联名流记录，不能重复通过')

    profile_data = dict(profile_payload or {})

    if not str(profile_data.get('category') or '').strip():
        profile_data['category'] = feedback_row.get('target_category') or ''
    if profile_data.get('sub_tab') is None or str(profile_data.get('sub_tab') or '').strip() == '':
        profile_data['sub_tab'] = feedback_row.get('target_sub_tab') or ''
    if not str(profile_data.get('nickname') or '').strip():
        profile_data['nickname'] = feedback_row.get('user_nick_name') or '社区名流'
    if not str(profile_data.get('bio') or '').strip():
        profile_data['bio'] = feedback_row.get('content') or ''
    if not str(profile_data.get('wechat') or '').strip() and not str(profile_data.get('qq') or '').strip():
        profile_data['wechat'] = feedback_row.get('contact') or ''
    if not str(profile_data.get('badge_type') or '').strip():
        profile_data['badge_type'] = 'verified'
    if not str(profile_data.get('badge_label') or '').strip():
        profile_data['badge_label'] = '认证'
    if 'is_active' not in profile_data:
        profile_data['is_active'] = True

    created_profile = create_community_profile(conn, profile_data)
    reply_text = str(admin_reply or '').strip() or '社区名流认证已通过，已加入对应板块展示。'

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE user_feedback
            SET status=%s,
                admin_reply=%s,
                linked_profile_id=%s,
                handled_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            ''',
            (FEEDBACK_STATUS_COMPLETED, reply_text[:255], int(created_profile.get('id') or 0), feedback_id)
        )

    return {
        'feedback': find_feedback_entry(conn, feedback_id),
        'profile': created_profile,
    }

def build_feedback_payload(conn, user_row, limit=20, mine_only=False, feedback_type=None, scene=''):
    normalized_scene = normalize_feedback_scene(scene)
    scoped_type = normalize_feedback_type(feedback_type, normalized_scene) if (feedback_type or normalized_scene) else None
    daily_limit = get_feedback_daily_limit(scoped_type) if scoped_type else DEFAULT_FEEDBACK_DAILY_LIMIT
    today_count = count_today_feedbacks(conn, user_row['id'], feedback_type=scoped_type)
    rows = list_feedback_entries(
        conn,
        limit=limit,
        user_id=user_row['id'] if mine_only else None,
        feedback_type=scoped_type,
    )
    return {
        'user': serialize_user(user_row),
        'feedback': {
            'scene': normalized_scene,
            'feedbackType': scoped_type or '',
            'dailyLimit': daily_limit,
            'todayCount': today_count,
            'remainingCount': max(0, daily_limit - today_count),
            'mineOnly': bool(mine_only),
            'list': [serialize_feedback_row(row, viewer_user_id=user_row['id']) for row in rows],
        }
    }

def serialize_manage_feedback_row(row):
    payload = serialize_feedback_row(row, viewer_user_id=row.get('user_id')) or {}
    payload.update({
        'contact': row.get('contact') or '',
        'account': row.get('user_account') or '',
        'beastId': normalize_beast_id_value(row.get('user_beast_id')),
        'scene': row.get('scene') or '',
        'targetCategory': row.get('target_category') or '',
        'targetCategoryLabel': row.get('target_category_label') or '',
        'targetSubTab': row.get('target_sub_tab') or '',
        'linkedProfileId': int(row.get('linked_profile_id') or 0),
    })
    return payload
