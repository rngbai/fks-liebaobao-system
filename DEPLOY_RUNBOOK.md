# DEPLOY_RUNBOOK

本文件说明 GitHub 同步与服务器部署流程，目标是稳定、可回溯、可快速回滚。

## 1. 环境约定

- 本地仓库根目录：`e:\猎宝保系统`
- 服务器项目目录：`/root/fks_project`
- 后端服务名：`fks`
- 后台访问路径：`http://<server>/admin/`

## 2. 日常发布（推荐标准流程）

### Step A: 本地自测

- 后端：确认本地 API 正常
- 前端：`fksAdmin` 页面功能正常

### Step B: 提交代码

在仓库根目录执行：

```bash
git status
git add .
git commit --trailer "Made-with: Cursor" -m "<清晰的变更说明>"
git push origin main
```

### Step C: 服务器同步

如果服务器已配置快速部署脚本，执行：

```bash
ssh root@<server_ip> /root/quick_deploy.sh
```

若没有脚本，则手动执行：

```bash
cd /root/fks_project
git pull origin main
systemctl restart fks
systemctl is-active fks
```

如果本次包含 `fksAdmin` 改动（Vue 管理端），请使用下面流程替代上面的简化命令：

```bash
cd /root/fks_project
git pull origin main
cd fksAdmin && npm run build
cd /root/fks_project
systemctl restart fks
systemctl is-active fks
```

### Step D: 发布后快速自检（避免“代码已更新但页面没变化”）

```bash
cd /root/fks_project
git log -1 --oneline
ls -lt /root/fks_project/fksapi/admin/dist/assets | head -n 5
```

检查要点：

- `git log -1` 必须是预期提交（例如：`52fb3a2`）
- `dist/assets` 的 `index-*.js` / `index-*.css` 时间应为本次发布时间
- 若提交已更新但页面仍是旧样式，优先怀疑未执行 `npm run build`

## 3. 前端与后端分别发布注意事项

### 3.1 仅后端改动（Python）

- 服务器只需 `git pull + restart fks`
- 不需要重新构建前端

### 3.2 包含后台前端改动（Vue）

- 必须构建：`cd fksAdmin && npm run build`
- `dist` 输出到 `fksapi/admin/dist`
- 再重启 `fks`

## 4. 健康检查

部署后建议检查：

```bash
systemctl status fks --no-pager
journalctl -u fks -n 80 --no-pager
curl -s http://127.0.0.1:5000/api/recharge/health
```

管理端检查：

- 打开 `/admin/`
- 刷新总览、Token 管理、社区名流等核心页面

## 5. 常见故障排查

### 5.1 页面是旧的

- 可能没 build 前端
- 可能 build 了但没同步到 `fksapi/admin/dist`
- 浏览器强刷（Ctrl+F5）
- 先执行 Step D 自检：确认提交号与 `dist/assets` 文件时间是否为最新
- 如本次包含 `fksAdmin` 改动，务必执行：`cd /root/fks_project/fksAdmin && npm run build`

### 5.2 接口返回 401 / 未登录

- 管理后台 token 失效，重新登录
- 服务重启后内存 session 会重建

### 5.3 小程序请求超时或 TLS 错误

- 开发工具临时可关闭校验
- 正式必须 HTTPS + 合法域名白名单

### 5.4 本地正常，服务器异常

- 检查 `.env` 配置是否一致
- 检查服务器数据库是否有对应数据
- 检查是否连错环境（127.0.0.1 vs 服务器）

## 6. 回滚策略

### 快速回滚到上一版本

```bash
cd /root/fks_project
git log --oneline -5
git reset --hard <稳定提交hash>
systemctl restart fks
```

注意：`reset --hard` 为高风险命令，仅在确认回滚时使用。

## 7. 现有脚本说明

- `deploy.sh`：全量部署脚本（初始化/安装环境）
- `backend_only_deploy.sh`：后端导向部署脚本
- `update.sh`：热更新脚本（保留 `.env` 与 uploads/logs）

建议长期使用：GitHub 提交 + `quick_deploy.sh` 快速上线。

