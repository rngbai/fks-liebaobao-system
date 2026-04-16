import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

import pymysql
from pymysql.cursors import DictCursor

DB_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
DB_USER = os.environ.get('MYSQL_USER', 'fks_user')
DB_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
DB_NAME = os.environ.get('MYSQL_DATABASE', 'fks_trade')
DEFAULT_GEM_BALANCE = 256
DEFAULT_CANCEL_LIMIT = 5
DEFAULT_GUARANTEE_FEE = 1
DEFAULT_TRANSFER_OUT_DAILY_LIMIT = 10
DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS = 50
DEFAULT_FEEDBACK_DAILY_LIMIT = 3
# 2级分销：每单双方各扣1宝石，拿出50%做推广激励（共1宝石/单）
PROMO_COMMISSION_L1_X10 = 8    # 一级分佣 0.8 宝石 (×10 存储)
PROMO_COMMISSION_L2_X10 = 2    # 二级分佣 0.2 宝石 (×10 存储)
PROMO_FIRST_ORDER_BONUS = 2    # 新人首单奖励 2 宝石（整数）
PROMO_TIER_RULES = [
    {'min_orders': 100, 'extra_x10': 3},   # ≥100单/月额外 +0.3/单
    {'min_orders': 30,  'extra_x10': 2},   # ≥30单/月额外 +0.2/单
]
PROMO_TOP5_REWARDS = [50, 30, 20, 10, 5]  # 月度Top5奖励（宝石）
HOME_CONTENT_CONFIG_KEY = 'home_content'
GAME_CREDENTIALS_CONFIG_KEY = 'game_credentials'
HOME_ACTION_TYPES = {'group', 'navigate', 'switchTab', 'none'}
HOME_NOTICE_DEFAULT = '首页顶部轮播和中部活动轮播都保留，官方群、榜单、担保入口统一集中。'
HOME_OFFICIAL_GROUP_DEFAULT = {
    'name': '方块兽交易交流群',
    'qq': '769851293',
}
HOME_TOP_BANNER_DEFAULTS = [
    {
        'id': 'top-group',
        'label': '广告',
        'title': '官方群与攻略助手入口',
        'desc': '点击广告位直接进群详情，群号 769851293，少走弯路。',
        'brand': '官方社群推荐',
        'cta': '立即查看',
        'visualTitle': 'QQ 交流群',
        'visualTag': '769851293',
        'type': 'group',
        'url': '',
        'qq': '769851293',
        'gradient': 'linear-gradient(135deg,#f7f8fc 0%,#ffffff 52%,#eef3ff 100%)',
    },
    {
        'id': 'top-rank',
        'label': '广告',
        'title': '担保达人榜 / 推荐贡献榜',
        'desc': '排行榜独立成页，顶部广告位也能直接点进去看完整榜单。',
        'brand': '榜单中心',
        'cta': '立即前往',
        'visualTitle': '今日热榜',
        'visualTag': '成功率榜',
        'type': 'navigate',
        'url': '/pages/rank/rank',
        'qq': '',
        'gradient': 'linear-gradient(135deg,#f9f5ff 0%,#ffffff 52%,#eef8ff 100%)',
    },
    {
        'id': 'top-guarantee',
        'label': '广告',
        'title': '担保、转入、市场一站直达',
        'desc': '顶部轮播保留成广告位样式，直接跳转担保中心和常用功能。',
        'brand': '交易服务',
        'cta': '去担保',
        'visualTitle': '担保交易',
        'visualTag': '安全托底',
        'type': 'switchTab',
        'url': '/pages/guarantee/guarantee',
        'qq': '',
        'gradient': 'linear-gradient(135deg,#f4fbff 0%,#ffffff 48%,#eaf6ff 100%)',
    },
]
HOME_PROMO_CARD_DEFAULTS = [
    {
        'id': 'promo-group',
        'title': '官方交易交流群',
        'subtitle': '点进卡片直接获取加群方式，第一时间交流行情和担保经验。',
        'badge': 'QQ 群',
        'accent': '立即加群',
        'type': 'group',
        'url': '',
        'qq': '769851293',
        'gradient': 'linear-gradient(135deg,#171a3b 0%,#3247c5 55%,#60d7ff 100%)',
    },
    {
        'id': 'promo-guarantee',
        'title': '担保交易全流程护航',
        'subtitle': '下单、转入、查询、申诉一条链路直达，减少来回找入口。',
        'badge': '平台功能',
        'accent': '去担保',
        'type': 'switchTab',
        'url': '/pages/guarantee/guarantee',
        'qq': '',
        'gradient': 'linear-gradient(135deg,#21163d 0%,#7c3aed 45%,#f59e0b 100%)',
    },
    {
        'id': 'promo-rank',
        'title': '榜单中心全新上线',
        'subtitle': '把担保达人榜和推荐贡献榜单独做成一个入口，首页不再挤。',
        'badge': '独立导航',
        'accent': '看榜单',
        'type': 'navigate',
        'url': '/pages/rank/rank',
        'qq': '',
        'gradient': 'linear-gradient(135deg,#12243d 0%,#0f766e 45%,#38bdf8 100%)',
    },
]

FEEDBACK_STATUS_PENDING = 'pending'

FEEDBACK_STATUS_ADOPTED = 'adopted'
FEEDBACK_STATUS_COMPLETED = 'completed'
FEEDBACK_STATUS_REJECTED = 'rejected'

FEEDBACK_STATUS_META = {
    FEEDBACK_STATUS_PENDING: {
        'text': '待处理',
        'desc': '等待后台查看',
        'class': 'pending',
    },
    FEEDBACK_STATUS_ADOPTED: {
        'text': '已采纳',
        'desc': '后台已采纳该反馈',
        'class': 'adopted',
    },
    FEEDBACK_STATUS_COMPLETED: {
        'text': '已完成',
        'desc': '该反馈已处理完成',
        'class': 'completed',
    },
    FEEDBACK_STATUS_REJECTED: {
        'text': '暂不处理',
        'desc': '当前版本暂不处理该反馈',
        'class': 'rejected',
    },
}

TRANSFER_REQUEST_STATUS_PENDING = 'pending'
TRANSFER_REQUEST_STATUS_DONE = 'done'
TRANSFER_REQUEST_STATUS_CANCELLED = 'cancelled'
TRANSFER_REQUEST_STATUS_REJECTED = 'rejected'

TRANSFER_REQUEST_STATUS_META = {
    TRANSFER_REQUEST_STATUS_PENDING: {
        'text': '待处理',
        'desc': '等待后台人工转出',
        'class': 'pending',
    },
    TRANSFER_REQUEST_STATUS_DONE: {
        'text': '已完成',
        'desc': '后台已登记转出完成',
        'class': 'done',
    },
    TRANSFER_REQUEST_STATUS_CANCELLED: {
        'text': '已取消',
        'desc': '该转出申请已取消',
        'class': 'cancelled',
    },
    TRANSFER_REQUEST_STATUS_REJECTED: {
        'text': '已拒绝',
        'desc': '后台已拒绝本次转出申请',
        'class': 'rejected',
    },
}



GUARANTEE_STATUS_PENDING = 'pending'
GUARANTEE_STATUS_MATCHED = 'matched'
GUARANTEE_STATUS_DONE = 'done'
GUARANTEE_STATUS_APPEAL = 'appeal'
GUARANTEE_AUTO_CONFIRM_HOURS = 2

