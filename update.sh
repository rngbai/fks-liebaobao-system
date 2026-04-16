#!/usr/bin/env bash
# ============================================================
# 方块兽担保系统 —— 代码热更新脚本
# 适合代码修改后快速重新部署，不会重置数据库和配置
# 使用: sudo bash update.sh
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "请以 root 或 sudo 运行此脚本"

APP_DIR="/opt/fks"
FKSAPI_DIR="${APP_DIR}/fksapi"
FKSADMIN_DIR="${APP_DIR}/fksAdmin"
VENV_DIR="${APP_DIR}/venv"
APP_USER="fks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info "开始更新代码..."

# 同步后端代码（保留 .env、uploads、logs）
rsync -a --exclude='*.pyc' --exclude='__pycache__' \
      --exclude='.env' --exclude='logs' --exclude='uploads' \
      --exclude='admin/dist' \
      "${SCRIPT_DIR}/fksapi/" "${FKSAPI_DIR}/"

# 同步前端代码
rsync -a --exclude='node_modules' --exclude='dist' \
      "${SCRIPT_DIR}/fksAdmin/" "${FKSADMIN_DIR}/"

# 更新 Python 依赖（如有新增）
info "更新 Python 依赖..."
"${VENV_DIR}/bin/pip" install -r "${FKSAPI_DIR}/requirements.txt" -q

# 重新构建前端
info "重新构建 Vue 前端..."
cd "${FKSADMIN_DIR}"
npm ci --silent
npm run build
success "前端构建完成"

# 修复权限
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

# 重启服务
info "重启后端服务..."
systemctl restart fks
sleep 2
if systemctl is-active --quiet fks; then
    success "服务重启成功"
else
    echo "服务重启失败，查看日志: journalctl -u fks -n 50"
fi

success "更新完成！"
