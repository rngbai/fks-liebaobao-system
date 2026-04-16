import base64
import binascii
import json
import logging
import logging.handlers
import mimetypes
import os
import secrets
import uuid
from pathlib import Path

# 自动加载同目录下的 .env 文件（本地开发用）
_env_file = Path(__file__).resolve().parent / '.env'
if _env_file.exists():
    for _line in _env_file.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and not _line.startswith('#') and '=' in _line:
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse



from config import token, userId
from db_mysql import (
    DEFAULT_CANCEL_LIMIT,
    bind_user_inviter,
    build_feedback_payload,
    build_home_content_payload,
    build_manage_dashboard,
    build_manage_feedback_payload,
    build_manage_guarantee_payload,
    build_manage_home_content_payload,
    build_manage_promotion_payload,
    build_manage_recharge_payload,
    build_manage_transfer_request_payload,
    build_manage_users_payload,
    build_game_config_payload,
    build_pending_summary,
    build_promotion_payload,
    build_recharge_state,
    get_live_game_credentials,
    save_game_config,
    list_community_profiles,
    create_community_profile,
    update_community_profile,
    delete_community_profile,
    settle_monthly_promotion,

    build_transfer_state,
    build_user_stats,
    cancel_recharge_order,
    complete_transfer_request,
    reject_transfer_request,

    create_feedback,

    create_guarantee_order,
    create_recharge_order,
    create_transfer_request,
    find_guarantee_order,
    import_manage_users,
    list_public_guarantee_orders,
    seller_confirm_guarantee_order,
    seller_reject_guarantee_order,

    find_recharge_order,
    get_connection,
    get_or_create_user,
    init_database_and_tables,
    list_guarantee_orders,
    list_wallet_records,
    mark_recharge_success,
    match_guarantee_order,
    now_ms,
    serialize_feedback_row,
    serialize_guarantee_row,
    serialize_manage_feedback_row,
    serialize_transfer_request,
    serialize_user,
    serialize_wallet,
    save_manage_home_content_payload,
    update_feedback_status,
)





from select_rockLog import (
    DEFAULT_VERIFY_MINUTES,
    TokenExpiredError,
    fetch_recent_sell_logs,
    verify_recent_recharge,
)

HOST = os.environ.get('RECHARGE_VERIFY_HOST', '0.0.0.0')
PORT = int(os.environ.get('RECHARGE_VERIFY_PORT', '5000'))

LOG_DIR = Path(os.environ.get('FKS_LOG_DIR', Path(__file__).resolve().parent / 'logs'))
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _setup_logging():
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)
    rotating = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / 'app.log', when='midnight', backupCount=14, encoding='utf-8'
    )
    rotating.setFormatter(fmt)
    root.addHandler(rotating)

