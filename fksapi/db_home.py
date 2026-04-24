from db_mysql import *  # compatibility re-export source for extracted domain functions

def normalize_home_item_id(raw_id, prefix='slot', index=0):
    text = str(raw_id or '').strip().replace(' ', '-').replace('/', '-').replace('\\', '-')
    return (text[:48] or f'{prefix}-{index + 1}')

def normalize_home_action_type(value, default='none'):
    action_type = str(value or default or 'none').strip()
    if action_type in HOME_ACTION_TYPES:
        return action_type
    return default if default in HOME_ACTION_TYPES else 'none'

def normalize_home_group(payload=None):
    source = payload if isinstance(payload, dict) else {}
    return {
        'name': sanitize_text(source.get('name'), HOME_OFFICIAL_GROUP_DEFAULT['name'], 64),
        'qq': sanitize_text(source.get('qq'), HOME_OFFICIAL_GROUP_DEFAULT['qq'], 32),
    }

def normalize_home_top_banner_item(item=None, index=0, default_item=None):
    source = item if isinstance(item, dict) else {}
    default_row = default_item if isinstance(default_item, dict) else {}
    action_type = normalize_home_action_type(source.get('type'), default_row.get('type') or 'group')
    return {
        'id': normalize_home_item_id(source.get('id') or default_row.get('id'), 'top', index),
        'label': sanitize_text(source.get('label'), default_row.get('label') or '广告', 16),
        'title': sanitize_text(source.get('title'), default_row.get('title') or '首页广告位', 64),
        'desc': sanitize_text(source.get('desc'), default_row.get('desc') or '', 160),
        'brand': sanitize_text(source.get('brand'), default_row.get('brand') or '', 32),
        'cta': sanitize_text(source.get('cta'), default_row.get('cta') or '立即查看', 20),
        'visualTitle': sanitize_text(source.get('visualTitle'), default_row.get('visualTitle') or '', 32),
        'visualTag': sanitize_text(source.get('visualTag'), default_row.get('visualTag') or '', 32),
        'type': action_type,
        'url': sanitize_text(source.get('url'), default_row.get('url') or '', 255) if action_type in {'navigate', 'switchTab'} else '',
        'qq': sanitize_text(source.get('qq'), default_row.get('qq') or '', 32) if action_type == 'group' else '',
        'gradient': sanitize_text(
            source.get('gradient'),
            default_row.get('gradient') or 'linear-gradient(135deg,#f7f8fc 0%,#ffffff 52%,#eef3ff 100%)',
            255,
        ),
    }

def normalize_home_promo_card_item(item=None, index=0, default_item=None):
    source = item if isinstance(item, dict) else {}
    default_row = default_item if isinstance(default_item, dict) else {}
    action_type = normalize_home_action_type(source.get('type'), default_row.get('type') or 'group')
    return {
        'id': normalize_home_item_id(source.get('id') or default_row.get('id'), 'promo', index),
        'title': sanitize_text(source.get('title'), default_row.get('title') or '推荐位', 64),
        'subtitle': sanitize_text(source.get('subtitle'), default_row.get('subtitle') or '', 180),
        'badge': sanitize_text(source.get('badge'), default_row.get('badge') or '', 20),
        'accent': sanitize_text(source.get('accent'), default_row.get('accent') or '立即查看', 20),
        'type': action_type,
        'url': sanitize_text(source.get('url'), default_row.get('url') or '', 255) if action_type in {'navigate', 'switchTab'} else '',
        'qq': sanitize_text(source.get('qq'), default_row.get('qq') or '', 32) if action_type == 'group' else '',
        'gradient': sanitize_text(
            source.get('gradient'),
            default_row.get('gradient') or 'linear-gradient(135deg,#171a3b 0%,#3247c5 55%,#60d7ff 100%)',
            255,
        ),
    }

def normalize_home_top_banner_list(items=None):
    source_list = items if isinstance(items, list) else HOME_TOP_BANNER_DEFAULTS
    normalized = []
    for index, item in enumerate(source_list[:12]):
        default_item = HOME_TOP_BANNER_DEFAULTS[index] if index < len(HOME_TOP_BANNER_DEFAULTS) else HOME_TOP_BANNER_DEFAULTS[-1]
        normalized.append(normalize_home_top_banner_item(item, index=index, default_item=default_item))
    return normalized or clone_json_value(HOME_TOP_BANNER_DEFAULTS, HOME_TOP_BANNER_DEFAULTS)

def normalize_home_promo_card_list(items=None):
    source_list = items if isinstance(items, list) else HOME_PROMO_CARD_DEFAULTS
    normalized = []
    for index, item in enumerate(source_list[:12]):
        default_item = HOME_PROMO_CARD_DEFAULTS[index] if index < len(HOME_PROMO_CARD_DEFAULTS) else HOME_PROMO_CARD_DEFAULTS[-1]
        normalized.append(normalize_home_promo_card_item(item, index=index, default_item=default_item))
    return normalized or clone_json_value(HOME_PROMO_CARD_DEFAULTS, HOME_PROMO_CARD_DEFAULTS)

def normalize_home_content_payload(payload=None):
    source = payload if isinstance(payload, dict) else {}
    return {
        'hotNotice': sanitize_text(source.get('hotNotice'), HOME_NOTICE_DEFAULT, 200),
        'officialGroup': normalize_home_group(source.get('officialGroup')),
        'topBanners': normalize_home_top_banner_list(source.get('topBanners')),
        'bannerCards': normalize_home_promo_card_list(source.get('bannerCards')),
    }

def build_home_content_summary(content, updated_at=''):
    official_group = (content or {}).get('officialGroup') or {}
    return {
        'topBannerCount': len((content or {}).get('topBanners') or []),
        'bannerCardCount': len((content or {}).get('bannerCards') or []),
        'slotCount': len((content or {}).get('topBanners') or []) + len((content or {}).get('bannerCards') or []),
        'noticeLength': len(str((content or {}).get('hotNotice') or '')),
        'officialGroupQq': str(official_group.get('qq') or ''),
        'updatedAt': updated_at,
    }

def build_home_content_payload(conn):
    stored_payload, row = load_app_config_json(conn, HOME_CONTENT_CONFIG_KEY, default=normalize_home_content_payload())
    content = normalize_home_content_payload(stored_payload)
    if row is None:
        save_app_config_json(conn, HOME_CONTENT_CONFIG_KEY, content)
        row = get_app_config_row(conn, HOME_CONTENT_CONFIG_KEY)
    return {
        **content,
        'updatedAt': format_dt((row or {}).get('updated_at')),
    }

def build_manage_home_content_payload(conn):
    content = build_home_content_payload(conn)
    updated_at = content.get('updatedAt') or ''
    pure_content = {
        'hotNotice': content.get('hotNotice') or HOME_NOTICE_DEFAULT,
        'officialGroup': content.get('officialGroup') or normalize_home_group(),
        'topBanners': clone_json_value(content.get('topBanners'), HOME_TOP_BANNER_DEFAULTS),
        'bannerCards': clone_json_value(content.get('bannerCards'), HOME_PROMO_CARD_DEFAULTS),
    }
    return {
        'summary': build_home_content_summary(pure_content, updated_at=updated_at),
        'content': pure_content,
        'updatedAt': updated_at,
        'configKey': HOME_CONTENT_CONFIG_KEY,
    }

def save_manage_home_content_payload(conn, payload=None):
    content = normalize_home_content_payload(payload)
    save_app_config_json(conn, HOME_CONTENT_CONFIG_KEY, content)
    return build_manage_home_content_payload(conn)