GUARANTEE_STATUS_META = {

    GUARANTEE_STATUS_PENDING: {
        'index': 0,
        'text': '等待买家比配',
        'short_text': '等待中',
        'desc': '等待买家提交方块兽 ID、昵称与交易说明',
        'class': 'pending',
    },
    GUARANTEE_STATUS_MATCHED: {
        'index': 1,
        'text': '待卖家确认',
        'short_text': '待确认',
        'desc': '买家已提交资料，等待卖家核对交易是否真实完成',
        'class': 'matched',
    },
    GUARANTEE_STATUS_DONE: {
        'index': 2,
        'text': '已完成',
        'short_text': '已完成',
        'desc': '系统已自动发放宝石给买家',
        'class': 'done',
    },

    GUARANTEE_STATUS_APPEAL: {
        'index': 3,
        'text': '申诉中',
        'short_text': '申诉中',
        'desc': '订单申诉处理中',
        'class': 'appeal',
    },
}

RECHARGE_STATUS_META = {
    'pending': {'text': '待验证', 'class': 'pending'},
    'success': {'text': '已到账', 'class': 'success'},
    'cancelled': {'text': '已取消', 'class': 'cancelled'},
    'expired': {'text': '已超时', 'class': 'expired'},
}

CREATE_DATABASE_SQL = f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_key VARCHAR(64) NOT NULL UNIQUE,
        openid VARCHAR(64) DEFAULT NULL,
        nick_name VARCHAR(64) NOT NULL DEFAULT '方块兽玩家',
        avatar_url VARCHAR(255) NOT NULL DEFAULT '',
        account VARCHAR(64) NOT NULL DEFAULT '',
        beast_id VARCHAR(32) NOT NULL DEFAULT '',
        phone VARCHAR(32) NOT NULL DEFAULT '',
        email VARCHAR(128) NOT NULL DEFAULT '',
        status TINYINT NOT NULL DEFAULT 1,
        invite_code VARCHAR(16) NOT NULL DEFAULT '',
        invited_by_user_id BIGINT DEFAULT NULL,
        invited_at DATETIME DEFAULT NULL,
        promotion_effective_at DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_openid (openid),
        INDEX idx_invite_code (invite_code),
        INDEX idx_invited_by (invited_by_user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    f"""
    CREATE TABLE IF NOT EXISTS user_wallets (
        user_id BIGINT PRIMARY KEY,
        gem_balance INT NOT NULL DEFAULT {DEFAULT_GEM_BALANCE},
        locked_gems INT NOT NULL DEFAULT 0,
        total_recharged INT NOT NULL DEFAULT 0,
        total_spent INT NOT NULL DEFAULT 0,
        total_earned INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_updated_at (updated_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS wallet_transactions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        biz_type VARCHAR(32) NOT NULL,
        change_amount INT NOT NULL,
        balance_before INT NOT NULL,
        balance_after INT NOT NULL,
        ref_type VARCHAR(32) NOT NULL DEFAULT '',
        ref_id VARCHAR(64) NOT NULL DEFAULT '',
        remark VARCHAR(255) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_created (user_id, created_at DESC),
        INDEX idx_ref (ref_type, ref_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS recharge_orders (
        id VARCHAR(32) PRIMARY KEY,
        user_id BIGINT NOT NULL,
        amount INT NOT NULL,
        beast_id VARCHAR(32) NOT NULL,
        beast_nick VARCHAR(64) NOT NULL,
        verify_code VARCHAR(4) NOT NULL DEFAULT '',
        matched_datetime VARCHAR(32) NOT NULL DEFAULT '',
        matched_timestamp BIGINT NOT NULL DEFAULT 0,
        status VARCHAR(16) NOT NULL DEFAULT 'pending',
        create_source VARCHAR(16) NOT NULL DEFAULT 'miniapp',
        created_at_ms BIGINT NOT NULL,
        expire_at_ms BIGINT NOT NULL,
        verified_at_ms BIGINT NOT NULL DEFAULT 0,
        cancelled_at_ms BIGINT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_status_created (user_id, status, created_at_ms DESC),
        INDEX idx_status_expire (status, expire_at_ms)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    f"""
    CREATE TABLE IF NOT EXISTS guarantee_orders (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_no VARCHAR(32) NOT NULL UNIQUE,
        seller_user_id BIGINT NOT NULL,
        buyer_user_id BIGINT DEFAULT NULL,
        seller_beast_id VARCHAR(32) NOT NULL DEFAULT '',
        pet_name VARCHAR(64) NOT NULL DEFAULT '',
        trade_quantity INT NOT NULL DEFAULT 1,
        seller_game_id VARCHAR(32) NOT NULL DEFAULT '',
        seller_game_nick VARCHAR(64) NOT NULL DEFAULT '',
        buyer_beast_id VARCHAR(32) NOT NULL DEFAULT '',
        buyer_beast_nick VARCHAR(64) NOT NULL DEFAULT '',
        buyer_trade_note VARCHAR(255) NOT NULL DEFAULT '',
        buyer_proof_image VARCHAR(255) NOT NULL DEFAULT '',
        buyer_proof_uploaded_at DATETIME DEFAULT NULL,
        gem_amount INT NOT NULL,

        fee_amount INT NOT NULL DEFAULT {DEFAULT_GUARANTEE_FEE},
        remark VARCHAR(255) NOT NULL DEFAULT '',
        admin_note VARCHAR(255) NOT NULL DEFAULT '',
        status VARCHAR(16) NOT NULL DEFAULT 'pending',
        appeal_reason VARCHAR(255) NOT NULL DEFAULT '',
        matched_at DATETIME DEFAULT NULL,
        seller_confirmed_at DATETIME DEFAULT NULL,
        finished_at DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_seller_status_created (seller_user_id, status, created_at DESC),
        INDEX idx_buyer_status_created (buyer_user_id, status, created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4

    """,
    f"""
    CREATE TABLE IF NOT EXISTS gem_transfer_requests (
        id VARCHAR(32) PRIMARY KEY,
        user_id BIGINT NOT NULL,
        beast_id VARCHAR(32) NOT NULL DEFAULT '',
        beast_nick VARCHAR(64) NOT NULL DEFAULT '',
        request_amount INT NOT NULL,
        fee_amount INT NOT NULL DEFAULT 0,
        actual_amount INT NOT NULL DEFAULT 0,
        fee_basis_points INT NOT NULL DEFAULT {DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS},
        status VARCHAR(16) NOT NULL DEFAULT 'pending',
        user_note VARCHAR(255) NOT NULL DEFAULT '',
        admin_note VARCHAR(255) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        processed_at DATETIME DEFAULT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_created (user_id, created_at DESC),
        INDEX idx_status_created (status, created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS market_listings (

        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        order_no VARCHAR(32) NOT NULL UNIQUE,
        user_id BIGINT NOT NULL,
        listing_type VARCHAR(8) NOT NULL,
        title VARCHAR(128) NOT NULL DEFAULT '',
        quantity INT NOT NULL DEFAULT 0,
        price_per INT NOT NULL DEFAULT 0,
        seller_nick VARCHAR(64) NOT NULL DEFAULT '',
        contact_info VARCHAR(128) NOT NULL DEFAULT '',
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_type_status (user_id, listing_type, status),
        INDEX idx_status_created (status, created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_feedback (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        feedback_type VARCHAR(32) NOT NULL DEFAULT '其他',
        title VARCHAR(120) NOT NULL DEFAULT '',
        content VARCHAR(500) NOT NULL DEFAULT '',
        contact VARCHAR(64) NOT NULL DEFAULT '',
        status VARCHAR(16) NOT NULL DEFAULT 'pending',
        admin_reply VARCHAR(255) NOT NULL DEFAULT '',
        handled_at DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_created (user_id, created_at DESC),
        INDEX idx_status_created (status, created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_messages (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        msg_type VARCHAR(32) NOT NULL,
        title VARCHAR(128) NOT NULL DEFAULT '',
        content VARCHAR(255) NOT NULL DEFAULT '',
        related_type VARCHAR(32) NOT NULL DEFAULT '',
        related_id VARCHAR(64) NOT NULL DEFAULT '',
        is_read TINYINT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_read_created (user_id, is_read, created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS promotion_reward_logs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        invitee_user_id BIGINT DEFAULT NULL,
        reward_type VARCHAR(32) NOT NULL DEFAULT 'milestone',
        trigger_threshold INT NOT NULL DEFAULT 0,
        reward_amount INT NOT NULL DEFAULT 0,
        remark VARCHAR(255) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_user_reward (user_id, reward_type, trigger_threshold),
        INDEX idx_user_created (user_id, created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS app_configs (
        config_key VARCHAR(64) PRIMARY KEY,
        config_value LONGTEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS promotion_commission_logs (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        user_id BIGINT NOT NULL,
        invitee_user_id BIGINT NOT NULL,
        reward_type VARCHAR(32) NOT NULL COMMENT 'l1_commission/l2_commission/first_order_bonus/monthly_tier/monthly_top5',
        order_no VARCHAR(64) NOT NULL DEFAULT '',
        reward_amount_x10 INT NOT NULL DEFAULT 0 COMMENT '奖励额×10，避免小数：8=0.8宝石',
        flushed_amount INT NOT NULL DEFAULT 0 COMMENT '实际发放到钱包的整宝石数',
        remark VARCHAR(255) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_commission (user_id, reward_type, order_no),
        INDEX idx_user_created (user_id, created_at DESC),
        INDEX idx_invitee (invitee_user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS community_profiles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        category VARCHAR(32) NOT NULL COMMENT 'captain/broker/streamer/blogger/guild',
        sub_tab VARCHAR(64) NOT NULL DEFAULT '' COMMENT '子分类标签',
        nickname VARCHAR(64) NOT NULL,
        bio VARCHAR(255) NOT NULL DEFAULT '',
        avatar_url VARCHAR(512) NOT NULL DEFAULT '',
        wechat VARCHAR(64) NOT NULL DEFAULT '',
        qq VARCHAR(32) NOT NULL DEFAULT '',
        badge_type VARCHAR(32) NOT NULL DEFAULT 'verified' COMMENT 'gold/silver/verified/streamer/guild',
        badge_label VARCHAR(32) NOT NULL DEFAULT '认证',
        game_tag VARCHAR(64) NOT NULL DEFAULT '',
        sort_order INT NOT NULL DEFAULT 0,
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_category_sub (category, sub_tab),
        INDEX idx_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]




def now_ms():
    return int(time.time() * 1000)


def format_ms(ts_ms):
    ts_ms = int(ts_ms or 0)
    if ts_ms <= 0:
        return ''
    return datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M')


def format_dt(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M')
    return str(value)


def clone_json_value(value, fallback=None):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except Exception:
        return json.loads(json.dumps(fallback, ensure_ascii=False)) if fallback is not None else None


def sanitize_text(value, default='', max_length=255):
    text = str(value or '').strip()
    if not text:
        text = str(default or '').strip()
    return text[:max_length]


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


@contextmanager

def get_connection(use_database=True, autocommit=True):
    config = {
        'host': DB_HOST,
        'port': DB_PORT,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
        'autocommit': autocommit,
    }
    if use_database:
        config['database'] = DB_NAME
    conn = pymysql.connect(**config)
    try:
        yield conn
    finally:
        conn.close()


def column_exists(conn, table_name, column_name):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT COUNT(*) AS total
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
            ''',
            (DB_NAME, table_name, column_name)
        )
        row = cursor.fetchone() or {}
    return int(row.get('total') or 0) > 0


def ensure_schema_upgrades(conn):
    upgrade_statements = []
    if not column_exists(conn, 'guarantee_orders', 'buyer_beast_nick'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN buyer_beast_nick VARCHAR(64) NOT NULL DEFAULT '' AFTER buyer_beast_id"
        )
    if not column_exists(conn, 'guarantee_orders', 'admin_note'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN admin_note VARCHAR(255) NOT NULL DEFAULT '' AFTER remark"
        )
    if not column_exists(conn, 'guarantee_orders', 'pet_name'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN pet_name VARCHAR(64) NOT NULL DEFAULT '' AFTER seller_beast_id"
        )
    if not column_exists(conn, 'guarantee_orders', 'trade_quantity'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN trade_quantity INT NOT NULL DEFAULT 1 AFTER pet_name"
        )
    if not column_exists(conn, 'guarantee_orders', 'seller_game_id'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN seller_game_id VARCHAR(32) NOT NULL DEFAULT '' AFTER trade_quantity"
        )
    if not column_exists(conn, 'guarantee_orders', 'seller_game_nick'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN seller_game_nick VARCHAR(64) NOT NULL DEFAULT '' AFTER seller_game_id"
        )
    if not column_exists(conn, 'guarantee_orders', 'buyer_trade_note'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN buyer_trade_note VARCHAR(255) NOT NULL DEFAULT '' AFTER buyer_beast_nick"
        )
    if not column_exists(conn, 'guarantee_orders', 'seller_confirmed_at'):
        upgrade_statements.append(
            "ALTER TABLE guarantee_orders ADD COLUMN seller_confirmed_at DATETIME DEFAULT NULL AFTER matched_at"
        )
    if not column_exists(conn, 'users', 'invite_code'):
        upgrade_statements.append(
            "ALTER TABLE users ADD COLUMN invite_code VARCHAR(16) NOT NULL DEFAULT '' AFTER status"
        )
    if not column_exists(conn, 'users', 'invited_by_user_id'):
        upgrade_statements.append(
            "ALTER TABLE users ADD COLUMN invited_by_user_id BIGINT DEFAULT NULL AFTER invite_code"
        )
    if not column_exists(conn, 'users', 'invited_at'):
        upgrade_statements.append(
            "ALTER TABLE users ADD COLUMN invited_at DATETIME DEFAULT NULL AFTER invited_by_user_id"
        )
    if not column_exists(conn, 'users', 'promotion_effective_at'):
        upgrade_statements.append(
            "ALTER TABLE users ADD COLUMN promotion_effective_at DATETIME DEFAULT NULL AFTER invited_at"
        )
    if not column_exists(conn, 'user_wallets', 'commission_pending_x10'):
        upgrade_statements.append(
            "ALTER TABLE user_wallets ADD COLUMN commission_pending_x10 INT NOT NULL DEFAULT 0 COMMENT '待发放佣金×10'"
        )
    with conn.cursor() as cursor:
        for statement in upgrade_statements:
            cursor.execute(statement)


def init_database_and_tables():
    with get_connection(use_database=False) as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_DATABASE_SQL)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
        ensure_schema_upgrades(conn)

    return {
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_NAME,
        'user': DB_USER,
    }


def sanitize_profile(profile=None):
    profile = profile or {}
    user_key = str(profile.get('userKey') or '').strip()
    nick_name = str(profile.get('nickName') or profile.get('nick_name') or '方块兽玩家').strip() or '方块兽玩家'
    avatar_url = str(profile.get('avatarUrl') or profile.get('avatar_url') or '').strip()
    account = str(profile.get('account') or '').strip()
    beast_id = str(profile.get('beastId') or profile.get('beast_id') or '').strip()
    phone = str(profile.get('phone') or '').strip()
    email = str(profile.get('email') or '').strip()
    openid = str(profile.get('openid') or '').strip()
    return {
        'user_key': user_key,
        'nick_name': nick_name[:64],
        'avatar_url': avatar_url[:255],
        'account': account[:64],
        'beast_id': beast_id[:32],
        'phone': phone[:32],
        'email': email[:128],
        'openid': openid[:64],
    }


def get_or_create_user(conn, user_key, profile=None):
    profile_data = sanitize_profile(profile)
    profile_data['user_key'] = str(user_key).strip()
    if not profile_data['user_key']:
        raise ValueError('缺少 user_key')

    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE user_key=%s LIMIT 1', (profile_data['user_key'],))
        user = cursor.fetchone()

        if not user:
            account = profile_data['account'] or f"player_{profile_data['user_key'][-6:]}"
            beast_id = profile_data['beast_id'] or ''

            cursor.execute(
                '''
                INSERT INTO users (user_key, openid, nick_name, avatar_url, account, beast_id, phone, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    profile_data['user_key'],
                    profile_data['openid'] or None,
                    profile_data['nick_name'],
                    profile_data['avatar_url'],
                    account,
                    beast_id,
                    profile_data['phone'],
                    profile_data['email'],
                )
            )
            user_id = cursor.lastrowid
            cursor.execute('INSERT INTO user_wallets (user_id) VALUES (%s)', (user_id,))
            cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (user_id,))
            user = cursor.fetchone()
        else:
            updates = []
            params = []
            field_map = {
                'openid': 'openid',
                'nick_name': 'nick_name',
                'avatar_url': 'avatar_url',
                'account': 'account',
                'beast_id': 'beast_id',
                'phone': 'phone',
                'email': 'email',
            }
            for key, column in field_map.items():
                value = profile_data.get(key)
                if value and value != (user.get(column) or ''):
                    updates.append(f"{column}=%s")
                    params.append(value)
            if updates:
                params.append(user['id'])
                cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=%s", params)
                cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (user['id'],))
                user = cursor.fetchone()

        ensure_user_invite_code(conn, user)
        cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (user['id'],))
        user = cursor.fetchone()
        cursor.execute('SELECT * FROM user_wallets WHERE user_id=%s LIMIT 1', (user['id'],))

        wallet = cursor.fetchone()
        if not wallet:
            cursor.execute('INSERT INTO user_wallets (user_id) VALUES (%s)', (user['id'],))
            cursor.execute('SELECT * FROM user_wallets WHERE user_id=%s LIMIT 1', (user['id'],))
            wallet = cursor.fetchone()

    return user, wallet


def is_placeholder_beast_id(beast_id):
    value = str(beast_id or '').strip()
    return value.startswith('BEAST_')



def normalize_beast_id_value(beast_id):
    value = str(beast_id or '').strip()
    return '' if is_placeholder_beast_id(value) else value



def serialize_user(user_row):
    return {
        'id': int(user_row['id']),
        'nickName': user_row.get('nick_name') or '方块兽玩家',
        'avatarUrl': user_row.get('avatar_url') or '',
        'account': user_row.get('account') or '',
        'beastId': normalize_beast_id_value(user_row.get('beast_id')),
        'phone': user_row.get('phone') or '',
        'email': user_row.get('email') or '',
        'inviteCode': user_row.get('invite_code') or '',
        'invitedByUserId': int(user_row.get('invited_by_user_id') or 0),
        'invitedAt': format_dt(user_row.get('invited_at')),
        'promotionEffectiveAt': format_dt(user_row.get('promotion_effective_at')),
    }




def serialize_wallet(wallet_row):
    return {
        'gemBalance': int(wallet_row.get('gem_balance') or 0),
        'lockedGems': int(wallet_row.get('locked_gems') or 0),
        'totalRecharged': int(wallet_row.get('total_recharged') or 0),
        'totalSpent': int(wallet_row.get('total_spent') or 0),
        'totalEarned': int(wallet_row.get('total_earned') or 0),
    }


def insert_wallet_transaction(conn, user_id, biz_type, change_amount, balance_before, balance_after, ref_type='', ref_id='', remark=''):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO wallet_transactions (user_id, biz_type, change_amount, balance_before, balance_after, ref_type, ref_id, remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (user_id, biz_type, int(change_amount), int(balance_before), int(balance_after), ref_type, ref_id, remark[:255])
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



def get_feedback_meta(status):
    return FEEDBACK_STATUS_META.get(status or FEEDBACK_STATUS_PENDING, FEEDBACK_STATUS_META[FEEDBACK_STATUS_PENDING])



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



def count_today_feedbacks(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT COUNT(*) AS total
            FROM user_feedback
            WHERE user_id=%s AND DATE(created_at)=CURDATE()
            ''',
            (user_id,)
        )
        row = cursor.fetchone() or {}
    return int(row.get('total') or 0)



def list_feedback_entries(conn, limit=20, user_id=None, status=None):
    limit = max(1, min(100, int(limit)))
    conditions = []
    params = []
    if user_id:
        conditions.append('f.user_id=%s')
        params.append(int(user_id))
    if status:
        conditions.append('f.status=%s')
        params.append(str(status))
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



def create_feedback(conn, user_row, feedback_type, title, content, contact=''):
    feedback_type = str(feedback_type or '其他').strip()[:32] or '其他'
    title = str(title or '').strip()[:120]
    content = str(content or '').strip()[:500]
    contact = str(contact or '').strip()[:64]

    if len(title) < 2:
        raise ValueError('请填写反馈标题')
    if len(content) < 5:
        raise ValueError('请尽量详细描述问题，至少 5 个字')

    today_count = count_today_feedbacks(conn, user_row['id'])
    if today_count >= DEFAULT_FEEDBACK_DAILY_LIMIT:
        raise ValueError(f'每天最多提交 {DEFAULT_FEEDBACK_DAILY_LIMIT} 次反馈，请明天再试')

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO user_feedback (user_id, feedback_type, title, content, contact, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (
                user_row['id'],
                feedback_type,
                title,
                content,
                contact,
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



def build_feedback_payload(conn, user_row, limit=20, mine_only=False):
    today_count = count_today_feedbacks(conn, user_row['id'])
    rows = list_feedback_entries(conn, limit=limit, user_id=user_row['id'] if mine_only else None)
    return {
        'user': serialize_user(user_row),
        'feedback': {
            'dailyLimit': DEFAULT_FEEDBACK_DAILY_LIMIT,
            'todayCount': today_count,
            'remainingCount': max(0, DEFAULT_FEEDBACK_DAILY_LIMIT - today_count),
            'mineOnly': bool(mine_only),
            'list': [serialize_feedback_row(row, viewer_user_id=user_row['id']) for row in rows],
        }
    }



def get_transfer_request_meta(status):

    return TRANSFER_REQUEST_STATUS_META.get(status or TRANSFER_REQUEST_STATUS_PENDING, TRANSFER_REQUEST_STATUS_META[TRANSFER_REQUEST_STATUS_PENDING])



def calculate_transfer_out_fee(amount):
    amount = max(0, int(amount or 0))
    return max(0, amount * DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS // 10000)



def calculate_guarantee_seller_total_cost(gem_amount, fee_amount=DEFAULT_GUARANTEE_FEE):
    gem_amount = max(0, int(gem_amount or 0))
    fee_amount = max(0, int(fee_amount or 0))
    return gem_amount + fee_amount



def calculate_guarantee_actual_receive(gem_amount, fee_amount=DEFAULT_GUARANTEE_FEE):
    gem_amount = max(0, int(gem_amount or 0))
    fee_amount = max(0, int(fee_amount or 0))
    return max(gem_amount - fee_amount, 0)



def calculate_guarantee_total_fee(fee_amount=DEFAULT_GUARANTEE_FEE):
    fee_amount = max(0, int(fee_amount or 0))
    return fee_amount * 2



def serialize_transfer_request(row):

    if not row:
        return None
    meta = get_transfer_request_meta(row.get('status'))
    request_amount = int(row.get('request_amount') or 0)
    fee_amount = int(row.get('fee_amount') or 0)
    actual_amount = int(row.get('actual_amount') or max(request_amount - fee_amount, 0))
    return {
        'id': row.get('id') or '',
        'requestAmount': request_amount,
        'request_amount': request_amount,
        'feeAmount': fee_amount,
        'fee_amount': fee_amount,
        'actualAmount': actual_amount,
        'actual_amount': actual_amount,
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



def get_guarantee_meta(status):

    return GUARANTEE_STATUS_META.get(status or GUARANTEE_STATUS_PENDING, GUARANTEE_STATUS_META[GUARANTEE_STATUS_PENDING])


def serialize_guarantee_row(row):
    if not row:
        return None
    raw_status = row.get('status') or GUARANTEE_STATUS_PENDING
    meta = get_guarantee_meta(raw_status)
    gem_amount = int(row.get('gem_amount') or 0)
    fee_amount = int(row.get('fee_amount') or 0)
    seller_total_cost = calculate_guarantee_seller_total_cost(gem_amount, fee_amount)
    actual_receive = calculate_guarantee_actual_receive(gem_amount, fee_amount)
    total_fee_amount = calculate_guarantee_total_fee(fee_amount)
    seller_confirmed = bool(row.get('seller_confirmed_at'))

    status_text = meta['text']
    status_short_text = meta['short_text']
    status_desc = meta['desc']
    if raw_status == GUARANTEE_STATUS_MATCHED and seller_confirmed:
        status_text = '自动到账中'
        status_short_text = '到账中'
        status_desc = f'卖家已确认交易完成，系统正在给买家发放宝石（到账后实收 {actual_receive}）'
    elif raw_status == GUARANTEE_STATUS_DONE:
        status_desc = f'系统已按双边手续费规则完成结算，买家最终实收 {actual_receive} 宝石'


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
        'feeAmount': fee_amount,
        'fee_amount': fee_amount,
        'sellerFeeAmount': fee_amount,
        'seller_fee_amount': fee_amount,
        'buyerFeeAmount': fee_amount,
        'buyer_fee_amount': fee_amount,
        'totalFeeAmount': total_fee_amount,
        'total_fee_amount': total_fee_amount,
        'sellerTotalCost': seller_total_cost,
        'seller_total_cost': seller_total_cost,
        'actualReceive': actual_receive,
        'actual_receive': actual_receive,

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
        'autoConfirmTime': format_dt(row.get('auto_confirm_at')),

        'auto_confirm_time': format_dt(row.get('auto_confirm_at')),
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


def build_user_stats(conn, user_id):
    with conn.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) AS total FROM guarantee_orders WHERE seller_user_id=%s', (user_id,))
        guarantee_total = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute("SELECT COUNT(*) AS total FROM guarantee_orders WHERE seller_user_id=%s AND status=%s", (user_id, GUARANTEE_STATUS_DONE))
        guarantee_done = int((cursor.fetchone() or {}).get('total') or 0)
        cursor.execute("SELECT COALESCE(SUM(change_amount), 0) AS total FROM wallet_transactions WHERE user_id=%s AND change_amount > 0 AND biz_type <> 'recharge'", (user_id,))
        earned_gem = int((cursor.fetchone() or {}).get('total') or 0)
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
    balance_before = int(wallet.get('gem_balance') or 0)
    amount = int(order_row.get('amount') or 0)
    balance_after = balance_before + amount
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
                cursor.execute('SELECT gem_balance FROM user_wallets WHERE user_id=%s LIMIT 1', (user_row['id'],))
                wallet_row = cursor.fetchone() or {}
                return int(wallet_row.get('gem_balance') or balance_after)
            raise ValueError('订单状态已变化，请刷新后重试')

        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s, total_recharged=total_recharged+%s, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (balance_after, amount, user_row['id'])
        )

    insert_wallet_transaction(
        conn,
        user_row['id'],
        'recharge',
        amount,
        balance_before,
        balance_after,
        'recharge_order',
        order_row['id'],
        f"充值到账 #{order_row['id']}"
    )
    activate_promotion_for_user(conn, user_row['id'])
    return balance_after



def generate_order_no(prefix, user_id=None):
    user_part = str(user_id or 0)[-2:].zfill(2)
    time_part = str(now_ms())[-10:]
    return f"{prefix}{user_part}{time_part}"



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
    balance_before = int(wallet.get('gem_balance') or 0)
    locked_before = int(wallet.get('locked_gems') or 0)
    if balance_before < request_amount:
        raise ValueError(f'宝石余额不足，当前仅有 {balance_before} 宝石')

    fee_amount = calculate_transfer_out_fee(request_amount)
    actual_amount = max(request_amount - fee_amount, 0)
    request_id = generate_order_no('TX', user_row['id'])
    balance_after = balance_before - request_amount
    locked_after = locked_before + request_amount

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO gem_transfer_requests (
                id, user_id, beast_id, beast_nick, request_amount, fee_amount, actual_amount,
                fee_basis_points, status, user_note
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (
                request_id,
                user_row['id'],
                beast_id,
                (user_row.get('nick_name') or '方块兽玩家')[:64],
                request_amount,
                fee_amount,
                actual_amount,
                DEFAULT_TRANSFER_OUT_FEE_BASIS_POINTS,
                TRANSFER_REQUEST_STATUS_PENDING,
                str(user_note or '').strip()[:255],
            )
        )
        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s, locked_gems=%s, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (balance_after, locked_after, user_row['id'])
        )

    insert_wallet_transaction(
        conn,
        user_row['id'],
        'transfer_out_lock',
        -request_amount,
        balance_before,
        balance_after,
        'transfer_request',
        request_id,
        f"提交转出申请 #{request_id}"
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
    wallet = lock_wallet(conn, user_id)
    locked_before = int(wallet.get('locked_gems') or 0)
    if locked_before < request_amount:
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
            SET locked_gems=locked_gems-%s,
                total_spent=total_spent+%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (request_amount, request_amount, user_id)
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
    wallet = lock_wallet(conn, user_id)
    balance_before = int(wallet.get('gem_balance') or 0)
    locked_before = int(wallet.get('locked_gems') or 0)
    if locked_before < request_amount:
        raise ValueError('锁定宝石不足，无法拒绝转出，请检查数据')
    balance_after = balance_before + request_amount

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
                locked_gems=locked_gems-%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (balance_after, request_amount, user_id)
        )

    insert_wallet_transaction(
        conn,
        user_id,
        'transfer_out_unlock',
        request_amount,
        balance_before,
        balance_after,
        'transfer_request',
        request_id,
        f"后台已拒绝转出申请 #{request_id}，解锁 {request_amount} 宝石"
    )
    return find_transfer_request(conn, request_id)




def apply_guarantee_auto_confirm(conn, order_no=None):
    conditions = [
        'status=%s',
        'seller_confirmed_at IS NULL',
        'matched_at IS NOT NULL',
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
        complete_guarantee_transfer(conn, target_order_no)

        settled_count += 1
    return settled_count



def find_guarantee_order(conn, order_no):
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
):
    gem_amount = int(gem_amount or 0)
    fee_amount = int(fee_amount or 0)
    trade_quantity = max(1, int(trade_quantity or 1))
    pet_name = str(pet_name or '').strip()[:64]
    seller_game_id = str(seller_game_id or '').strip()[:32]
    seller_game_nick = str(seller_game_nick or '').strip()[:64]
    remark = str(remark or '').strip()[:255]

    if not pet_name:
        raise ValueError('请选择兽王类型')
    if gem_amount <= 0:
        raise ValueError('请输入正确的担保宝石数量')
    if fee_amount < 0:
        raise ValueError('手续费不能小于 0')
    if not seller_game_id:
        raise ValueError('请填写地球猎人ID号')
    if not seller_game_nick:
        raise ValueError('请填写地球猎人昵称')

    wallet = lock_wallet(conn, user_row['id'])
    balance_before = int(wallet.get('gem_balance') or 0)
    locked_before = int(wallet.get('locked_gems') or 0)
    total_cost = calculate_guarantee_seller_total_cost(gem_amount, fee_amount)
    if balance_before < total_cost:
        raise ValueError(f'余额不足，当前仅有 {balance_before} 宝石，需要至少 {total_cost} 宝石')


    order_no = generate_order_no('GUA', user_row['id'])
    balance_after = balance_before - total_cost
    locked_after = locked_before + total_cost
    seller_beast_id = normalize_beast_id_value(user_row.get('beast_id'))

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO guarantee_orders (
                order_no, seller_user_id, seller_beast_id, pet_name, trade_quantity,
                seller_game_id, seller_game_nick, gem_amount, fee_amount, remark, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                fee_amount,
                remark,
                GUARANTEE_STATUS_PENDING,
            )
        )
        cursor.execute(
            '''
            UPDATE user_wallets
            SET gem_balance=%s, locked_gems=%s, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (balance_after, locked_after, user_row['id'])
        )

    insert_wallet_transaction(
        conn,
        user_row['id'],
        'guarantee_lock',
        -total_cost,
        balance_before,
        balance_after,
        'guarantee_order',
        order_no,
        f"担保锁定 #{order_no}（卖家实扣 {total_cost}，含手续费 {fee_amount}）"
    )

    return find_guarantee_order(conn, order_no)



def match_guarantee_order(conn, order_no, buyer_user_row, buyer_beast_id, buyer_beast_nick, buyer_trade_note='', buyer_proof_image=''):

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

    if current_status == GUARANTEE_STATUS_MATCHED:
        existing_buyer_id = int(order_row.get('buyer_user_id') or 0)
        if existing_buyer_id and existing_buyer_id != int(buyer_user_row.get('id') or 0):
            raise ValueError('该担保单已被其他买家匹配')
        return find_guarantee_order(conn, order_no)

    buyer_beast_id = str(buyer_beast_id or buyer_user_row.get('beast_id') or '').strip()[:32]
    buyer_beast_nick = str(buyer_beast_nick or buyer_user_row.get('nick_name') or '').strip()[:64]
    buyer_trade_note = str(buyer_trade_note or '').strip()[:255]
    buyer_proof_image = str(buyer_proof_image or '').strip()[:255]
    if not buyer_beast_id:
        raise ValueError('请填写买家方块兽ID')
    if not buyer_beast_nick:
        raise ValueError('请填写买家昵称')
    if not buyer_proof_image:
        raise ValueError('请上传交易截图，方便卖家核对')

    with conn.cursor() as cursor:
        cursor.execute(
            '''
            UPDATE guarantee_orders
            SET buyer_user_id=%s,
                buyer_beast_id=%s,
                buyer_beast_nick=%s,
                buyer_trade_note=%s,
                buyer_proof_image=%s,
                buyer_proof_uploaded_at=CURRENT_TIMESTAMP,
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
        raise ValueError('未找到担保单')

    current_status = order_row.get('status') or GUARANTEE_STATUS_PENDING
    if current_status == GUARANTEE_STATUS_DONE:
        return find_guarantee_order(conn, order_no)
    if current_status != GUARANTEE_STATUS_MATCHED:
        raise ValueError('当前担保单还未进入可完成状态')
    if not order_row.get('seller_confirmed_at'):
        raise ValueError('卖家还未确认交易完成，系统暂不可结算')

    seller_user_id = int(order_row.get('seller_user_id') or 0)
    buyer_user_id = int(order_row.get('buyer_user_id') or 0)
    if buyer_user_id <= 0:
        raise ValueError('当前担保单还没有买家，无法完成结算')

    gem_amount = int(order_row.get('gem_amount') or 0)
    fee_amount = int(order_row.get('fee_amount') or 0)
    total_cost = calculate_guarantee_seller_total_cost(gem_amount, fee_amount)
    actual_receive = calculate_guarantee_actual_receive(gem_amount, fee_amount)

    wallet_ids = [seller_user_id] if seller_user_id == buyer_user_id else sorted({seller_user_id, buyer_user_id})

    wallet_map = {}
    for uid in wallet_ids:
        wallet_map[uid] = lock_wallet(conn, uid)

    seller_wallet = wallet_map[seller_user_id]
    buyer_wallet = wallet_map[buyer_user_id]
    locked_before = int(seller_wallet.get('locked_gems') or 0)
    if locked_before < total_cost:
        raise ValueError('锁定宝石不足，无法完成结算，请检查订单数据')

    buyer_balance_before = int(buyer_wallet.get('gem_balance') or 0)
    buyer_balance_after = buyer_balance_before + actual_receive
    final_admin_note = str(admin_note or f'系统已自动给买家发放 {actual_receive} 宝石（买家手续费 {fee_amount}）').strip()[:255]


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
            raise ValueError('担保结算失败，请刷新后重试')
        cursor.execute(
            '''
            UPDATE user_wallets
            SET locked_gems=locked_gems-%s,
                total_spent=total_spent+%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
            ''',
            (total_cost, total_cost, seller_user_id)
        )
        if actual_receive > 0:
            cursor.execute(
                '''
                UPDATE user_wallets
                SET gem_balance=%s,
                    total_earned=total_earned+%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s
                ''',
                (buyer_balance_after, actual_receive, buyer_user_id)
            )


    if actual_receive > 0:
        insert_wallet_transaction(
            conn,
            buyer_user_id,
            'guarantee_receive',
            actual_receive,
            buyer_balance_before,
            buyer_balance_after,
            'guarantee_order',
            order_no,
            f"担保到账 #{order_no}（到账 {actual_receive}，已扣手续费 {fee_amount}）"
        )

    try:
        grant_order_commission(conn, order_row)
    except Exception:
        pass

    return find_guarantee_order(conn, order_no)




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



def serialize_manage_feedback_row(row):
    payload = serialize_feedback_row(row, viewer_user_id=row.get('user_id')) or {}
    payload.update({
        'contact': row.get('contact') or '',
        'account': row.get('user_account') or '',
        'beastId': normalize_beast_id_value(row.get('user_beast_id')),
    })
    return payload



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
    """担保单完成后触发：给卖家的邀请人（L1）发 0.8 宝石，给 L1 的邀请人（L2）发 0.2 宝石。
    若受益人本次是被邀请来的首单，额外给 L1 发 2 宝石首单奖励。"""
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
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE user_wallets SET commission_pending_x10=commission_pending_x10+%s WHERE user_id=%s',
                (amount_x10, recipient_id)
            )
        flushed = _flush_commission_pending(conn, recipient_id)
        if flushed > 0:
            with conn.cursor() as cursor:
                cursor.execute(
                    'UPDATE promotion_commission_logs SET flushed_amount=%s WHERE user_id=%s AND order_no=%s AND reward_type=%s',
                    (flushed, recipient_id, order_no, rtype)
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
    reward_amount = int(row.get('total_reward_amount') or 0)
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
        'rewardAmount': int(row.get('reward_amount') or 0),
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
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE id=%s LIMIT 1', (user_id,))
        latest_user = cursor.fetchone() or user_row
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
                   COALESCE(SUM(reward_amount), 0) AS reward_amount
            FROM promotion_reward_logs
            WHERE user_id=%s
            """,
            (user_id,)
        )
        reward_row = cursor.fetchone() or {}
        cursor.execute(
            f'''
            SELECT r.*, invitee.nick_name AS invitee_nick_name, invitee.beast_id AS invitee_beast_id
            FROM promotion_reward_logs r
            LEFT JOIN users invitee ON invitee.id = r.invitee_user_id
            WHERE r.user_id=%s
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT {max(1, min(100, int(limit or 20)))}
            ''',
            (user_id,)
        )
        reward_rows = cursor.fetchall() or []

    invited_count = int(invited_row.get('invited_count') or 0)
    effective_invited_count = int(invited_row.get('effective_invited_count') or 0)
    reward_amount = int(reward_row.get('reward_amount') or 0)
    reward_count = int(reward_row.get('reward_count') or 0)
    rules = [
        {'label': '一级分佣（直接邀请）', 'rewardDesc': '每单 +0.8 宝石'},
        {'label': '二级分佣（间接邀请）', 'rewardDesc': '每单 +0.2 宝石'},
        {'label': '新人首单奖励',         'rewardDesc': f'邀请人完成首单 +{PROMO_FIRST_ORDER_BONUS} 宝石'},
        {'label': '月度阶梯（≥30单）',   'rewardDesc': '每单额外 +0.2 宝石，月末结算'},
        {'label': '月度阶梯（≥100单）',  'rewardDesc': '每单额外 +0.3 宝石，月末结算'},
        {'label': '全月 Top5',            'rewardDesc': '50/30/20/10/5 宝石，月末结算'},
    ]
    return {
        'user': serialize_user(latest_user),
        'promotion': {
            'inviteCode': latest_user.get('invite_code') or '',
            'sharePath': f"/pages/index/index?ref={latest_user.get('invite_code') or ''}",
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
                   COALESCE(SUM(reward_amount), 0) AS total_reward_amount,
                   MAX(created_at) AS latest_reward_at
            FROM promotion_reward_logs
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
               COALESCE(reward.total_reward_amount, 0) AS total_reward_amount,
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
                   COALESCE(SUM(reward_amount), 0) AS total_reward_amount,
                   MAX(created_at) AS latest_reward_at
            FROM promotion_reward_logs
            GROUP BY user_id
        ) reward ON reward.user_id = u.id
        {where_sql}
        ORDER BY COALESCE(inv.effective_invited_count, 0) DESC,
                 COALESCE(reward.total_reward_amount, 0) DESC,
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
            FROM promotion_reward_logs r
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
            'totalRewardAmount': int(reward_summary.get('reward_amount') or 0),
            'recentEffectiveCount': int(recent_summary.get('recent_effective_count') or 0),
            'conversionRate': round((effective_total * 100 / invitee_total), 1) if invitee_total else 0,
        },
        'rules': [
            {'label': '一级分佣（直接邀请）', 'rewardDesc': '每单 +0.8 宝石'},
            {'label': '二级分佣（间接邀请）', 'rewardDesc': '每单 +0.2 宝石'},
            {'label': '新人首单奖励',         'rewardDesc': f'邀请人完成首单 +{PROMO_FIRST_ORDER_BONUS} 宝石'},
            {'label': '月度阶梯（≥30单）',   'rewardDesc': '每单额外 +0.2 宝石，月末结算'},
            {'label': '月度阶梯（≥100单）',  'rewardDesc': '每单额外 +0.3 宝石，月末结算'},
            {'label': '全月 Top5',            'rewardDesc': '50/30/20/10/5 宝石，月末结算'},
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



def build_manage_feedback_payload(conn, query='', status='all', page=1, page_size=20, pending_only=False):
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 20)))
    offset = (page - 1) * page_size
    keyword = str(query or '').strip()
    normalized_status = str(status or 'all').strip() or 'all'

    conditions = []
    params = []
    if pending_only:
        conditions.append('f.status=%s')
        params.append(FEEDBACK_STATUS_PENDING)
    elif normalized_status not in ('', 'all'):
        conditions.append('f.status=%s')
        params.append(normalized_status)
    if keyword:
        like_text = f"%{keyword}%"
        conditions.append(
            "(CAST(f.id AS CHAR) LIKE %s OR f.title LIKE %s OR f.content LIKE %s OR f.type LIKE %s OR u.nick_name LIKE %s OR u.account LIKE %s OR u.beast_id LIKE %s OR f.contact LIKE %s OR f.admin_reply LIKE %s)"
        )
        params.extend([like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text, like_text])

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



def build_manage_dashboard(conn, days=7, limit=20):


    days = max(3, min(30, int(days)))
    limit = max(0, min(100, int(limit)))

    oldest_date = (datetime.now() - timedelta(days=days - 1)).date()
    oldest_text = oldest_date.strftime('%Y-%m-%d')

    apply_guarantee_auto_confirm(conn)
    settle_confirmed_guarantee_orders(conn)

    with conn.cursor() as cursor:


        cursor.execute('SELECT COUNT(*) AS total FROM users')
        user_count = int((cursor.fetchone() or {}).get('total') or 0)

        cursor.execute('SELECT COALESCE(SUM(gem_balance), 0) AS total_balance, COALESCE(SUM(locked_gems), 0) AS total_locked FROM user_wallets')
        wallet_summary = cursor.fetchone() or {}

        cursor.execute("SELECT COALESCE(SUM(flushed_amount), 0) AS total FROM promotion_commission_logs")
        promo_reward_summary = cursor.fetchone() or {}

        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total_recharged FROM recharge_orders WHERE status='success'")
        plat_recharge = cursor.fetchone() or {}
        cursor.execute("SELECT COALESCE(SUM(actual_amount), 0) AS total_transferred FROM gem_transfer_requests WHERE status=%s", (TRANSFER_REQUEST_STATUS_DONE,))
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
                   COALESCE(SUM(fee_amount * 2), 0) AS total_fee_amount
            FROM guarantee_orders
            WHERE status=%s
            """,
            (GUARANTEE_STATUS_DONE,)
        )

        guarantee_fee_summary = cursor.fetchone() or {}


        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(fee_amount), 0) AS total_fee_amount
            FROM gem_transfer_requests
            WHERE status=%s
            """,
            (TRANSFER_REQUEST_STATUS_DONE,)
        )
        transfer_fee_summary = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count, COALESCE(SUM(amount), 0) AS total_amount
            FROM recharge_orders
            WHERE status='success' AND DATE(FROM_UNIXTIME(verified_at_ms / 1000)) = CURDATE()
            """
        )

        today_recharge = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(GREATEST(gem_amount - fee_amount, 0)), 0) AS total_amount,
                   COALESCE(SUM(fee_amount * 2), 0) AS total_fee_amount
            FROM guarantee_orders
            WHERE status=%s AND DATE(finished_at) = CURDATE()

            """,
            (GUARANTEE_STATUS_DONE,)
        )

        today_guarantee_transfer = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(actual_amount), 0) AS total_amount
            FROM gem_transfer_requests
            WHERE status=%s AND DATE(processed_at) = CURDATE()
            """,
            (TRANSFER_REQUEST_STATUS_DONE,)
        )
        today_user_transfer = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS total_count
            FROM user_feedback
            WHERE DATE(created_at)=CURDATE()
            """
        )
        today_feedback = cursor.fetchone() or {}

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
            "SELECT COUNT(*) AS total_count FROM user_feedback WHERE status=%s",
            (FEEDBACK_STATUS_PENDING,)
        )
        pending_feedback = cursor.fetchone() or {}

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
            WHERE status='success' AND verified_at_ms > 0 AND DATE(FROM_UNIXTIME(verified_at_ms / 1000)) >= %s
            GROUP BY DATE(FROM_UNIXTIME(verified_at_ms / 1000))
            ''',
            (oldest_text,)
        )
        recharge_daily_rows = cursor.fetchall() or []

        cursor.execute(
            '''
            SELECT DATE(created_at) AS stat_date,
                   COUNT(*) AS created_count
            FROM guarantee_orders
            WHERE DATE(created_at) >= %s
            GROUP BY DATE(created_at)
            ''',
            (oldest_text,)
        )
        guarantee_created_rows = cursor.fetchall() or []

        cursor.execute(
            '''
            SELECT DATE(created_at) AS stat_date,
                   COUNT(*) AS feedback_count
            FROM user_feedback
            WHERE DATE(created_at) >= %s
            GROUP BY DATE(created_at)
            ''',
            (oldest_text,)
        )
        feedback_created_rows = cursor.fetchall() or []

        cursor.execute(
            '''
            SELECT DATE(finished_at) AS stat_date,
                   COUNT(*) AS transfer_count,
                   COALESCE(SUM(GREATEST(gem_amount - fee_amount, 0)), 0) AS transfer_amount,
                   COALESCE(SUM(fee_amount * 2), 0) AS fee_amount
            FROM guarantee_orders
            WHERE status=%s AND finished_at IS NOT NULL AND DATE(finished_at) >= %s
            GROUP BY DATE(finished_at)
            ''',
            (GUARANTEE_STATUS_DONE, oldest_text)
        )

        guarantee_done_rows = cursor.fetchall() or []

        cursor.execute(
            '''
            SELECT DATE(processed_at) AS stat_date,
                   COUNT(*) AS transfer_count,
                   COALESCE(SUM(actual_amount), 0) AS transfer_amount,
                   COALESCE(SUM(fee_amount), 0) AS fee_amount
            FROM gem_transfer_requests
            WHERE status=%s AND processed_at IS NOT NULL AND DATE(processed_at) >= %s
            GROUP BY DATE(processed_at)
            ''',
            (TRANSFER_REQUEST_STATUS_DONE, oldest_text)
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
            daily_map[key]['transferAmount'] += int(row.get('transfer_amount') or 0)
            daily_map[key]['guaranteeFeeAmount'] += int(row.get('fee_amount') or 0)
            daily_map[key]['platformFeeAmount'] += int(row.get('fee_amount') or 0)

    for row in transfer_request_done_rows:
        key = str(row.get('stat_date'))
        if key in daily_map:
            daily_map[key]['transferCount'] += int(row.get('transfer_count') or 0)
            daily_map[key]['transferAmount'] += int(row.get('transfer_amount') or 0)
            daily_map[key]['withdrawFeeAmount'] += int(row.get('fee_amount') or 0)
            daily_map[key]['platformFeeAmount'] += int(row.get('fee_amount') or 0)


    pending_transfer_count = int(pending_transfer.get('total_count') or 0)
    pending_withdraw_count = int(pending_withdraw.get('total_count') or 0)
    pending_feedback_count = int(pending_feedback.get('total_count') or 0)


    return {
        'totals': {
            'userCount': user_count,
            'walletBalance': int(wallet_summary.get('total_balance') or 0),
            'lockedGems': int(wallet_summary.get('total_locked') or 0),
            'totalRechargeCount': int(recharge_summary.get('total_count') or 0),
            'totalRechargeAmount': int(recharge_summary.get('total_amount') or 0),
            'rechargeRecordCount': int(recharge_record_summary.get('total_count') or 0),
            'completedGuaranteeCount': int(guarantee_done.get('total_count') or 0),
            'guaranteeRecordCount': int(guarantee_record_summary.get('total_count') or 0),
            'totalFeedbackCount': int(feedback_summary.get('total_count') or 0),
            'feedbackRecordCount': int(feedback_summary.get('total_count') or 0),
            'totalGuaranteeFeeAmount': int(guarantee_fee_summary.get('total_fee_amount') or 0),
            'totalWithdrawFeeAmount': int(transfer_fee_summary.get('total_fee_amount') or 0),
            'totalPlatformFeeAmount': int(guarantee_fee_summary.get('total_fee_amount') or 0) + int(transfer_fee_summary.get('total_fee_amount') or 0),
            'pendingTransferCount': pending_transfer_count,
            'pendingWithdrawCount': pending_withdraw_count,
            'pendingFeedbackCount': pending_feedback_count,
            'pendingActionCount': pending_transfer_count + pending_withdraw_count + pending_feedback_count,
            'totalPromotionReward': int(promo_reward_summary.get('total') or 0),
            'platformAccountBalance': max(0, int(plat_recharge.get('total_recharged') or 0) - int(plat_transfer.get('total_transferred') or 0)),
            'allUsersWalletBalance': int(wallet_summary.get('total_balance') or 0),
        },

        'today': {
            'rechargeCount': int(today_recharge.get('total_count') or 0),
            'rechargeAmount': int(today_recharge.get('total_amount') or 0),
            'transferCount': int(today_guarantee_transfer.get('total_count') or 0) + int(today_user_transfer.get('total_count') or 0),
            'transferAmount': int(today_guarantee_transfer.get('total_amount') or 0) + int(today_user_transfer.get('total_amount') or 0),
            'guaranteeFeeAmount': int(today_guarantee_transfer.get('total_fee_amount') or 0),
            'withdrawFeeAmount': int(today_user_transfer.get('total_fee_amount') or 0),
            'platformFeeAmount': int(today_guarantee_transfer.get('total_fee_amount') or 0) + int(today_user_transfer.get('total_fee_amount') or 0),
            'feedbackCount': int(today_feedback.get('total_count') or 0),
        },

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


def build_game_config_payload(conn, env_user_id='', env_token='', env_token_type='fks'):
    """读取游戏凭证配置，DB 优先，无则降级到环境变量。"""
    stored, row = load_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, default={})
    user_id = str(stored.get('userId') or env_user_id or '').strip()
    token = str(stored.get('token') or env_token or '').strip()
    token_type = str(stored.get('tokenType') or env_token_type or 'fks').strip().lower()
    if token_type not in ('fks', 'cw'):
        token_type = 'fks'
    exp_ts = _parse_jwt_exp(token)
    now_ts = int(time.time())
    days_left = max(0, round((exp_ts - now_ts) / 86400, 1)) if exp_ts else None
    is_expired = bool(exp_ts and exp_ts <= now_ts)
    return {
        'userId': user_id,
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


def save_game_config(conn, user_id, token, token_type='fks'):
    """保存游戏凭证到 DB，立即对后续请求生效（无需重启）。"""
    user_id = str(user_id or '').strip()
    token = str(token or '').strip()
    token_type = str(token_type or 'fks').strip().lower()
    if token_type not in ('fks', 'cw'):
        token_type = 'fks'
    if not user_id:
        raise ValueError('userId 不能为空')
    if not token:
        raise ValueError('Token 不能为空')
    save_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, {
        'userId': user_id,
        'token': token,
        'tokenType': token_type,
    })
    return build_game_config_payload(conn, env_user_id=user_id, env_token=token, env_token_type=token_type)


def get_live_game_credentials(conn, env_user_id='', env_token=''):
    """获取当前生效的游戏凭证（DB 优先 → 环境变量）。每次调用都从 DB 读，热更新无需重启。"""
    stored, _ = load_app_config_json(conn, GAME_CREDENTIALS_CONFIG_KEY, default={})
    user_id = str(stored.get('userId') or env_user_id or '').strip()
    token = str(stored.get('token') or env_token or '').strip()
    token_type = str(stored.get('tokenType') or 'fks').strip().lower()
    return user_id, token, token_type


# ── 社区名流 CRUD ────────────────────────────────────────────────

def _serialize_profile(row):
    if not row:
        return None
    r = dict(row)
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
    cols = ', '.join(fields)
    placeholders = ', '.join(['%s'] * len(fields))
    sql = f'INSERT INTO community_profiles ({cols}) VALUES ({placeholders})'
    with conn.cursor() as cur:
        cur.execute(sql, [values[f] for f in fields])
    conn.commit()
    return get_community_profile(conn, conn.insert_id())


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