_setup_logging()
logger = logging.getLogger('fks')
RECEIVER_BEAST_ID = str(userId)
RECEIVER_BEAST_NICK = os.environ.get('RECEIVER_BEAST_NICK', '面板小助手')
BASE_DIR = Path(__file__).resolve().parent
ADMIN_DIST_DIR = BASE_DIR / 'admin' / 'dist'
ADMIN_INDEX_FILE = ADMIN_DIST_DIR / 'index.html'
UPLOADS_DIR = BASE_DIR / 'uploads'
ALLOWED_UPLOAD_FOLDERS = {'guarantee-proof', 'community-avatar'}
ADMIN_USERNAME = os.environ.get('FKS_ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('FKS_ADMIN_PASSWORD', '')
try:
    ADMIN_SESSION_TTL_MS = max(10 * 60 * 1000, int(os.environ.get('FKS_ADMIN_SESSION_TTL_MS', '43200000')))
except (TypeError, ValueError):
    ADMIN_SESSION_TTL_MS = 12 * 60 * 60 * 1000
ADMIN_SESSIONS = {}




def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_bytes(handler, status_code, body, content_type='application/octet-stream'):
    handler.send_response(status_code)
    handler.send_header('Content-Type', content_type)
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, openid, x-user-key, x-admin-token')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    handler.end_headers()
    handler.wfile.write(body)


def build_json(handler, status_code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    build_bytes(handler, status_code, body, 'application/json; charset=utf-8')


def build_html(handler, status_code, html_text):
    build_bytes(handler, status_code, html_text.encode('utf-8'), 'text/html; charset=utf-8')



def ok(data=None, message='success'):
    return {'ok': True, 'message': message, 'data': data or {}}


def fail(message, status=200, data=None):
    return status, {'ok': False, 'message': message, 'data': data or {}}



def resolve_admin_asset(request_path):
    if request_path in ('/admin', '/admin/', '/admin/index.html'):
        return ADMIN_INDEX_FILE

    if not request_path.startswith('/admin/'):
        raise FileNotFoundError('后台资源路径不存在')

    relative_path = request_path[len('/admin/'):].lstrip('/')
    if not relative_path:
        return ADMIN_INDEX_FILE

    admin_root = ADMIN_DIST_DIR.resolve()
    candidate = (ADMIN_DIST_DIR / relative_path).resolve()
    try:
        candidate.relative_to(admin_root)
    except ValueError as exc:
        raise PermissionError('非法后台资源路径') from exc

    if candidate.is_file():
        return candidate

    if Path(relative_path).suffix:
        raise FileNotFoundError(f'未找到后台资源文件: {candidate}')

    return ADMIN_INDEX_FILE


def load_admin_asset(request_path):
    asset_path = resolve_admin_asset(request_path)
    if not asset_path.exists():
        raise FileNotFoundError(f'未找到后台构建文件: {asset_path}')

    content_type = mimetypes.guess_type(str(asset_path))[0] or 'application/octet-stream'
    suffix = asset_path.suffix.lower()
    if suffix == '.html':
        content_type = 'text/html; charset=utf-8'
    elif suffix == '.css':
        content_type = 'text/css; charset=utf-8'
    elif suffix == '.js':
        content_type = 'text/javascript; charset=utf-8'
    elif suffix == '.json':
        content_type = 'application/json; charset=utf-8'

    return asset_path.read_bytes(), content_type



def load_upload_asset(request_path):
    relative_path = str(request_path or '')[len('/uploads/'):].lstrip('/')
    if not relative_path:
        raise FileNotFoundError('缺少上传资源路径')
    upload_root = UPLOADS_DIR.resolve()
    candidate = (UPLOADS_DIR / relative_path).resolve()
    try:
        candidate.relative_to(upload_root)
    except ValueError as exc:
        raise PermissionError('非法上传资源路径') from exc
    if not candidate.is_file():
        raise FileNotFoundError(f'未找到上传资源文件: {candidate}')
    content_type = mimetypes.guess_type(str(candidate))[0] or 'application/octet-stream'
    return candidate.read_bytes(), content_type


def save_base64_image(image_base64, image_name='', folder='guarantee-proof'):
    folder_name = str(folder or 'guarantee-proof').strip().lower() or 'guarantee-proof'
    if folder_name not in ALLOWED_UPLOAD_FOLDERS:
        folder_name = 'guarantee-proof'

    raw_text = str(image_base64 or '').strip()
    if not raw_text:
        raise ValueError('缺少图片内容')

    header = ''
    if raw_text.startswith('data:'):
        header, _, raw_text = raw_text.partition(',')

    try:
        content = base64.b64decode(raw_text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('图片数据解析失败') from exc

    if not content:
        raise ValueError('图片内容为空')

    suffix = Path(str(image_name or '')).suffix.lower()
    if suffix not in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
        if 'image/png' in header.lower():
            suffix = '.png'
        elif 'image/webp' in header.lower():
            suffix = '.webp'
        elif 'image/gif' in header.lower():
            suffix = '.gif'
        else:
            suffix = '.jpg'
    if suffix == '.jpeg':
        suffix = '.jpg'

    upload_dir = (UPLOADS_DIR / folder_name).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f'{uuid.uuid4().hex}{suffix}'
    file_path = upload_dir / file_name
    file_path.write_bytes(content)
    return f'/uploads/{folder_name}/{file_name}'


def build_public_file_url(handler, relative_url):
    host = str(handler.headers.get('Host') or f'127.0.0.1:{PORT}').strip()
    return f'http://{host}{relative_url}'


def cleanup_admin_sessions():
    current_ms = now_ms()
    expired_tokens = [
        session_token
        for session_token, session in ADMIN_SESSIONS.items()
        if current_ms >= int((session or {}).get('expiresAt') or 0)
    ]
    for session_token in expired_tokens:
        ADMIN_SESSIONS.pop(session_token, None)



def create_admin_session(username):
    cleanup_admin_sessions()
    session_token = secrets.token_urlsafe(32)
    expires_at = now_ms() + ADMIN_SESSION_TTL_MS
    ADMIN_SESSIONS[session_token] = {
        'username': username,
        'expiresAt': expires_at,
    }
    return {
        'token': session_token,
        'username': username,
        'expiresAt': expires_at,
    }



def revoke_admin_session(session_token):
    if session_token:
        ADMIN_SESSIONS.pop(session_token, None)



def verify_admin_login(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD



def make_profile(payload, headers):


    return {
        'nickName': payload.get('nickName') or payload.get('nick_name') or '',
        'avatarUrl': payload.get('avatarUrl') or payload.get('avatar_url') or '',
        'account': payload.get('account') or '',
        'beastId': payload.get('beastId') or payload.get('beast_id') or '',
        'phone': payload.get('phone') or '',
        'email': payload.get('email') or '',
        'openid': headers.get('openid') or payload.get('openid') or '',
    }


class RechargeVerifyHandler(BaseHTTPRequestHandler):
    server_version = 'RechargeVerifyHTTP/3.0'

    def log_message(self, fmt, *args):
        logger.info('[api] ' + fmt % args)

    def do_OPTIONS(self):
        build_json(self, 204, {})

    def read_json_body(self):
        length = to_int(self.headers.get('Content-Length'), 0) or 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode('utf-8')
        return json.loads(raw or '{}')

    def get_user_key(self, payload=None):
        payload = payload or {}
        return (
            self.headers.get('x-user-key')
            or self.headers.get('openid')
            or payload.get('user_key')
            or payload.get('openid')
            or 'local_debug_user'
        )

    def get_admin_token(self):
        return str(self.headers.get('x-admin-token') or '').strip()

    def get_admin_session(self):
        cleanup_admin_sessions()
        session_token = self.get_admin_token()
        if not session_token:
            return None
        session = ADMIN_SESSIONS.get(session_token)
        if not session:
            return None
        expires_at = int(session.get('expiresAt') or 0)
        if expires_at and expires_at <= now_ms():
            ADMIN_SESSIONS.pop(session_token, None)
            return None
        return {
            'token': session_token,
            'username': session.get('username') or ADMIN_USERNAME,
            'expiresAt': expires_at,
        }

    def is_admin_authed(self):
        return self.get_admin_session() is not None

    def ensure_admin(self):
        session = self.get_admin_session()
        if session:
            return session
        build_json(self, 401, {'ok': False, 'message': '后台未登录或登录已失效'})
        return None


    def get_recharge_state_payload(self, user_key, profile=None):

        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            data = build_recharge_state(conn, user_row, wallet_row, RECEIVER_BEAST_ID, RECEIVER_BEAST_NICK)
            conn.commit()
            return data

    def get_user_profile_payload(self, user_key, profile=None):
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            payload = {
                'user': serialize_user(user_row),
                'wallet': serialize_wallet(wallet_row),
                'stats': build_user_stats(conn, user_row['id']),
            }
            conn.commit()
            return payload

    def get_transfer_state_payload(self, user_key, profile=None, limit=20):
        with get_connection(autocommit=False) as conn:
            user_row, wallet_row = get_or_create_user(conn, user_key, profile)
            payload = build_transfer_state(conn, user_row, wallet_row, limit=limit)
            conn.commit()
            return payload

    def get_guarantee_list_payload(self, user_key, profile=None, limit=20):

        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            orders = list_guarantee_orders(conn, user_id=user_row['id'], role='seller', limit=limit)
            wallet_row = get_or_create_user(conn, user_key, profile)[1]
            payload = {
                'wallet': serialize_wallet(wallet_row),
                'orders': orders,
            }
            conn.commit()
            return payload


    def get_guarantee_detail_payload(self, user_key, order_no, profile=None):
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            order_row = find_guarantee_order(conn, order_no)
            if not order_row:
                raise ValueError('未找到担保单')
            wallet_row = get_or_create_user(conn, user_key, profile)[1]
            seller_user_id = int(order_row.get('seller_user_id') or 0)
            buyer_user_id = int(order_row.get('buyer_user_id') or 0)
            current_user_id = int(user_row.get('id') or 0)
            can_match = (order_row.get('status') == 'pending') and seller_user_id != current_user_id
            viewer_role = 'seller' if seller_user_id == current_user_id else ('buyer' if buyer_user_id == current_user_id else 'guest')
            payload = {
                'order': serialize_guarantee_row(order_row),
                'wallet': serialize_wallet(wallet_row),
                'viewerRole': viewer_role,
                'canMatch': can_match,
            }
            conn.commit()
            return payload


    def get_feedback_payload(self, user_key, profile=None, limit=20, mine_only=False):
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            payload = build_feedback_payload(conn, user_row, limit=limit, mine_only=mine_only)
            conn.commit()
            return payload

    def get_promotion_payload(self, user_key, profile=None, limit=20):
        with get_connection(autocommit=False) as conn:
            user_row, _ = get_or_create_user(conn, user_key, profile)
            payload = build_promotion_payload(conn, user_row, limit=limit)
            conn.commit()
            return payload

    def get_home_content_payload(self):
        with get_connection(autocommit=False) as conn:
            payload = build_home_content_payload(conn)
            conn.commit()
            return payload

    def get_live_credentials(self, conn=None):
        """从 DB 读当前游戏凭证，优先 DB，降级到启动时的环境变量。"""
        if conn is not None:
            return get_live_game_credentials(conn, RECEIVER_BEAST_ID, token)
        with get_connection(autocommit=False) as c:
            uid, tk = get_live_game_credentials(c, RECEIVER_BEAST_ID, token)
            c.commit()
        return uid, tk

    def do_GET(self):



        parsed = urlparse(self.path)

        if parsed.path == '/admin' or parsed.path.startswith('/admin/'):
            try:
                body, content_type = load_admin_asset(parsed.path)
                build_bytes(self, 200, body, content_type)
            except PermissionError as exc:
                build_json(self, 403, {'ok': False, 'message': str(exc)})
            except FileNotFoundError as exc:
                build_json(self, 404, {'ok': False, 'message': str(exc)})
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取后台页面失败: {exc}'})
            return

        if parsed.path.startswith('/uploads/'):
            try:
                body, content_type = load_upload_asset(parsed.path)
                build_bytes(self, 200, body, content_type)
            except PermissionError as exc:
                build_json(self, 403, {'ok': False, 'message': str(exc)})
            except FileNotFoundError as exc:
                build_json(self, 404, {'ok': False, 'message': str(exc)})
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取上传图片失败: {exc}'})
            return

        if parsed.path == '/api/manage/auth-check':

            session = self.get_admin_session()
            if session:
                build_json(self, 200, ok({
                    'dashboardPath': '/admin/',
                    'username': session.get('username') or ADMIN_USERNAME,
                    'expiresAt': session.get('expiresAt') or 0,
                }, '验证成功'))
            else:
                build_json(self, 401, {'ok': False, 'message': '后台未登录或登录已失效'})
            return


        params = parse_qs(parsed.query)
        user_key = self.get_user_key({
            'user_key': params.get('user_key', [''])[0],
            'openid': params.get('openid', [''])[0],
        })

        if parsed.path == '/api/recharge/health':
            build_json(self, 200, ok({
                'uid': RECEIVER_BEAST_ID,
                'port': PORT,
                'receiverBeastNick': RECEIVER_BEAST_NICK,
                'cancelLimit': DEFAULT_CANCEL_LIMIT,
                'adminPath': '/admin/',
            }, 'recharge verify server is running'))
            return


        if parsed.path == '/api/recharge/recent':
            minutes = max(1, to_int(params.get('minutes', [DEFAULT_VERIFY_MINUTES])[0], DEFAULT_VERIFY_MINUTES))
            try:
                live_uid, live_tk = self.get_live_credentials()
                logs = fetch_recent_sell_logs(live_uid, live_tk, minutes=minutes)
                build_json(self, 200, ok({
                    'minutes': minutes,
                    'logs': logs,
                    'count': len(logs)
                }, '查询成功'))
            except TokenExpiredError as exc:
                build_json(self, 401, {'ok': False, 'message': str(exc)})
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'查询失败: {exc}'})
            return

        if parsed.path == '/api/recharge/state':
            try:
                data = self.get_recharge_state_payload(user_key)
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取充值状态失败: {exc}'})
            return

        if parsed.path == '/api/user/profile':
            try:
                data = self.get_user_profile_payload(user_key)
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取用户资料失败: {exc}'})
            return

        if parsed.path == '/api/user/balance':
            try:
                data = self.get_user_profile_payload(user_key)
                build_json(self, 200, ok({'gemBalance': data['wallet']['gemBalance']}, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取余额失败: {exc}'})
            return

        if parsed.path == '/api/user/wallet-records':
            limit = max(1, to_int(params.get('limit', ['50'])[0], 50))
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, wallet_row = get_or_create_user(conn, user_key)
                    records = list_wallet_records(conn, user_row['id'], limit)
                    transfer_payload = build_transfer_state(conn, user_row, wallet_row, limit=10)
                    wallet = serialize_wallet(wallet_row)
                    conn.commit()
                build_json(self, 200, ok({
                    'user': transfer_payload['user'],
                    'balance': wallet['gemBalance'],
                    'lockedGems': wallet['lockedGems'],
                    'totalRecharged': wallet['totalRecharged'],
                    'totalSpent': wallet['totalSpent'],
                    'totalEarned': wallet['totalEarned'],
                    'pendingTransfer': transfer_payload['transfer']['pendingRequest'],
                    'transferHistory': transfer_payload['transfer']['history'],
                    'records': records,
                }, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取宝石流水失败: {exc}'})
            return

        if parsed.path == '/api/transfer/state':
            limit = max(1, to_int(params.get('limit', ['20'])[0], 20))
            try:
                data = self.get_transfer_state_payload(user_key, limit=limit)
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取转出状态失败: {exc}'})
            return

        if parsed.path == '/api/guarantee/list':

            limit = max(1, to_int(params.get('limit', ['20'])[0], 20))
            try:
                data = self.get_guarantee_list_payload(user_key, limit=limit)
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取担保列表失败: {exc}'})
            return

        if parsed.path == '/api/guarantee/detail':
            order_no = str(params.get('order_no', [''])[0] or params.get('id', [''])[0]).strip()
            if not order_no:
                build_json(self, 200, {'ok': False, 'message': '缺少担保单号'})
                return
            try:
                data = self.get_guarantee_detail_payload(user_key, order_no)
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取担保单失败: {exc}'})
            return

        if parsed.path == '/api/feedback/list':
            limit = max(1, to_int(params.get('limit', ['20'])[0], 20))
            mine_only = str(params.get('mine', ['0'])[0] or '').strip().lower() in ('1', 'true', 'yes', 'mine')
            try:
                data = self.get_feedback_payload(user_key, limit=limit, mine_only=mine_only)
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取反馈列表失败: {exc}'})
            return

        if parsed.path == '/api/promotion/my':
            limit = max(1, to_int(params.get('limit', ['20'])[0], 20))
            try:
                data = self.get_promotion_payload(user_key, limit=limit)
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取推广信息失败: {exc}'})
            return

        if parsed.path == '/api/user/pending-summary':
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, _ = get_or_create_user(conn, user_key)
                    data = build_pending_summary(conn, user_row['id'])
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取待办摘要失败: {exc}'})
            return

        if parsed.path == '/api/guarantee/public':
            limit = max(1, to_int(params.get('limit', ['20'])[0], 20))
            pet_name = str(params.get('pet_name', [''])[0] or '').strip() or None
            try:
                with get_connection(autocommit=False) as conn:
                    orders = list_public_guarantee_orders(conn, limit=limit, pet_name=pet_name)
                    conn.commit()
                build_json(self, 200, ok({'orders': orders}, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取公开保单失败: {exc}'})
            return

        if parsed.path == '/api/home/content':
            try:
                data = self.get_home_content_payload()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取首页内容失败: {exc}'})
            return

        if parsed.path == '/api/manage/home-content':
            if not self.ensure_admin():
                return
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_home_content_payload(conn)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取首页内容管理数据失败: {exc}'})
            return

        if parsed.path == '/api/manage/users':

            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_users_payload(conn, query=query, status=status, page=page, page_size=page_size)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取用户管理数据失败: {exc}'})
            return

        if parsed.path == '/api/manage/promotions':
            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            reward_limit = max(1, to_int(params.get('reward_limit', ['30'])[0], 30))
            invitee_limit = max(1, to_int(params.get('invitee_limit', ['40'])[0], 40))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_promotion_payload(
                        conn,
                        query=query,
                        status=status,
                        page=page,
                        page_size=page_size,
                        reward_limit=reward_limit,
                        invitee_limit=invitee_limit,
                    )
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取推广管理数据失败: {exc}'})
            return

        if parsed.path == '/api/manage/recharges':
            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_recharge_payload(conn, query=query, status=status, page=page, page_size=page_size)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取充值记录失败: {exc}'})
            return

        if parsed.path == '/api/manage/guarantees':
            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_guarantee_payload(conn, query=query, status=status, page=page, page_size=page_size)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取担保档案失败: {exc}'})
            return

        if parsed.path == '/api/manage/feedbacks':
            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_feedback_payload(conn, query=query, status=status, page=page, page_size=page_size)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取反馈档案失败: {exc}'})
            return

        if parsed.path == '/api/manage/pending-guarantees':
            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_guarantee_payload(conn, query=query, status=status, page=page, page_size=page_size, pending_only=True)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取担保待确认列表失败: {exc}'})
            return

        if parsed.path == '/api/manage/transfer-requests':
            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_transfer_request_payload(conn, query=query, status=status, page=page, page_size=page_size)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取用户转出申请失败: {exc}'})
            return


        if parsed.path == '/api/manage/pending-feedbacks':
            if not self.ensure_admin():
                return
            page = max(1, to_int(params.get('page', ['1'])[0], 1))
            page_size = max(1, to_int(params.get('page_size', ['20'])[0], 20))
            query = str(params.get('query', [''])[0] or '').strip()
            status = str(params.get('status', ['all'])[0] or 'all').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_feedback_payload(conn, query=query, status=status, page=page, page_size=page_size, pending_only=True)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取待处理反馈失败: {exc}'})
            return

        if parsed.path == '/api/manage/token-config':
            if not self.ensure_admin():
                return
            try:
                with get_connection(autocommit=False) as conn:
                    data = build_game_config_payload(conn, RECEIVER_BEAST_ID, token)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取游戏凭证失败: {exc}'})
            return

        if parsed.path == '/api/manage/community':
            if not self.ensure_admin():
                return
            try:
                category = params.get('category', [None])[0]
                sub_tab = params.get('sub_tab', [None])[0]
                active_only = params.get('active_only', ['0'])[0] == '1'
                with get_connection() as conn:
                    rows = list_community_profiles(conn, category=category, sub_tab=sub_tab, active_only=active_only)
                build_json(self, 200, ok({'list': rows, 'total': len(rows)}, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'查询社区名流失败: {exc}'})
            return

        if parsed.path.startswith('/api/community'):
            try:
                category = params.get('category', [None])[0]
                sub_tab = params.get('sub_tab', [None])[0]
                with get_connection() as conn:
                    rows = list_community_profiles(conn, category=category, sub_tab=sub_tab, active_only=True)
                build_json(self, 200, ok({'list': rows}, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'查询社区名流失败: {exc}'})
            return

        if parsed.path == '/api/manage/dashboard':



            if not self.ensure_admin():
                return
            days = max(3, to_int(params.get('days', ['7'])[0], 7))
            limit = max(0, to_int(params.get('limit', ['20'])[0], 20))

            try:
                with get_connection(autocommit=False) as conn:
                    data = build_manage_dashboard(conn, days=days, limit=limit)
                    conn.commit()
                build_json(self, 200, ok(data, '查询成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'读取管理台数据失败: {exc}'})
            return


        build_json(self, 404, {'ok': False, 'message': '接口不存在'})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self.read_json_body()
        except Exception as exc:
            build_json(self, 400, {'ok': False, 'message': f'请求体不是合法 JSON: {exc}'})
            return

        if parsed.path == '/api/manage/login':
            username = str(payload.get('username') or '').strip()
            password = str(payload.get('password') or '')
            if not username or not password:
                build_json(self, 400, {'ok': False, 'message': '请输入后台账号和密码'})
                return
            if not verify_admin_login(username, password):
                build_json(self, 401, {'ok': False, 'message': '后台账号或密码错误'})
                return
            session = create_admin_session(username)
            build_json(self, 200, ok({
                'token': session.get('token') or '',
                'username': session.get('username') or username,
                'expiresAt': session.get('expiresAt') or 0,
            }, '登录成功'))
            return

        if parsed.path == '/api/manage/logout':
            revoke_admin_session(self.get_admin_token())
            build_json(self, 200, ok({}, '已退出登录'))
            return

        if parsed.path.startswith('/api/manage/') and not self.ensure_admin():
            return

        if parsed.path == '/api/manage/users/import':
            raw_text = str(payload.get('text') or payload.get('raw_text') or payload.get('content') or '').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    result = import_manage_users(conn, raw_text)
                    latest = build_manage_users_payload(conn, page=1, page_size=20)
                    conn.commit()
                build_json(self, 200, ok({
                    'result': result,
                    'latest': latest,
                }, '用户导入完成'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'导入用户失败: {exc}'})
            return

        if parsed.path == '/api/manage/home-content':
            content_payload = payload.get('content') if isinstance(payload.get('content'), dict) else payload
            try:
                with get_connection(autocommit=False) as conn:
                    data = save_manage_home_content_payload(conn, content_payload)
                    conn.commit()
                build_json(self, 200, ok(data, '首页内容已保存'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'保存首页内容失败: {exc}'})
            return

        user_key = self.get_user_key(payload)

        profile = make_profile(payload, self.headers)

        if parsed.path == '/api/promotion/bind':
            invite_code = str(payload.get('invite_code') or payload.get('inviteCode') or payload.get('ref') or '').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, _ = get_or_create_user(conn, user_key, profile)
                    user_row = bind_user_inviter(conn, user_row, invite_code)
                    data = build_promotion_payload(conn, user_row, limit=max(1, to_int(payload.get('limit'), 20)))
                    conn.commit()
                build_json(self, 200, ok(data, '推荐码绑定成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'绑定推荐码失败: {exc}'})
            return

        if parsed.path == '/api/user/profile':


            try:
                data = self.get_user_profile_payload(user_key, profile)
                build_json(self, 200, ok(data, '保存成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'保存用户资料失败: {exc}'})
            return

        if parsed.path == '/api/feedback/create':
            feedback_type = str(payload.get('type') or payload.get('feedback_type') or '其他').strip()
            title = str(payload.get('title') or '').strip()
            content = str(payload.get('content') or payload.get('desc') or '').strip()
            contact = str(payload.get('contact') or '').strip()
            limit = max(1, to_int(payload.get('limit'), 20))
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, _ = get_or_create_user(conn, user_key, profile)
                    feedback_row = create_feedback(conn, user_row, feedback_type, title, content, contact=contact)
                    data = build_feedback_payload(conn, user_row, limit=limit, mine_only=False)
                    data['created'] = serialize_feedback_row(feedback_row, viewer_user_id=user_row['id'])
                    conn.commit()
                build_json(self, 200, ok(data, '反馈已提交'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'提交反馈失败: {exc}'})
            return

        if parsed.path == '/api/upload/image':
            image_base64 = str(payload.get('image_base64') or payload.get('imageBase64') or '').strip()
            image_name = str(payload.get('image_name') or payload.get('imageName') or '').strip()
            folder = str(payload.get('folder') or 'guarantee-proof').strip().lower() or 'guarantee-proof'
            try:
                if folder not in ALLOWED_UPLOAD_FOLDERS:
                    folder = 'guarantee-proof'
                if not image_base64:
                    raise ValueError('缺少图片内容')
                header = ''
                raw_text = image_base64
                if raw_text.startswith('data:'):
                    header, _, raw_text = raw_text.partition(',')
                try:
                    content = base64.b64decode(raw_text, validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise ValueError('图片数据解析失败') from exc
                if not content:
                    raise ValueError('图片内容为空')
                suffix = Path(str(image_name or '')).suffix.lower()
                if suffix not in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
                    if 'image/png' in header.lower():
                        suffix = '.png'
                    elif 'image/webp' in header.lower():
                        suffix = '.webp'
                    elif 'image/gif' in header.lower():
                        suffix = '.gif'
                    else:
                        suffix = '.jpg'
                if suffix == '.jpeg':
                    suffix = '.jpg'
                upload_dir = (UPLOADS_DIR / folder).resolve()
                upload_dir.mkdir(parents=True, exist_ok=True)
                file_name = f'{uuid.uuid4().hex}{suffix}'
                file_path = upload_dir / file_name
                file_path.write_bytes(content)
                relative_url = f'/uploads/{folder}/{file_name}'
                host = str(self.headers.get('Host') or f'127.0.0.1:{PORT}').strip()
                build_json(self, 200, ok({
                    'url': f'http://{host}{relative_url}',
                    'path': relative_url,
                }, '上传成功'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'上传图片失败: {exc}'})
            return


        if parsed.path == '/api/recharge/create':

            amount = to_int(payload.get('amount'), 0)

            beast_id = str(payload.get('beast_id') or RECEIVER_BEAST_ID)
            beast_nick = str(payload.get('beast_nick') or RECEIVER_BEAST_NICK)
            if amount <= 0:
                status, body = fail('请输入正确的转入数量')
                build_json(self, status, body)
                return
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, wallet_row = get_or_create_user(conn, user_key, profile)
                    create_recharge_order(conn, user_row, amount, beast_id, beast_nick)
                    updated_wallet_row = wallet_row
                    data = build_recharge_state(conn, user_row, updated_wallet_row, RECEIVER_BEAST_ID, RECEIVER_BEAST_NICK)
                    conn.commit()
                build_json(self, 200, ok(data, '订单已创建'))
            except PermissionError as exc:
                status, body = fail(str(exc))
                build_json(self, status, body)
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'创建充值订单失败: {exc}'})
            return

        if parsed.path == '/api/recharge/cancel':
            order_id = str(payload.get('order_id') or '').strip()
            if not order_id:
                status, body = fail('缺少 order_id')
                build_json(self, status, body)
                return
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, wallet_row = get_or_create_user(conn, user_key, profile)
                    cancel_recharge_order(conn, user_row, order_id)
                    data = build_recharge_state(conn, user_row, wallet_row, RECEIVER_BEAST_ID, RECEIVER_BEAST_NICK)
                    conn.commit()
                build_json(self, 200, ok(data, '订单已取消'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'取消订单失败: {exc}'})
            return

        if parsed.path == '/api/recharge/verify':
            order_id = str(payload.get('order_id') or '').strip()
            verify_code = str(payload.get('verify_code') or '').strip()
            expire_minutes = max(1, to_int(payload.get('expire_minutes'), DEFAULT_VERIFY_MINUTES))

            if not order_id:
                status, body = fail('缺少 order_id')
                build_json(self, status, body)
                return
            if len(verify_code) != 4:
                status, body = fail('请输入时间后4位数字')
                build_json(self, status, body)
                return

            try:
                with get_connection(autocommit=False) as conn:
                    user_row, wallet_row = get_or_create_user(conn, user_key, profile)
                    order_row = find_recharge_order(conn, user_row['id'], order_id)
                    if not order_row:
                        status, body = fail('未找到充值订单')
                        build_json(self, status, body)
                        return

                    current_ms = now_ms()
                    if order_row.get('status') == 'pending' and current_ms > int(order_row.get('expire_at_ms') or 0):
                        conn.cursor().execute(
                            "UPDATE recharge_orders SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE id=%s AND user_id=%s AND status='pending'",
                            (order_id, user_row['id'])
                        )
                        data = build_recharge_state(conn, user_row, wallet_row, RECEIVER_BEAST_ID, RECEIVER_BEAST_NICK)
                        conn.commit()
                        status, body = fail('订单已超时失效', data=data)
                        build_json(self, status, body)
                        return

                    if order_row.get('status') == 'success':
                        data = build_recharge_state(conn, user_row, wallet_row, RECEIVER_BEAST_ID, RECEIVER_BEAST_NICK)
                        matched = {
                            'datetime': order_row.get('matched_datetime') or '',
                            'timestamp': int(order_row.get('matched_timestamp') or 0),
                        }
                        conn.commit()
                        build_json(self, 200, ok({
                            **data,
                            'matched': matched,
                            'newBalance': serialize_wallet(wallet_row)['gemBalance'],
                        }, '该订单已校验成功'))
                        return

                    live_uid, live_tk = get_live_game_credentials(conn, RECEIVER_BEAST_ID, token)
                    result = verify_recent_recharge(
                        live_uid,
                        live_tk,
                        amount=order_row['amount'],
                        verify_code=verify_code,
                        created_after_ms=order_row['created_at_ms'],
                        expire_minutes=expire_minutes,
                    )
                    if not result.get('ok'):
                        conn.commit()
                        status, body = fail(result.get('message') or '未匹配到10分钟内对应记录')
                        build_json(self, status, body)
                        return

                    matched_log = result.get('matched') or {}
                    new_balance = mark_recharge_success(conn, user_row, order_row, matched_log, verify_code)
                    wallet_row['gem_balance'] = new_balance
                    data = build_recharge_state(conn, user_row, wallet_row, RECEIVER_BEAST_ID, RECEIVER_BEAST_NICK)
                    conn.commit()
                    build_json(self, 200, ok({
                        **data,
                        'matched': matched_log,
                        'newBalance': new_balance,
                    }, '校验成功'))
            except TokenExpiredError as exc:
                build_json(self, 401, {'ok': False, 'message': str(exc)})
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'校验失败: {exc}'})
            return

        if parsed.path == '/api/guarantee/create':
            gem_amount = to_int(payload.get('gem_amount') or payload.get('amount'), 0)
            remark = str(payload.get('remark') or '').strip()
            pet_name = str(payload.get('pet_name') or payload.get('petName') or '').strip()
            trade_quantity = max(1, to_int(payload.get('trade_quantity') or payload.get('tradeQuantity'), 1))
            seller_game_id = str(payload.get('seller_game_id') or payload.get('sellerGameId') or '').strip()
            seller_game_nick = str(payload.get('seller_game_nick') or payload.get('sellerGameNick') or '').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, _ = get_or_create_user(conn, user_key, profile)
                    order_row = create_guarantee_order(
                        conn,
                        user_row,
                        gem_amount,
                        remark=remark,
                        pet_name=pet_name,
                        trade_quantity=trade_quantity,
                        seller_game_id=seller_game_id,
                        seller_game_nick=seller_game_nick,
                    )
                    wallet_row = get_or_create_user(conn, user_key, profile)[1]
                    conn.commit()
                build_json(self, 200, ok({
                    'order': serialize_guarantee_row(order_row),
                    'wallet': serialize_wallet(wallet_row),
                }, '担保单已创建'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'创建担保单失败: {exc}'})
            return

        if parsed.path == '/api/guarantee/match':
            order_no = str(payload.get('order_no') or payload.get('orderId') or '').strip()
            buyer_beast_id = str(payload.get('buyer_beast_id') or payload.get('buyerBeastId') or '').strip()
            buyer_beast_nick = str(payload.get('buyer_beast_nick') or payload.get('buyerBeastNick') or '').strip()
            buyer_trade_note = str(payload.get('buyer_trade_note') or payload.get('buyerTradeNote') or '').strip()
            buyer_proof_image = str(payload.get('buyer_proof_image') or payload.get('buyerProofImage') or '').strip()
            if not order_no:
                build_json(self, 200, {'ok': False, 'message': '缺少担保单号'})
                return
            try:
                with get_connection(autocommit=False) as conn:
                    buyer_user_row, _ = get_or_create_user(conn, user_key, profile)
                    order_row = match_guarantee_order(
                        conn,
                        order_no,
                        buyer_user_row,
                        buyer_beast_id,
                        buyer_beast_nick,
                        buyer_trade_note=buyer_trade_note,
                        buyer_proof_image=buyer_proof_image,
                    )
                    conn.commit()
                build_json(self, 200, ok({
                    'order': serialize_guarantee_row(order_row),
                    'viewerRole': 'buyer',
                    'canMatch': False,
                }, '匹配成功，等待卖家确认'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'买家匹配失败: {exc}'})
            return



        if parsed.path == '/api/transfer/create':
            request_amount = to_int(payload.get('amount') or payload.get('request_amount'), 0)
            user_note = str(payload.get('remark') or payload.get('user_note') or '').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    user_row, wallet_row = get_or_create_user(conn, user_key, profile)
                    request_row = create_transfer_request(conn, user_row, request_amount, user_note=user_note)
                    wallet_row = get_or_create_user(conn, user_key, profile)[1]
                    data = build_transfer_state(conn, user_row, wallet_row, limit=20)
                    conn.commit()
                build_json(self, 200, ok({
                    **data,
                    'request': serialize_transfer_request(request_row),
                }, '转出申请已提交'))

            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'提交转出申请失败: {exc}'})
            return

        if parsed.path == '/api/guarantee/seller-confirm':
            order_no = str(payload.get('order_no') or payload.get('orderId') or '').strip()
            if not order_no:
                build_json(self, 200, {'ok': False, 'message': '缺少担保单号'})
                return
            try:
                with get_connection(autocommit=False) as conn:
                    seller_user_row, _ = get_or_create_user(conn, user_key, profile)
                    order_row = seller_confirm_guarantee_order(conn, order_no, seller_user_row)
                    conn.commit()
                build_json(self, 200, ok({
                    'order': serialize_guarantee_row(order_row),
                    'viewerRole': 'seller',
                    'canMatch': False,
                }, '卖家已确认，系统已按双边手续费规则自动给买家结算到账'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'卖家确认失败: {exc}'})
            return

        if parsed.path == '/api/guarantee/seller-reject':
            order_no = str(payload.get('order_no') or payload.get('orderId') or '').strip()
            reject_reason = str(payload.get('reason') or payload.get('reject_reason') or '').strip()
            if not order_no:
                build_json(self, 200, {'ok': False, 'message': '缺少担保单号'})
                return
            try:
                with get_connection(autocommit=False) as conn:
                    seller_user_row, _ = get_or_create_user(conn, user_key, profile)
                    order_row = seller_reject_guarantee_order(conn, order_no, seller_user_row, reject_reason)
                    conn.commit()
                build_json(self, 200, ok({
                    'order': serialize_guarantee_row(order_row),
                    'viewerRole': 'seller',
                    'canMatch': False,
                }, '已拒绝确认，订单已进入申诉状态，等待后台人工仲裁'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'拒绝确认失败: {exc}'})
            return

        if parsed.path == '/api/manage/transfer-request/complete':
            request_id = str(payload.get('request_id') or payload.get('requestId') or '').strip()
            admin_note = str(payload.get('admin_note') or payload.get('adminNote') or '后台已完成用户转出').strip()
            if not request_id:
                build_json(self, 200, {'ok': False, 'message': '缺少转出申请单号'})
                return
            try:
                with get_connection(autocommit=False) as conn:
                    request_row = complete_transfer_request(conn, request_id, admin_note=admin_note)
                    conn.commit()
                build_json(self, 200, ok({'request': serialize_transfer_request(request_row)}, '已记录用户转出完成'))

            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'记录用户转出失败: {exc}'})
            return

        if parsed.path == '/api/manage/transfer-request/reject':
            request_id = str(payload.get('request_id') or payload.get('requestId') or '').strip()
            admin_note = str(payload.get('admin_note') or payload.get('adminNote') or '后台已拒绝本次转出申请').strip()
            if not request_id:
                build_json(self, 200, {'ok': False, 'message': '缺少转出申请单号'})
                return
            try:
                with get_connection(autocommit=False) as conn:
                    request_row = reject_transfer_request(conn, request_id, admin_note=admin_note)
                    conn.commit()
                build_json(self, 200, ok({'request': serialize_transfer_request(request_row)}, '已拒绝用户转出申请'))

            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'拒绝用户转出失败: {exc}'})
            return

        if parsed.path == '/api/manage/token-config':
            new_user_id = str(payload.get('userId') or payload.get('user_id') or '').strip()
            new_token = str(payload.get('token') or '').strip()
            try:
                with get_connection(autocommit=False) as conn:
                    data = save_game_config(conn, new_user_id, new_token)
                    conn.commit()
                logger.info(f'[admin] 游戏凭证已更新 userId={new_user_id}')
                build_json(self, 200, ok(data, '游戏凭证已更新，立即生效无需重启'))
            except ValueError as exc:
                build_json(self, 200, {'ok': False, 'message': str(exc)})
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'保存游戏凭证失败: {exc}'})
            return

        if parsed.path == '/api/manage/community':
            if not self.ensure_admin():
                return
            try:
                with get_connection() as conn:
                    row = create_community_profile(conn, payload)
                build_json(self, 200, ok({'profile': row}, '名流已添加'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'添加名流失败: {exc}'})
            return

        if parsed.path.startswith('/api/manage/community/'):
            if not self.ensure_admin():
                return
            profile_id = parsed.path.split('/')[-1]
            action = payload.get('_action', '')
            try:
                with get_connection() as conn:
                    if action == 'delete':
                        delete_community_profile(conn, profile_id)
                        build_json(self, 200, ok({}, '已删除'))
                    else:
                        row = update_community_profile(conn, profile_id, payload)
                        build_json(self, 200, ok({'profile': row}, '已更新'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'操作名流失败: {exc}'})
            return

        if parsed.path == '/api/manage/promotion/settle-monthly':
            if not self.ensure_admin():
                return
            year_month = str(payload.get('year_month') or '').strip()
            if not year_month:
                build_json(self, 200, {'ok': False, 'message': '请传 year_month，格式 YYYY-MM'})
                return
            try:
                with get_connection() as conn:
                    results = settle_monthly_promotion(conn, year_month)
                build_json(self, 200, ok({'results': results, 'count': len(results)},
                                         f'{year_month} 月度推广结算完成，共 {len(results)} 条'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'月度结算失败: {exc}'})
            return

        if parsed.path == '/api/manage/guarantee-transfer':

            build_json(self, 200, {
                'ok': False,
                'message': '担保单已改为系统自动到账，无需后台手动转出；只有用户主动发起转出申请时才需要人工处理'
            })
            return


        if parsed.path == '/api/manage/feedback/update-status':
            feedback_id = to_int(payload.get('feedback_id') or payload.get('feedbackId') or payload.get('id'), 0)
            status = str(payload.get('status') or '').strip()
            admin_reply = str(payload.get('admin_reply') or payload.get('adminReply') or '').strip()
            if feedback_id <= 0:
                build_json(self, 200, {'ok': False, 'message': '缺少反馈编号'})
                return
            try:
                with get_connection(autocommit=False) as conn:
                    feedback_row = update_feedback_status(conn, feedback_id, status, admin_reply=admin_reply)
                    conn.commit()
                build_json(self, 200, ok({'feedback': serialize_manage_feedback_row(feedback_row)}, '反馈状态已更新'))
            except Exception as exc:
                build_json(self, 500, {'ok': False, 'message': f'更新反馈状态失败: {exc}'})
            return

        build_json(self, 404, {'ok': False, 'message': '接口不存在'})




def _check_required_env():
    errors = []
    if not ADMIN_PASSWORD:
        errors.append('FKS_ADMIN_PASSWORD 未设置（不允许空密码运行）')
    from db_mysql import DB_PASSWORD
    if not DB_PASSWORD:
        errors.append('MYSQL_PASSWORD 未设置')
    if errors:
        for e in errors:
            print(f'[FATAL] {e}', flush=True)
        raise SystemExit('请在 .env 或环境变量中设置上述必需配置后再启动。')


def run_server(host=HOST, port=PORT):
    _check_required_env()
    init_database_and_tables()
    server = ThreadingHTTPServer((host, port), RechargeVerifyHandler)
    logger.info(f'recharge verify server listening on http://{host}:{port}')
    logger.info(f'log dir: {LOG_DIR}')
    server.serve_forever()


if __name__ == '__main__':
    run_server()
