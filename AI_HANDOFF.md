# AI_HANDOFF

给任何新 AI 的“最小上下文”模板，减少 token 消耗，快速进入可修改状态。

## 1. 项目一句话

这是一个“Python 后端 + Vue 管理后台 + 微信小程序”的交易担保系统，核心业务是充值校验、担保撮合、钱包记账与推广奖励。

## 2. 先读这 5 个文件（不要全仓扫描）

1. `fksapi/recharge_verify_server.py`
2. `fksapi/db_mysql.py`
3. `fksapi/select_rockLog.py`
4. `fksAdmin/src/components/TokenManagePanel.vue`
5. `fksAdmin/src/views/DashboardView.vue`

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

## 5. 本地开发常用命令

```bash
# 后端
cd fksapi
python recharge_verify_server.py

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

