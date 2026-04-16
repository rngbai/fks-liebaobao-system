#!/usr/bin/env bash
# ============================================================
# 方块兽担保系统 —— Ubuntu 服务器一键部署脚本
# 适用系统: Ubuntu 22.04 LTS / 24.04 LTS
# 使用方式:
#   chmod +x deploy.sh
#   sudo bash deploy.sh
# ============================================================
set -euo pipefail

# ===== 颜色输出 =====
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ===== 基础检查 =====
[[ $EUID -ne 0 ]] && error "请以 root 或 sudo 运行此脚本"

UBUNTU_VERSION=$(lsb_release -rs 2>/dev/null || echo "0")
info "检测到 Ubuntu ${UBUNTU_VERSION}"

# ===== 可配置变量（按需修改） =====
APP_USER="fks"
APP_DIR="/opt/fks"
FKSAPI_DIR="${APP_DIR}/fksapi"
FKSADMIN_DIR="${APP_DIR}/fksAdmin"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="fks"
DOMAIN=""          # 留空跳过 SSL 申请，填写后自动配置 HTTPS

PYTHON_VER="3.11.5"
PYTHON_MIN="3.10"
USE_SOURCE_PYTHON="${USE_SOURCE_PYTHON:-false}"
USE_MYSQL_OFFICIAL_REPO="${USE_MYSQL_OFFICIAL_REPO:-false}"
NODE_MIN="20"
MYSQL_DB="fks_trade"
MYSQL_USER="fks_user"
MYSQL_DEFAULT_APP_PASS="1L0v3c4ts@ndd0gs"

