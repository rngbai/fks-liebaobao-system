from db_mysql import *  # compatibility re-export source for extracted domain functions

def get_app_config_row(conn, config_key):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM app_configs WHERE config_key=%s LIMIT 1', (config_key,))
        return cursor.fetchone()

def load_app_config_json(conn, config_key, default=None):
    row = get_app_config_row(conn, config_key)
    if not row:
        return clone_json_value(default, default), None
    raw_text = row.get('config_value') or ''
    if not raw_text:
        return clone_json_value(default, default), row
    try:
        return json.loads(raw_text), row
    except (TypeError, ValueError, json.JSONDecodeError):
        return clone_json_value(default, default), row

def save_app_config_json(conn, config_key, payload):
    raw_text = json.dumps(payload, ensure_ascii=False)
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO app_configs (config_key, config_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE config_value=VALUES(config_value), updated_at=CURRENT_TIMESTAMP
            ''',
            (config_key, raw_text)
        )

def _parse_jwt_exp(token_str):
    """尝试从 JWT payload 解析过期时间戳（exp 字段），失败则返回 0。"""
    import base64
    try:
        parts = str(token_str or '').split('.')
        if len(parts) < 2:
            return 0
        payload_b64 = parts[1]
        # base64 padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
        return int(payload.get('exp') or 0)
    except Exception:
        return 0

def build_game_config_payload(conn, env_user_id='', env_token='', env_token_type='fks', env_user_name=''):
    """读取游戏凭证配置，DB 优先，无则降级到环境变量。"""
    stored, row = load_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, default={})
    user_id = str(stored.get('userId') or env_user_id or '').strip()
    token = str(stored.get('token') or env_token or '').strip()
    token_type = str(stored.get('tokenType') or env_token_type or 'fks').strip().lower()
    user_name = str(
        stored.get('userName')
        or stored.get('user_name')
        or stored.get('beastNick')
        or stored.get('beast_nick')
        or env_user_name
        or ''
    ).strip()
    if token_type not in ('fks', 'cw'):
        token_type = 'fks'
    exp_ts = _parse_jwt_exp(token)
    now_ts = int(time.time())
    days_left = max(0, round((exp_ts - now_ts) / 86400, 1)) if exp_ts else None
    is_expired = bool(exp_ts and exp_ts <= now_ts)
    return {
        'userId': user_id,
        'userName': user_name,
        'tokenPreview': (token[:12] + '…' + token[-6:]) if len(token) > 20 else token,
        'tokenFull': token,
        'tokenType': token_type,
        'expTimestamp': exp_ts,
        'expText': format_dt(datetime.fromtimestamp(exp_ts)) if exp_ts else '未知',
        'daysLeft': days_left,
        'isExpired': is_expired,
        'source': 'db' if row else 'env',
        'updatedAt': format_dt((row or {}).get('updated_at')),
    }

def save_game_config(conn, user_id, token, token_type='fks', user_name=''):
    """保存游戏凭证到 DB，立即对后续请求生效（无需重启）。"""
    user_id = str(user_id or '').strip()
    token = str(token or '').strip()
    token_type = str(token_type or 'fks').strip().lower()
    stored, _ = load_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, default={})
    user_name = str(
        user_name
        or stored.get('userName')
        or stored.get('user_name')
        or stored.get('beastNick')
        or stored.get('beast_nick')
        or ''
    ).strip()
    if token_type not in ('fks', 'cw'):
        token_type = 'fks'
    if not user_id:
        raise ValueError('userId 不能为空')
    if not token:
        raise ValueError('Token 不能为空')
    save_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, {
        'userId': user_id,
        'userName': user_name,
        'token': token,
        'tokenType': token_type,
    })
    return build_game_config_payload(
        conn,
        env_user_id=user_id,
        env_token=token,
        env_token_type=token_type,
        env_user_name=user_name,
    )

def patch_game_config(conn, user_id=None, token=None, token_type=None, user_name=None):
    """
    部分更新游戏凭证配置：
    - userId / token / userName / tokenType 任意字段可单独更新
    - 未传字段沿用现有值
    """
    current = build_game_config_payload(conn, env_user_id='', env_token='', env_token_type='fks', env_user_name='')
    next_user_id = str(current.get('userId') or '').strip()
    next_token = str(current.get('tokenFull') or '').strip()
    next_user_name = str(current.get('userName') or '').strip()
    next_token_type = str(current.get('tokenType') or 'fks').strip().lower()

    if user_id is not None:
        next_user_id = str(user_id or '').strip()
    if token is not None:
        next_token = str(token or '').strip()
    if user_name is not None:
        next_user_name = str(user_name or '').strip()
    if token_type is not None:
        next_token_type = str(token_type or '').strip().lower() or next_token_type

    if next_token_type not in ('fks', 'cw'):
        next_token_type = 'fks'
    if not next_user_id:
        raise ValueError('userId 不能为空')
    if not next_token:
        raise ValueError('Token 不能为空')

    save_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, {
        'userId': next_user_id,
        'userName': next_user_name,
        'token': next_token,
        'tokenType': next_token_type,
    })
    return build_game_config_payload(
        conn,
        env_user_id=next_user_id,
        env_token=next_token,
        env_token_type=next_token_type,
        env_user_name=next_user_name,
    )

def get_live_game_credentials(conn, env_user_id='', env_token='', env_token_type='fks', env_user_name=''):
    """获取当前生效的游戏凭证（DB 优先 → 环境变量）。每次调用都从 DB 读，热更新无需重启。"""
    stored, _ = load_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, default={})
    user_id = str(stored.get('userId') or env_user_id or '').strip()
    token = str(stored.get('token') or env_token or '').strip()
    token_type = str(stored.get('tokenType') or env_token_type or 'fks').strip().lower()
    user_name = str(
        stored.get('userName')
        or stored.get('user_name')
        or stored.get('beastNick')
        or stored.get('beast_nick')
        or env_user_name
        or ''
    ).strip()
    if token_type not in ('fks', 'cw'):
        token_type = 'fks'
    return user_id, token, token_type, user_name



# ── 社区名流 CRUD ────────────────────────────────────────────────
