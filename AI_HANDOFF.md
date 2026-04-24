# AI_HANDOFF

给任何新 AI 的“最小上下文”模板，减少 token 消耗，快速进入可修改状态。

## 1. 项目一句话

这是一个“FastAPI 后端 + Vue 管理后台 + 微信小程序”的交易担保系统，核心业务是充值校验、担保撮合、钱包记账与推广奖励。

## 2. 先读这 5 个文件（不要全仓扫描）

1. `fksapi/fastapi_app.py`
2. `fksapi/fastapi_shared.py`
3. `fksapi/api_runtime.py`
4. `fksapi/api_game.py`
5. `fksapi/db_common.py`
6. `fksapi/routers/public_api.py`
7. `fksapi/routers/manage_api.py`
8. `fksapi/fastapi_service.py`
9. `fksapi/db_mysql.py`
10. `fksapi/db_home.py`
11. `fksapi/db_promotion.py`
12. `fksapi/db_community.py`
13. `fksapi/db_wallet.py`
14. `fksapi/db_recharge.py`
15. `fksapi/db_transfer.py`
16. `fksapi/db_guarantee.py`
17. `fksapi/db_feedback.py`
18. `fksapi/db_config.py`
19. `fksapi/db_manage.py`
20. `fksAdmin/src/views/DashboardView.vue`

## 3. 关键规则（必须遵守）

- `tokenType` 只允许：`fks` 或 `cw`
- 充值校验时 UA 必须匹配 token 类型：
  - `fks` -> 方块兽 UA
  - `cw` -> 潮玩宇宙 UA
- 后台前端变更必须 build 才会生效
- 后端 Python 变更必须重启服务才会生效

## 4. 常用路径

- 后端目录：`fksapi`
- 前端目录：`fksAdmin`
- 小程序目录：`fksTradMini`
- 管理后台静态输出：`fksapi/admin/dist`

## 4.1 固定连接信息（可直接用于部署）

> 仅限本项目内部使用，避免每次重复向用户询问。

- 服务器地址：`124.223.80.102`
- SSH 用户：`root`
- SSH 密码：`T9$xZ!4rW@7yU^2iO&5pQ*1sA`
- GitHub 仓库：`https://github.com/rngbai/fks-liebaobao-system`
- 默认分支：`main`
- 服务器项目目录：`/root/fks_project`
- 服务名：`fks`
- 线上后台地址：`http://124.223.80.102/admin/`
- 健康检查：`http://127.0.0.1:5000/api/recharge/health`

## 4.2 AI 默认发布动作（标准顺序）

1. 本地提交并推送：`git push origin main`
2. 服务器拉取：`cd /root/fks_project && git pull origin main`
3. 若包含 `fksAdmin` 改动：`cd /root/fks_project/fksAdmin && npm run build`
4. 重启服务：`systemctl restart fks && systemctl is-active fks`
5. 验证：`git log -1 --oneline`、健康检查、后台页面强刷

## 5. 本地开发常用命令

```bash
# 后端
cd fksapi
python fastapi_server.py

# 后台前端
cd fksAdmin
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:5000"; npm run dev

# 构建
cd fksAdmin
npm run build
```

## 6. 发布最短路径

```bash
git add .
git commit --trailer "Made-with: Cursor" -m "<message>"
git push origin main
ssh root@<server_ip> /root/quick_deploy.sh
```

## 7. 排错优先级（按顺序）

1. 是否连对环境（本地/服务器）
2. 是否 build 前端
3. 是否重启后端服务
4. 登录态是否失效（401）
5. token 是否过期、tokenType 是否匹配

## 7.1 近期高频坑位（优先检查）

- Token 管理支持“部分更新”：
  - `userId / userName / token / tokenType` 可单独修改
  - 扫码成功后通常仅需手动补 `userName`
- 扫码“实际成功但弹窗失败”：
  - 重点检查前端状态判断，不要只看弹窗文案
- 管理后台页面未更新：
  - 优先判断是否漏 `npm run build`
  - 检查 `fksapi/admin/dist/assets` 是否是最新时间
- 反馈管理 SQL 报缺字段（如 `scene`）：
  - 说明线上老库未升级；确认后端自动补列逻辑是否已执行
- 服务器 `git pull` 偶发失败：
  - 常见 443/TLS 网络抖动，默认做 2~3 次重试

## 8. 可直接粘贴给 AI 的提示词

```text
你正在维护一个三端系统：
- fksapi (Python API)
- fksAdmin (Vue3 admin)
- fksTradMini (WeChat mini-program)

请先读取：
1) fksapi/recharge_verify_server.py
2) fksapi/db_mysql.py
3) fksapi/select_rockLog.py
4) fksAdmin/src/components/TokenManagePanel.vue
5) fksAdmin/src/views/DashboardView.vue

注意：tokenType=cw 时必须使用 CW UA，tokenType=fks 使用 FKS UA。
请只做最小改动，优先保证可回滚和可部署。
```
