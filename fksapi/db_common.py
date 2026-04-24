from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor

from env_bootstrap import load_local_env

load_local_env()

DB_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
DB_USER = os.environ.get("MYSQL_USER", "fks_user")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
DB_NAME = os.environ.get("MYSQL_DATABASE", "fks_trade")

DEFAULT_GEM_BALANCE = 256
GEM_SCALE = 10

try:
    from dbutils.pooled_db import PooledDB as _PooledDB

    _DB_POOL = _PooledDB(
        creator=pymysql,
        mincached=2,
        maxcached=8,
        maxconnections=20,
        blocking=True,
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
    )
    _DB_POOL_NO_DB = _PooledDB(
        creator=pymysql,
        mincached=1,
        maxcached=2,
        maxconnections=5,
        blocking=True,
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
    )
    _POOL_AVAILABLE = True
except Exception:
    _DB_POOL = None
    _DB_POOL_NO_DB = None
    _POOL_AVAILABLE = False


def now_ms():
    return int(time.time() * 1000)


def format_ms(ts_ms):
    if not ts_ms:
        return ""
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def format_dt(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def clone_json_value(value, fallback=None):
    try:
        return json.loads(json.dumps(value if value is not None else fallback, ensure_ascii=False))
    except Exception:
        return fallback


def to_x10_amount(value):
    return int(round(float(value or 0) * GEM_SCALE))


def x10_to_amount(value_x10):
    value_x10 = int(value_x10 or 0)
    if value_x10 % GEM_SCALE == 0:
        return value_x10 // GEM_SCALE
    return round(value_x10 / GEM_SCALE, 1)


def get_row_amount_x10(row, field_name):
    row = row or {}
    x10_key = f"{field_name}_x10"
    if x10_key in row and row.get(x10_key) is not None:
        return int(row.get(x10_key) or 0)
    return to_x10_amount(row.get(field_name) or 0)


def sync_legacy_int_amount(amount_x10):
    amount_x10 = int(amount_x10 or 0)
    if amount_x10 < 0:
        return -((-amount_x10) // GEM_SCALE)
    return amount_x10 // GEM_SCALE


@contextmanager
def get_connection(use_database=True, autocommit=True):
    if _POOL_AVAILABLE and autocommit:
        pool = _DB_POOL if use_database else _DB_POOL_NO_DB
        conn = pool.connection()
        try:
            yield conn
        finally:
            conn.close()
    else:
        config = {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "password": DB_PASSWORD,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": autocommit,
            "connect_timeout": 10,
        }
        if use_database:
            config["database"] = DB_NAME
        conn = pymysql.connect(**config)
        try:
            yield conn
        finally:
            conn.close()


def column_exists(conn, table_name, column_name):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
            """,
            (DB_NAME, table_name, column_name),
        )
        row = cursor.fetchone() or {}
    return int(row.get("total") or 0) > 0


def ensure_schema_upgrades(conn):
    from db_mysql import ensure_schema_upgrades as _legacy_ensure_schema_upgrades

    return _legacy_ensure_schema_upgrades(conn)


def init_database_and_tables():
    from db_mysql import CREATE_DATABASE_SQL, SCHEMA_STATEMENTS

    with get_connection(use_database=False) as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_DATABASE_SQL)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
        ensure_schema_upgrades(conn)

    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
        "user": DB_USER,
    }


def sanitize_profile(profile=None):
    profile = profile or {}
    user_key = str(profile.get("userKey") or "").strip()
    nick_name = str(profile.get("nickName") or profile.get("nick_name") or "方块兽玩家").strip() or "方块兽玩家"
    avatar_url = str(profile.get("avatarUrl") or profile.get("avatar_url") or "").strip()
    account = str(profile.get("account") or "").strip()
    beast_id = str(profile.get("beastId") or profile.get("beast_id") or "").strip()
    phone = str(profile.get("phone") or "").strip()
    email = str(profile.get("email") or "").strip()
    openid = str(profile.get("openid") or "").strip()
    return {
        "user_key": user_key,
        "nick_name": nick_name[:64],
        "avatar_url": avatar_url[:255],
        "account": account[:64],
        "beast_id": beast_id[:32],
        "phone": phone[:32],
        "email": email[:128],
        "openid": openid[:64],
    }


def is_placeholder_beast_id(beast_id):
    value = str(beast_id or "").strip()
    return value.startswith("BEAST_")


def normalize_beast_id_value(beast_id):
    value = str(beast_id or "").strip()
    return "" if is_placeholder_beast_id(value) else value


def get_or_create_user(conn, user_key, profile=None):
    profile_data = sanitize_profile(profile)
    profile_data["user_key"] = str(user_key).strip()
    if not profile_data["user_key"]:
        raise ValueError("缺少 user_key")

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE user_key=%s LIMIT 1", (profile_data["user_key"],))
        user = cursor.fetchone()

        if not user:
            account = profile_data["account"] or f"player_{profile_data['user_key'][-6:]}"
            beast_id = profile_data["beast_id"] or ""
            cursor.execute(
                """
                INSERT INTO users (user_key, openid, nick_name, avatar_url, account, beast_id, phone, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    profile_data["user_key"],
                    profile_data["openid"] or None,
                    profile_data["nick_name"],
                    profile_data["avatar_url"],
                    account,
                    beast_id,
                    profile_data["phone"],
                    profile_data["email"],
                ),
            )
            user_id = cursor.lastrowid
            cursor.execute("INSERT INTO user_wallets (user_id) VALUES (%s)", (user_id,))
            cursor.execute("SELECT * FROM users WHERE id=%s LIMIT 1", (user_id,))
            user = cursor.fetchone()
        else:
            updates = []
            params = []
            field_map = {
                "openid": "openid",
                "nick_name": "nick_name",
                "avatar_url": "avatar_url",
                "account": "account",
                "beast_id": "beast_id",
                "phone": "phone",
                "email": "email",
            }
            for key, column in field_map.items():
                value = profile_data.get(key)
                if value and value != (user.get(column) or ""):
                    updates.append(f"{column}=%s")
                    params.append(value)
            if updates:
                params.append(user["id"])
                cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=%s", params)
                cursor.execute("SELECT * FROM users WHERE id=%s LIMIT 1", (user["id"],))
                user = cursor.fetchone()

        from db_promotion import ensure_user_invite_code

        ensure_user_invite_code(conn, user)
        cursor.execute("SELECT * FROM users WHERE id=%s LIMIT 1", (user["id"],))
        user = cursor.fetchone()
        cursor.execute("SELECT * FROM user_wallets WHERE user_id=%s LIMIT 1", (user["id"],))
        wallet = cursor.fetchone()
        if not wallet:
            cursor.execute("INSERT INTO user_wallets (user_id) VALUES (%s)", (user["id"],))
            cursor.execute("SELECT * FROM user_wallets WHERE user_id=%s LIMIT 1", (user["id"],))
            wallet = cursor.fetchone()

    return user, wallet
