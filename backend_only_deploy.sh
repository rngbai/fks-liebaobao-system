#!/usr/bin/env bash
# ============================================================
# 方块兽担保系统 —— 仅后端部署脚本
# 适用场景：Python/Node/MySQL 已安装，仅需部署后端服务与 Nginx
# 使用方式：
#   chmod +x backend_only_deploy.sh
#   sudo bash backend_only_deploy.sh
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "请以 root 或 sudo 运行此脚本"

# ===== 可调整配置 =====
# 按你的要求：所有文件都在 /root/fks_project 下，不再使用 /opt/fks
APP_ROOT="/root/fks_project"
APP_API="${APP_ROOT}/fksapi"
APP_ADMIN="${APP_ROOT}/fksAdmin"
VENV_PATH="${APP_ROOT}/venv"

MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_DB="fks_trade"
MYSQL_USER="fks_user"
MYSQL_PASSWORD="1L0v3c4ts@ndd0gs"

ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Fks@Admin2024!"

GAME_USER_ID="9100503"
GAME_TOKEN=""
RECEIVER_BEAST_NICK="面板小助手"

SERVICE_NAME="fks"

info "开始执行仅后端部署..."

# ===== 0) 前置检查 =====
[[ -d "${APP_API}" ]] || error "未找到后端目录: ${APP_API}"
[[ -d "${APP_ADMIN}" ]] || error "未找到后台目录: ${APP_ADMIN}"
command -v python3 >/dev/null 2>&1 || error "python3 不存在，请先安装 Python"
command -v npm >/dev/null 2>&1 || error "npm 不存在，请先安装 Node.js"
command -v nginx >/dev/null 2>&1 || error "nginx 不存在，请先安装 Nginx"
command -v mysql >/dev/null 2>&1 || error "mysql 客户端不存在，请先安装 MySQL"

# ===== 1) 写入 .env =====
info "写入后端环境变量文件 ${APP_API}/.env"
cat > "${APP_API}/.env" <<EOF
RECHARGE_VERIFY_HOST=127.0.0.1
RECHARGE_VERIFY_PORT=5000
MYSQL_HOST=${MYSQL_HOST}
MYSQL_PORT=${MYSQL_PORT}
MYSQL_USER=${MYSQL_USER}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_DATABASE=${MYSQL_DB}
FKS_ADMIN_USERNAME=${ADMIN_USERNAME}
FKS_ADMIN_PASSWORD=${ADMIN_PASSWORD}
FKS_GAME_USER_ID=${GAME_USER_ID}
FKS_GAME_TOKEN=${GAME_TOKEN}
RECEIVER_BEAST_NICK=${RECEIVER_BEAST_NICK}
FKS_LOG_DIR=${APP_API}/logs
EOF
chmod 600 "${APP_API}/.env"

# ===== 2) 虚拟环境 + 依赖 =====
info "创建/更新 Python 虚拟环境"
python3 -m venv "${VENV_PATH}"
"${VENV_PATH}/bin/pip" install --upgrade pip -q
"${VENV_PATH}/bin/pip" install -r "${APP_API}/requirements.txt" -q
success "Python 依赖安装完成"

# ===== 3) 初始化数据库 =====
info "初始化数据库表结构"
cd "${APP_API}"
env $(grep -v '^#' .env | xargs) "${VENV_PATH}/bin/python" init_mysql_schema.py
success "数据库初始化完成"

# ===== 4) 构建后台前端 =====
info "构建后台前端（输出到 fksapi/admin/dist）"
cd "${APP_ADMIN}"
npm ci --silent
npm run build
success "后台前端构建完成"

# ===== 5) 创建必须目录 =====
mkdir -p "${APP_API}/logs" "${APP_API}/uploads/guarantee-proof" "${APP_API}/admin/dist"

# ===== 6) systemd 服务 =====
info "创建 systemd 服务: ${SERVICE_NAME}.service"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=FKS API Service
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${APP_API}
EnvironmentFile=${APP_API}/.env
ExecStart=${VENV_PATH}/bin/python recharge_verify_server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fks-api

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"
sleep 2
systemctl status "${SERVICE_NAME}" --no-pager || error "${SERVICE_NAME} 启动失败，请查看日志: journalctl -u ${SERVICE_NAME} -n 100"
success "后端服务启动成功"

# ===== 7) Nginx 反代配置 =====
info "写入 Nginx 站点配置"
cat > /etc/nginx/sites-available/fks <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 10m;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:5000;
    }

    location = / {
        return 302 /admin/;
    }
}
EOF

ln -sf /etc/nginx/sites-available/fks /etc/nginx/sites-enabled/fks
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
success "Nginx 配置已生效"

echo ""
success "仅后端部署完成"
echo "后台地址: http://你的服务器IP/admin/"
echo "健康检查: http://你的服务器IP/api/recharge/health"
echo "查看日志: journalctl -u ${SERVICE_NAME} -f"