# ===== 读取预配置文件（deploy.conf） =====
CONF_FILE="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/deploy.conf"
if [[ -f "$CONF_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$CONF_FILE"
    info "已读取预配置文件: $CONF_FILE"
    # 从配置文件加载到对应变量（若文件里已赋值则直接使用）
    DOMAIN="${DOMAIN:-}"
    MYSQL_ROOT_PASS="${MYSQL_ROOT_PASS:-}"
    MYSQL_APP_PASS="${MYSQL_APP_PASS:-${MYSQL_DEFAULT_APP_PASS}}"
    ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
    ADMIN_PASS="${ADMIN_PASS:-}"
    GAME_USER_ID="${GAME_USER_ID:-9100503}"
    GAME_TOKEN="${GAME_TOKEN:-}"
fi

# ===== 交互式补全（deploy.conf 里留空的项才会提示输入） =====
echo ""
echo "============================================================"
echo "  方块兽担保系统 部署向导"
echo "============================================================"

prompt_input() {
    local var_name=$1 prompt=$2 default=$3 secret=${4:-false}
    local value=""
    if [[ -n "$default" ]]; then
        read -rp "${prompt} [${default}]: " value
        value="${value:-$default}"
    elif [[ "$secret" == "true" ]]; then
        read -rsp "${prompt}: " value
        echo ""
    else
        read -rp "${prompt}: " value
    fi
    printf -v "$var_name" '%s' "$value"
}

# 仅在对应值为空时才提示输入
[[ -z "${DOMAIN+x}" ]]          && prompt_input DOMAIN          "请输入你的域名（留空则跳过 HTTPS）" ""
[[ -z "$MYSQL_ROOT_PASS" ]]     && prompt_input MYSQL_ROOT_PASS "MySQL root 密码" "" true
[[ -z "$MYSQL_APP_PASS" ]]      && MYSQL_APP_PASS="${MYSQL_DEFAULT_APP_PASS}" && \
                                   prompt_input MYSQL_APP_PASS  "数据库应用账号密码" "${MYSQL_DEFAULT_APP_PASS}"
[[ -z "$ADMIN_USERNAME" ]]      && prompt_input ADMIN_USERNAME  "后台管理员账号" "admin"
[[ -z "$ADMIN_PASS" ]]          && prompt_input ADMIN_PASS      "后台管理员密码（至少8位）" "" true
[[ -z "$GAME_USER_ID" ]]        && prompt_input GAME_USER_ID    "游戏 userId" "9100503"
[[ -z "$GAME_TOKEN" ]]          && prompt_input GAME_TOKEN      "游戏 Token（JWT，可部署后在后台管理页面填写）" ""

# 密码长度校验
[[ ${#ADMIN_PASS} -lt 8 ]] && error "后台密码至少需要8位"

echo ""
info "配置确认完毕，开始安装..."
info "服务器 IP: $(hostname -I | awk '{print $1}' 2>/dev/null || echo '未知')"
info "域名: ${DOMAIN:-（未配置，使用 IP 直接访问）}"
echo ""

# ===== 1. 系统更新 & 基础工具 =====
info "步骤 1/9 — 更新系统软件包"
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget git unzip build-essential \
    software-properties-common ca-certificates gnupg \
    lsb-release ufw fail2ban
success "基础工具安装完成"

# ===== 2. Python 运行环境 =====
if [[ "${USE_SOURCE_PYTHON}" == "true" ]]; then
    info "步骤 2/9 — 编译安装 Python ${PYTHON_VER}（已启用源码模式）"

    apt-get install -y -qq \
        build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
        libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev \
        liblzma-dev tk-dev uuid-dev

    PY_BIN="/usr/local/bin/python3.11"
    if [[ -x "$PY_BIN" ]]; then
        info "Python ${PYTHON_VER} 已存在，跳过编译"
    else
        info "下载 Python ${PYTHON_VER} 源码..."
        cd /tmp
        PY_TARBALL="Python-${PYTHON_VER}.tgz"
        PY_URLS=(
            "https://www.python.org/ftp/python/${PYTHON_VER}/${PY_TARBALL}"
            "https://mirrors.tuna.tsinghua.edu.cn/python/${PYTHON_VER}/${PY_TARBALL}"
            "https://mirrors.aliyun.com/python-release/source/${PY_TARBALL}"
            "https://mirrors.ustc.edu.cn/python/${PYTHON_VER}/${PY_TARBALL}"
        )
        DOWNLOADED=false
        for url in "${PY_URLS[@]}"; do
            info "尝试下载: ${url}"
            if curl -fL --connect-timeout 10 --max-time 600 -o "${PY_TARBALL}" "${url}"; then
                DOWNLOADED=true
                break
            else
                warn "下载失败，切换下一个源..."
                rm -f "${PY_TARBALL}"
            fi
        done
        if [[ "${DOWNLOADED}" != "true" ]]; then
            error "Python 源码下载失败，请检查网络或手动下载 ${PY_TARBALL} 到 /tmp 后重试"
        fi
        tar -xf "Python-${PYTHON_VER}.tgz"
        cd "Python-${PYTHON_VER}"
        info "配置并编译（约需 3-5 分钟）..."
        ./configure --enable-optimizations --with-lto --quiet
        make -j"$(nproc)" --quiet
        make altinstall --quiet
        cd /tmp && rm -rf "Python-${PYTHON_VER}" "Python-${PYTHON_VER}.tgz"
    fi

    ln -sf /usr/local/bin/python3.11 /usr/local/bin/python3
    ln -sf /usr/local/bin/pip3.11    /usr/local/bin/pip3
    PYTHON_CMD="/usr/local/bin/python3.11"
else
    info "步骤 2/9 — 安装 Python 运行环境（APT 模式，推荐）"
    apt-get install -y -qq python3 python3-pip python3-venv python3-dev
    PYTHON_CMD="$(command -v python3)"
fi

PYVER=$(${PYTHON_CMD} -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
info "Python 版本: ${PYVER}"
${PYTHON_CMD} -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ 必需'" \
    || error "Python 版本过低，请升级到 3.10+"
success "Python ${PYVER} 就绪"

# ===== 3. Node.js =====
info "步骤 3/9 — 安装 Node.js ${NODE_MIN}+"
if ! command -v node &>/dev/null || [[ $(node -v | tr -d 'v' | cut -d. -f1) -lt $NODE_MIN ]]; then
    curl -fsSL https://deb.nodesource.com/setup_${NODE_MIN}.x | bash - >/dev/null
    apt-get install -y -qq nodejs
fi
NODE_VER=$(node -v)
info "Node.js 版本: ${NODE_VER}"
success "Node.js 就绪"

# ===== 4. MySQL 8.0 =====
info "步骤 4/9 — 安装 & 配置 MySQL 8.0"
if ! command -v mysql &>/dev/null; then
    if [[ "${USE_MYSQL_OFFICIAL_REPO}" == "true" ]]; then
        info "已启用官方仓库模式：添加 MySQL 8.0 官方 APT 源..."
        cd /tmp
        wget -q https://dev.mysql.com/get/mysql-apt-config_0.8.32-1_all.deb
        # 非交互模式预配置选择 mysql-8.0
        DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.32-1_all.deb <<< $'1\n1\n1\n4\n'
        rm -f mysql-apt-config_0.8.32-1_all.deb
        apt-get update -qq
    else
        info "使用 Ubuntu 官方仓库安装 MySQL（更稳定，推荐）"
    fi

    # 预设 root 密码，避免交互弹窗
    debconf-set-selections <<< "mysql-server mysql-server/root_password password ${MYSQL_ROOT_PASS}"
    debconf-set-selections <<< "mysql-server mysql-server/root_password_again password ${MYSQL_ROOT_PASS}"
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mysql-server
    systemctl enable --now mysql

    # 安全加固
    mysql -uroot -p"${MYSQL_ROOT_PASS}" -e "DELETE FROM mysql.user WHERE User='';" 2>/dev/null || true
    mysql -uroot -p"${MYSQL_ROOT_PASS}" -e "DROP DATABASE IF EXISTS test;" 2>/dev/null || true
    mysql -uroot -p"${MYSQL_ROOT_PASS}" -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASS}';" 2>/dev/null || true
    mysql -uroot -p"${MYSQL_ROOT_PASS}" -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    info "MySQL $(mysql --version | awk '{print $3}') 安装完成"
else
    info "MySQL 已安装，跳过安装步骤"
fi

# 创建数据库和应用账号
mysql -uroot -p"${MYSQL_ROOT_PASS}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DB}\`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'localhost' IDENTIFIED BY '${MYSQL_APP_PASS}';
GRANT ALL PRIVILEGES ON \`${MYSQL_DB}\`.* TO '${MYSQL_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL
success "MySQL 数据库 ${MYSQL_DB} & 用户 ${MYSQL_USER} 就绪"

# ===== 5. Nginx =====
info "步骤 5/9 — 安装 Nginx"
apt-get install -y -qq nginx
systemctl enable --now nginx
success "Nginx 就绪"

# ===== 6. 创建应用用户和目录 =====
info "步骤 6/9 — 创建应用目录和系统用户"
if ! id "${APP_USER}" &>/dev/null; then
    useradd -r -s /usr/sbin/nologin -d "${APP_DIR}" "${APP_USER}"
fi
mkdir -p "${FKSAPI_DIR}" "${FKSADMIN_DIR}" "${APP_DIR}/venv"
success "目录 ${APP_DIR} 就绪"

# ===== 7. 部署代码 =====
info "步骤 7/9 — 部署应用代码"

# 检查代码是否已在当前目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "${SCRIPT_DIR}/fksapi" && -d "${SCRIPT_DIR}/fksAdmin" ]]; then
    info "检测到源码目录，直接复制..."
    rsync -a --exclude='*.pyc' --exclude='__pycache__' \
          --exclude='.env' --exclude='admin/dist' \
          "${SCRIPT_DIR}/fksapi/" "${FKSAPI_DIR}/"
    rsync -a --exclude='node_modules' --exclude='dist' \
          "${SCRIPT_DIR}/fksAdmin/" "${FKSADMIN_DIR}/"
else
    warn "未找到源码目录，请手动将 fksapi/ 和 fksAdmin/ 上传到服务器后重新运行此脚本。"
    warn "上传方法: scp -r fksapi fksAdmin root@服务器IP:${APP_DIR}/"
    exit 1
fi

# 写入 .env
cat > "${FKSAPI_DIR}/.env" <<ENV
RECHARGE_VERIFY_HOST=127.0.0.1
RECHARGE_VERIFY_PORT=5000
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=${MYSQL_USER}
MYSQL_PASSWORD=${MYSQL_APP_PASS}
MYSQL_DATABASE=${MYSQL_DB}
FKS_ADMIN_USERNAME=${ADMIN_USERNAME}
FKS_ADMIN_PASSWORD=${ADMIN_PASS}
FKS_GAME_USER_ID=${GAME_USER_ID}
FKS_GAME_TOKEN=${GAME_TOKEN}
RECEIVER_BEAST_NICK=面板小助手
FKS_LOG_DIR=${FKSAPI_DIR}/logs
ENV
chmod 600 "${FKSAPI_DIR}/.env"

# 创建必要目录
mkdir -p "${FKSAPI_DIR}/uploads/guarantee-proof" "${FKSAPI_DIR}/logs" "${FKSAPI_DIR}/admin/dist"

# ===== 8. Python 虚拟环境 & 依赖 =====
info "步骤 8/9 — 构建 Python 虚拟环境（${PYVER}）"
${PYTHON_CMD} -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip -q
"${VENV_DIR}/bin/pip" install -r "${FKSAPI_DIR}/requirements.txt" -q
success "Python 依赖安装完成"

# 初始化数据库表结构
info "初始化数据库表结构..."
cd "${FKSAPI_DIR}"
# 临时加载环境变量执行初始化
env $(cat .env | grep -v '^#' | xargs) "${VENV_DIR}/bin/python" init_mysql_schema.py
success "数据库表结构初始化完成"

# ===== 构建前端 =====
info "构建 Vue 后台管理前端..."
cd "${FKSADMIN_DIR}"
npm ci --silent
npm run build
success "前端构建完成，产物已输出到 ${FKSAPI_DIR}/admin/dist"

# ===== 9. systemd 服务 =====
info "步骤 9/9 — 配置 systemd 服务"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<SERVICE
[Unit]
Description=方块兽担保系统后端 API
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${FKSAPI_DIR}
EnvironmentFile=${FKSAPI_DIR}/.env
ExecStart=${VENV_DIR}/bin/python recharge_verify_server.py
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=30
StartLimitBurst=5
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${FKSAPI_DIR}/uploads ${FKSAPI_DIR}/logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fks-api

[Install]
WantedBy=multi-user.target
SERVICE

# 设置文件权限
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
chmod 750 "${FKSAPI_DIR}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"
sleep 2
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    success "fks.service 启动成功"
else
    warn "服务启动失败，查看日志: journalctl -u ${SERVICE_NAME} -n 50"
fi

# ===== Nginx 配置 =====
info "配置 Nginx 反向代理..."
if [[ -n "$DOMAIN" ]]; then
    # HTTPS 配置（有域名）
    apt-get install -y -qq certbot python3-certbot-nginx
    cat > "/etc/nginx/sites-available/fks" <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl http2;
    server_name ${DOMAIN};
    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    client_max_body_size 10m;
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 30s;
    }
    location /admin/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    location /uploads/ {
        proxy_pass http://127.0.0.1:5000;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
    location = / { return 302 /admin/; }
}
NGINX
    ln -sf /etc/nginx/sites-available/fks /etc/nginx/sites-enabled/fks
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    # 申请 SSL 证书
    mkdir -p /var/www/certbot
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "admin@${DOMAIN}" || \
        warn "SSL 证书申请失败，请手动运行: certbot --nginx -d ${DOMAIN}"
    # 设置自动续期
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -
else
    # HTTP 配置（无域名，用 IP 直接访问，适合临时测试）
    cat > "/etc/nginx/sites-available/fks" <<NGINX
server {
    listen 80 default_server;
    client_max_body_size 10m;
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 30s;
    }
    location /admin/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
    }
    location /uploads/ {
        proxy_pass http://127.0.0.1:5000;
    }
    location = / { return 302 /admin/; }
}
NGINX
    ln -sf /etc/nginx/sites-available/fks /etc/nginx/sites-enabled/fks
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    warn "未配置域名，使用 HTTP（仅用于调试，微信小程序需要 HTTPS）"
fi
success "Nginx 配置完成"

# ===== 防火墙 =====
info "配置 UFW 防火墙..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
# 不暴露 5000 端口到外网，仅内部 Nginx 访问
ufw deny 5000/tcp 2>/dev/null || true
success "防火墙配置完成"

# ===== fail2ban =====
info "启用 fail2ban 防暴力破解..."
systemctl enable --now fail2ban
success "fail2ban 已启动"

# ===== 完成 =====
echo ""
echo "============================================================"
echo -e "  ${GREEN}✅ 部署完成！${NC}"
echo "============================================================"
echo ""
if [[ -n "$DOMAIN" ]]; then
    echo -e "  后台管理地址: ${CYAN}https://${DOMAIN}/admin/${NC}"
    echo -e "  API 地址:     ${CYAN}https://${DOMAIN}/api/${NC}"
    echo ""
    echo "  微信小程序 app.js 的 baseUrl 请设置为:"
    echo -e "  ${CYAN}https://${DOMAIN}${NC}"
else
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo -e "  后台管理地址: ${YELLOW}http://${SERVER_IP}/admin/${NC}  （需配置域名才能用于正式环境）"
    echo ""
    echo "  ⚠️  微信小程序必须用 HTTPS，请尽快绑定域名并申请 SSL 证书"
    echo "     配置完域名后: sudo certbot --nginx -d 你的域名"
fi
echo ""
echo "  常用运维命令:"
echo "    查看服务状态:  sudo systemctl status fks"
echo "    查看实时日志:  sudo journalctl -u fks -f"
echo "    重启服务:      sudo systemctl restart fks"
echo "    查看应用日志:  tail -f ${FKSAPI_DIR}/logs/app.log"
echo "    更新代码后:    sudo bash ${SCRIPT_DIR}/update.sh"
echo ""
echo "  ⚠️  重要提醒:"
echo "    1. 游戏 Token 有效期约 30 天，到期后请更新 .env 中的 FKS_GAME_TOKEN"
echo "    2. 更新 Token 后运行: sudo systemctl restart fks"
echo "    3. .env 文件含敏感信息，已设置 600 权限，请勿暴露"
echo "============================================================"
