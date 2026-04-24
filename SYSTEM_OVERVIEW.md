# SYSTEM_OVERVIEW

本文件用于快速理解当前系统，方便迁移到其他 AI 工具时减少上下文输入和 token 消耗。

## 1. 系统结构

- `fksapi`：Python 后端（现已增加 FastAPI 入口，保留旧 HTTPServer 入口作为回滚兼容）
- `fksAdmin`：Vue3 管理后台（运营、审核、推广、Token 管理）
- `fksTradMini`：微信小程序（用户端）

请求主链路：

- 小程序/后台 -> `/api/*` -> `fksapi/fastapi_app.py` -> `fksapi/fastapi_service.py` / `fksapi/db_mysql.py`

## 2. 关键入口文件

- 新后端入口：`fksapi/fastapi_server.py`
- FastAPI 应用：`fksapi/fastapi_app.py`
- FastAPI 业务服务层：`fksapi/fastapi_service.py`
- 旧后端入口（兼容回滚）：`fksapi/recharge_verify_server.py`
- 数据与业务核心：`fksapi/db_mysql.py`
- 已拆出的业务域：
  - `fksapi/db_home.py`
  - `fksapi/db_promotion.py`
  - `fksapi/db_community.py`
  - `fksapi/db_wallet.py`
  - `fksapi/db_recharge.py`
  - `fksapi/db_transfer.py`
  - `fksapi/db_guarantee.py`
  - `fksapi/db_feedback.py`
  - `fksapi/db_config.py`
  - `fksapi/db_manage.py`
- 充值到账校验：`fksapi/select_rockLog.py`
- CW 扫码/Token 工具：`fksapi/saomagetCwtk.py`
- 后台 Token 管理面板：`fksAdmin/src/components/TokenManagePanel.vue`
- 后台总览面板：`fksAdmin/src/views/DashboardView.vue`

## 3. 当前核心功能

### 3.1 担保与充值

- 充值创建、到账校验、钱包记账
- 担保单撮合、确认、状态流转
- 后台可查看待处理队列

### 3.2 推广系统（已改为新规则）

- 二级分佣：L1=0.8，L2=0.2（每有效单）
- 拉新首单奖励：2 宝石
- 月阶梯奖励与 Top5 奖励
- 月结算接口已接入

### 3.3 社区名流

- 后台管理：增删改查 + 排序 + 启停
- 头像为上传文件（`/uploads/community-avatar/`）
- 小程序按分类与子标签读取展示

### 3.4 Token 管理（重点）

- 支持手动设置：`userId + token + tokenType`
- 支持扫码登录（CW）并自动写入配置
- 支持过期信息展示（JWT 可解析时）
- 充值校验按 `tokenType` 自动切换 UA（`fks` / `cw`）

### 3.5 经营总览

- 平台指标卡片
- 账户宝石余额支持实时查询按钮（走后端实时接口）

## 4. 重要业务约束

1. `tokenType=cw` 必须使用 CW UA；`tokenType=fks` 必须使用 FKS UA。
2. 小程序开发可放开校验；正式环境必须 HTTPS + 合法域名。
3. 后台前端变更必须重新 build 并更新 `fksapi/admin/dist`。
4. 后端 Python 改动需重启 `fks` 服务。

## 5. 常见问题快速定位

- 页面改了没生效：先确认当前连的是本地后端还是服务器后端
- 小程序看不到新数据：检查是否连对服务器、是否 HTTPS 被拦
- 扫码登录失败：先检查后台登录态，再看 `/api/manage/token-config/qr-start` 响应
- 充值校验失败：检查 token 是否过期、tokenType 与 UA 是否匹配

## 6. 给新 AI 的最小上下文

建议先让 AI 只读以下文件，不要全仓扫描：

1. `fksapi/recharge_verify_server.py`
2. `fksapi/db_mysql.py`
3. `fksapi/select_rockLog.py`
4. `fksAdmin/src/components/TokenManagePanel.vue`
5. `fksAdmin/src/views/DashboardView.vue`

如果要继续维护 FastAPI 结构，建议优先补读：

6. `fksapi/fastapi_app.py`
7. `fksapi/fastapi_shared.py`
8. `fksapi/routers/public_api.py`
9. `fksapi/routers/manage_api.py`
10. `fksapi/db_wallet.py`
11. `fksapi/db_recharge.py`
12. `fksapi/db_transfer.py`
13. `fksapi/db_guarantee.py`
14. `fksapi/db_feedback.py`
15. `fksapi/db_config.py`
16. `fksapi/db_manage.py`

