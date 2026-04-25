from db_mysql import *  # compatibility re-export source for extracted domain functions

def _normalize_upload_url(value):
    text = str(value or '').strip()
    if not text:
        return ''
    marker = '/uploads/'
    if marker in text:
        return marker + text.split(marker, 1)[1].lstrip('/')
    return text

def _serialize_profile(row):
    if not row:
        return None
    r = dict(row)
    r['avatar_url'] = _normalize_upload_url(r.get('avatar_url'))
    r['is_active'] = bool(r.get('is_active', 1))
    r['created_at'] = format_dt(r.get('created_at'))
    r['updated_at'] = format_dt(r.get('updated_at'))
    return r

def list_community_profiles(conn, category=None, sub_tab=None, active_only=True):
    parts = ['SELECT * FROM community_profiles WHERE 1=1']
    params = []
    if active_only:
        parts.append('AND is_active = 1')
    if category:
        parts.append('AND category = %s')
        params.append(category)
    if sub_tab is not None:
        parts.append('AND sub_tab = %s')
        params.append(sub_tab)
    parts.append('ORDER BY sort_order ASC, id ASC')
    sql = ' '.join(parts)
    with conn.cursor(DictCursor) as cur:
        cur.execute(sql, params)
        return [_serialize_profile(r) for r in cur.fetchall()]

def get_community_profile(conn, profile_id):
    with conn.cursor(DictCursor) as cur:
        cur.execute('SELECT * FROM community_profiles WHERE id = %s', (profile_id,))
        return _serialize_profile(cur.fetchone())

def create_community_profile(conn, data):
    fields = ['category', 'sub_tab', 'nickname', 'bio', 'avatar_url',
              'wechat', 'qq', 'badge_type', 'badge_label', 'game_tag', 'sort_order', 'is_active']
    values = {f: data.get(f, '') for f in fields}
    values['sort_order'] = int(data.get('sort_order', 0))
    values['is_active'] = int(bool(data.get('is_active', True)))
    values['category'] = str(values.get('category') or '').strip()[:32]
    values['sub_tab'] = str(values.get('sub_tab') or '').strip()[:64]
    values['nickname'] = str(values.get('nickname') or '').strip()[:64]
    values['bio'] = str(values.get('bio') or '').strip()[:255]
    values['avatar_url'] = str(values.get('avatar_url') or '').strip()[:512]
    values['wechat'] = str(values.get('wechat') or '').strip()[:64]
    values['qq'] = str(values.get('qq') or '').strip()[:32]
    values['badge_type'] = str(values.get('badge_type') or 'verified').strip()[:32] or 'verified'
    values['badge_label'] = str(values.get('badge_label') or '认证').strip()[:32] or '认证'
    values['game_tag'] = str(values.get('game_tag') or '').strip()[:64]
    if not values['category']:
        raise ValueError('缺少名流主分类')
    if not values['nickname']:
        raise ValueError('请填写名流昵称')
    cols = ', '.join(fields)
    placeholders = ', '.join(['%s'] * len(fields))
    sql = f'INSERT INTO community_profiles ({cols}) VALUES ({placeholders})'
    with conn.cursor() as cur:
        cur.execute(sql, [values[f] for f in fields])
        profile_id = cur.lastrowid
    return get_community_profile(conn, profile_id)

def update_community_profile(conn, profile_id, data):
    allowed = ['category', 'sub_tab', 'nickname', 'bio', 'avatar_url',
               'wechat', 'qq', 'badge_type', 'badge_label', 'game_tag', 'sort_order', 'is_active']
    updates = {}
    for f in allowed:
        if f in data:
            updates[f] = data[f]
    if not updates:
        return get_community_profile(conn, profile_id)
    set_clause = ', '.join([f'{k} = %s' for k in updates])
    sql = f'UPDATE community_profiles SET {set_clause} WHERE id = %s'
    with conn.cursor() as cur:
        cur.execute(sql, list(updates.values()) + [profile_id])
    conn.commit()
    return get_community_profile(conn, profile_id)

def delete_community_profile(conn, profile_id):
    with conn.cursor() as cur:
        cur.execute('DELETE FROM community_profiles WHERE id = %s', (profile_id,))
    conn.commit()
    return cur.rowcount > 0
