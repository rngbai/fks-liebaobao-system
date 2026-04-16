# AI 速读总览：`fksAdmin` / `fksapi` / `fksTradMini`

## 文档目的

这份文档是给 **其他 AI 工具或新接手的人** 看的速读说明，目标是：

- **先建立系统全貌**，避免一上来扫描全部源码导致大量 token 消耗。
- 快速判断：**该去哪个目录改、哪个模块已接后端、哪个模块还只是占位/模拟实现**。
- 给后续 AI 一个稳定的上下文入口，减少误判和重复阅读。

> 本文档只覆盖三个目录：`fksAdmin`、`fksapi`、`fksTradMini`。
> 其他目录如 `fksTrae`、`备份`、`小程序原生写法` 不在本文档范围内。

---

## 一句话总览

这是一个由 **微信小程序前端** + **Python 单体后端** + **Vue 后台管理端** 组成的交易系统，当前主业务围绕：

- **宝石转入**
- **宝石转出**
- **担保交易**
- **用户资料 / 钱包 / 推广 / 反馈**
- **后台运营管理**

三个目录的角色分别是：

- `fksTradMini`：**当前主要维护的小程序前端**。
- `fksapi`：**唯一核心后端**，提供 API、管理后台鉴权、静态资源托管、上传文件访问、MySQL 持久化。
- `fksAdmin`：**Vue3 管理后台前端**，编译后部署到 `fksapi/admin/dist`，由 Python 后端统一托管。

---

## 系统结构总图

```text
用户（微信小程序）
  -> fksTradMini
      -> app.js 统一 request 封装
      -> 调用 /api/*
          -> fksapi/recharge_verify_server.py
              -> db_mysql.py（MySQL 数据读写）
              -> select_rockLog.py（外部游戏日志校验）
              -> uploads/（图片上传）
              -> admin/dist（后台构建产物）

管理员（浏览器）
  -> fksAdmin（开发态）
      -> Vite dev server
      -> 代理 /api 到 Python 后端
  -> build 后输出到 fksapi/admin/dist
      -> 通过 /admin/ 访问
```

---

## 当前建议的阅读顺序（给 AI）

如果后续别的 AI 要继续接手，**先读本文，再按下面顺序按需读文件**：

1. `fksTradMini/app.js`
2. `fksapi/recharge_verify_server.py`
3. `fksapi/db_mysql.py`
4. `fksAdmin/src/lib/api.js`
5. 再按任务去读具体页面/组件

### 不要默认全量扫描的目录

- `fksTradMini/pages/*`：页面很多，但只有一部分已接真实接口。
- `fksAdmin/src/components/*`：后台组件多，但都围绕同一批 `/api/manage/*` 接口。
- `fksapi/uploads/*`：上传文件目录，不需要当源码看。

---

## 1. `fksTradMini` 说明

## 定位

原生微信小程序项目，是当前用户端主入口。

## 技术栈

- 原生微信小程序
- JS + WXML + WXSS
- 无额外前端框架
- 网络请求通过 `app.js` 统一封装

## 核心入口

- `app.json`：页面注册、tabBar 配置
- `app.js`：基础 URL、用户标识、统一请求、统一 loading 管理
- `utils/request.js`：轻量 request 转发
- `utils/guarantee.js`：担保单字段归一化、图片 URL 解析
- `utils/user.js`：用户是否已绑定方块兽 ID 的校验

## 运行方式

- 小程序直接通过 `app.js` 中的 `baseUrl` 请求后端
- 默认后端地址是本地 `127.0.0.1:5000`
- `app.js` 内部负责：
  - 读取/保存 `baseUrl`
  - 生成本地 `userKey`
  - 拼装请求头
  - 统一错误处理
  - 统一 loading 显隐

## 页面模块梳理

### 已接真实后端、可视为主链路模块

#### 首页与用户体系

- `pages/index`：首页内容、余额、推荐码绑定、首页运营位内容拉取
- `pages/mine`：我的页面，聚合资料、余额、统计
- `pages/profile`：用户资料编辑
- `pages/gems`：钱包流水 / 转入转出概览
- `pages/messages`：消息页（需单独看实现，本文未深挖）
- `pages/recommend`：我的推广数据
- `pages/feedback`：反馈列表与提交

#### 充值 / 转出 / 担保主业务

- `pages/recharge`：转入宝石，真实校验模式
- `pages/transfer`：转出申请，人工审核模式
- `pages/guarantee`：担保中心入口页
- `pages/guarantee-order`：担保单创建 / 查询 / 买家匹配 / 卖家确认
- `pages/guarantee-records`：担保记录列表

#### 管理功能（小程序内简化版）

- `pages/manage`：小程序内简化管理台，只覆盖部分管理动作，不是主要后台

### 仍有 mock / 占位逻辑、不是当前核心可信链路

以下页面目前 **不是完整真实业务链路**，里面仍有模拟数据或注释掉的“实际接口”代码：

- `pages/market`
- `pages/market-detail`
- `pages/market-publish`
- `pages/detail`
- `pages/publish`
- `pages/appeal`

这些模块目前更像历史原型页/占位页，**不要默认把它们当作当前正式流程的真实实现**。

## 小程序当前真实业务流

### 1）转入宝石

页面：`pages/recharge`

流程：

1. 创建转入订单 `/api/recharge/create`
2. 用户去游戏侧完成转入
3. 输入“时间后 4 位”做校验 `/api/recharge/verify`
4. 后端调用外部游戏日志接口核实真实交易
5. 校验成功后写入 MySQL 钱包余额和流水

特点：

- 有 10 分钟时效
- 支持取消订单
- 取消次数有限制
- 是当前系统里 **最完整的一条真业务链** 之一

### 2）转出宝石

页面：`pages/transfer`

流程：

1. 用户提交转出申请 `/api/transfer/create`
2. 后端锁定宝石，记录申请
3. 后台人工处理
4. 管理员点击完成或拒绝
5. 完成则记流水，拒绝则退回锁定资产

特点：

- 依赖用户先绑定 `beastId`
- 每日申请次数有限制
- 手续费按基点计算
- 是 **半自动 + 人工审核** 模式

### 3）担保交易

页面：`pages/guarantee`、`pages/guarantee-order`、`pages/guarantee-records`

当前真实流程：

1. 卖家创建担保单 `/api/guarantee/create`
2. 买家查询担保单 `/api/guarantee/detail`
3. 买家填写方块兽信息、昵称、说明、交易截图 `/api/guarantee/match`
4. 卖家核对后确认 `/api/guarantee/seller-confirm`
5. 系统自动结算给买家

特点：

- 不是后台手动放款，**已经改成系统自动到账**
- 买家截图上传走 `/api/upload/image`
- 订单状态流包括：待匹配 / 待卖家确认 / 已完成 / 申诉中

## 小程序请求与身份机制

### 用户身份

系统不是严格依赖微信 openid 当前完成所有逻辑，而是：

- 用 `local_user_key_v1` 持久化一个本地用户标识
- `app.js` 在请求头里带 `x-user-key`
- 后端据此建档 / 识别用户

这意味着：

- 目前更像“本地设备账户”体系
- `openid` 字段存在，但不是主标识链路
- 如果 AI 要改登录体系，需要先看后端 `get_or_create_user` 的设计，不要想当然按微信授权体系重构

## 小程序图片处理现状

### 已修复的点

担保截图此前有两个问题：

1. HTTP 图片地址不能直接被小程序 `image` 组件渲染
2. 多请求并发时 `showLoading / hideLoading` 不配对

当前已做处理：

- `app.js` 已改成 **loading 计数器**
- `utils/guarantee.js` 增加 `resolveDisplayImageUrl`
- `pages/guarantee-order` 会把 HTTP 图先下载成本地临时文件再显示
- 买家上传后，**提交保存服务端路径，预览优先显示本地临时图**

## 小程序里的高风险点

### 1）`README.md` 已明显过时

`fksTradMini/README.md` 描述的还是旧版担保逻辑与旧目录用法，**不能作为当前真实结构依据**。

### 2）市场与旧担保页仍是原型状态

如上所述，`market`、`detail`、`publish`、`appeal` 等页面仍有大量模拟逻辑。

### 3）小程序内 `pages/manage` 不是完整后台

它只是一个简化管理入口，接口少、能力不完整。真正运营管理应以 `fksAdmin` 为准。

---

## 2. `fksapi` 说明

## 定位

整个系统的 **唯一核心后端**。

它负责：

- 对小程序提供业务 API
- 对后台管理端提供 `/api/manage/*` 接口
- 托管后台静态资源 `/admin/`
- 提供图片上传与图片读取 `/uploads/*`
- 调用外部游戏日志接口进行充值校验
- 读写 MySQL

## 技术栈

- Python
- `ThreadingHTTPServer`
- `pymysql`
- 单文件主服务：`recharge_verify_server.py`
- 数据逻辑集中在 `db_mysql.py`

## 核心文件

- `recharge_verify_server.py`：HTTP 服务入口，几乎所有接口都在这里分发
- `db_mysql.py`：建表 + 主要数据库读写逻辑
- `select_rockLog.py`：外部游戏日志校验
- `config.py`：外部接口身份配置（敏感）
- `uploads/`：上传截图文件目录
- `admin/dist/`：后台前端构建产物目录

## 后端运行入口

运行入口在：

- `recharge_verify_server.py -> run_server()`

默认：

- host：`0.0.0.0`
- port：`5000`

## 管理后台静态托管

后端同时负责托管后台页面：

- `/admin/` -> `fksapi/admin/dist`
- 这就是为什么 `fksAdmin` build 后输出目标是这里

## 图片上传与访问

- 上传接口：`POST /api/upload/image`
- 上传目录：`fksapi/uploads/guarantee-proof`
- 访问路径：`/uploads/...`

注意：

- 后端返回的 `url` 当前是 **HTTP 地址**
- 同时也返回 `path`
- 小程序端现在优先依赖 `path` + 本地下载展示兼容
- 如果未来要彻底消除兼容逻辑，最根本的方式是把上传访问链路切到 HTTPS 或小程序可直接访问的合法域名

## 后端 API 概览

### 用户侧 GET 接口

- `/api/recharge/recent`
- `/api/recharge/state`
- `/api/user/profile`
- `/api/user/balance`
- `/api/user/wallet-records`
- `/api/transfer/state`
- `/api/guarantee/list`
- `/api/guarantee/detail`
- `/api/feedback/list`
- `/api/promotion/my`
- `/api/home/content`

### 用户侧 POST 接口

- `/api/promotion/bind`
- `/api/user/profile`
- `/api/feedback/create`
- `/api/upload/image`
- `/api/recharge/create`
- `/api/recharge/cancel`
- `/api/recharge/verify`
- `/api/guarantee/create`
- `/api/guarantee/match`
- `/api/transfer/create`
- `/api/guarantee/seller-confirm`

### 管理侧 GET 接口

- `/api/manage/auth-check`
- `/api/manage/home-content`
- `/api/manage/users`
- `/api/manage/promotions`
- `/api/manage/recharges`
- `/api/manage/guarantees`
- `/api/manage/feedbacks`
- `/api/manage/pending-guarantees`
- `/api/manage/transfer-requests`
- `/api/manage/pending-feedbacks`
- `/api/manage/dashboard`

### 管理侧 POST 接口

- `/api/manage/login`
- `/api/manage/logout`
- `/api/manage/users/import`
- `/api/manage/home-content`
- `/api/manage/transfer-request/complete`
- `/api/manage/transfer-request/reject`
- `/api/manage/feedback/update-status`

### 已废弃/保留提示接口

- `/api/manage/guarantee-transfer`
  - 现在只返回提示：**担保单已改为系统自动到账，无需后台手动转出**

## 数据库核心表

`db_mysql.py` 中可见主要表：

- `users`
- `user_wallets`
- `wallet_transactions`
- `recharge_orders`
- `guarantee_orders`
- `gem_transfer_requests`
- `market_listings`
- `user_feedback`
- `user_messages`
- `promotion_reward_logs`
- `app_configs`

### 表职责速记

- `users`：账户主表
- `user_wallets`：钱包余额、锁定资产、累计统计
- `wallet_transactions`：钱包流水
- `recharge_orders`：转入订单
- `guarantee_orders`：担保订单
- `gem_transfer_requests`：用户主动转出申请
- `market_listings`：市场挂单（但前端市场功能目前未完全接通）
- `user_feedback`：用户反馈
- `user_messages`：消息
- `promotion_reward_logs`：推广奖励日志
- `app_configs`：首页配置等可运营内容

## 外部依赖与校验链

`select_rockLog.py` 会调用外部游戏接口抓取交易日志，用于转入校验。

核心点：

- 依赖 `config.py` 中的外部身份配置
- 通过“金额 + 时间后四位 + 创建时间窗口”匹配真实交易记录
- 若 token 失效会抛出 `TokenExpiredError`

### 安全提醒

- `config.py` 内含敏感配置，不应该出现在任何共享给外部 AI 的上下文里
- 后台账号密码通过环境变量控制，代码里存在默认值语义，**应视为敏感并尽快改为正式环境变量**

---

## 3. `fksAdmin` 说明

## 定位

运营管理后台前端，服务于：

- 用户管理
- 推广管理
- 首页内容运营
- 充值记录查看
- 担保记录查看
- 待处理担保 / 转出 / 反馈队列
- 反馈状态流转

## 技术栈

- Vue 3
- Vite
- Element Plus
- Axios
- Vue Router

## 核心入口

- `package.json`
- `vite.config.js`
- `src/main.js`
- `src/router/index.js`
- `src/lib/api.js`
- `src/stores/auth.js`
- `src/views/LoginView.vue`
- `src/views/DashboardView.vue`

## 路由结构

后台只有两张主视图：

- `/login`
- `/dashboard`

并通过路由守卫判断是否带后台 token。

## 请求方式

`src/lib/api.js` 中：

- Axios `baseURL` 为空
- 默认请求当前域名下的 `/api/*`
- 自动在请求头中附带 `x-admin-token`
- 如果接口返回 401，会清理本地会话并触发“登录失效”事件

## 开发 / 构建方式

### 开发态

- `npm run dev`
- Vite 默认端口 5173
- `/api` 代理到 `VITE_API_PROXY_TARGET`，默认是 `http://127.0.0.1:5000`

### 构建态

- 输出目录：`../fksapi/admin/dist`
- 也就是直接把构建产物放进后端目录
- 最终由 Python 后端统一通过 `/admin/` 提供访问

## 后台主要模块

### 页面级

- `LoginView.vue`：后台登录
- `DashboardView.vue`：主工作台，集成多个管理分区

### 组件级核心模块

- `UserManagePanel.vue`：用户管理、用户导入
- `PromotionManagePanel.vue`：推广员与奖励统计
- `HomeContentManagePanel.vue`：首页轮播/推荐位/公告运营
- `RechargeTable.vue`：充值记录
- `GuaranteeTable.vue`：担保记录
- `FeedbackTable.vue`：反馈记录
- `DetailDrawer.vue`：详情抽屉
- `PaginationBar.vue`：分页
- `SidebarNav.vue`：侧栏导航

### Dashboard 分区定义

分区定义在 `src/constants/dashboard.js`：

- 经营总览
- 用户管理
- 推广管理
- 首页内容管理
- 担保待确认
- 用户转出申请
- 待处理反馈
- 充值记录
- 担保档案
- 反馈档案
- 近 7 天走势

## 后台与后端的对齐关系

后台基本就是 `/api/manage/*` 的可视化壳层。

### 典型对应

- 用户管理 -> `/api/manage/users`
- 用户导入 -> `/api/manage/users/import`
- 推广管理 -> `/api/manage/promotions`
- 首页内容管理 -> `/api/manage/home-content`
- 仪表盘 -> `/api/manage/dashboard`
- 待确认担保 -> `/api/manage/pending-guarantees`
- 用户转出申请 -> `/api/manage/transfer-requests`
- 反馈状态更新 -> `/api/manage/feedback/update-status`

因此如果后台出问题，**先查接口，再查组件**，不要反过来。

---

## 业务能力矩阵（现状判断）

| 模块 | 前端状态 | 后端状态 | 结论 |
|---|---|---|---|
| 用户资料 | 已接通 | 已接通 | 可用 |
| 钱包流水 | 已接通 | 已接通 | 可用 |
| 转入宝石 | 已接通 | 已接通 | 核心可用 |
| 转出申请 | 已接通 | 已接通 | 核心可用 |
| 担保交易 | 已接通 | 已接通 | 核心可用 |
| 推广体系 | 已接通 | 已接通 | 可用 |
| 反馈系统 | 已接通 | 已接通 | 可用 |
| 首页运营位 | 已接通 | 已接通 | 可用 |
| 后台管理 | 已接通 | 已接通 | 可用 |
| 市场大厅 | 前端多为 mock | 表结构存在但接口未成体系 | 未完成 |
| 老版订单详情/发布/申诉 | 前端 mock | 无对应正式链路 | 历史残留/占位 |

---

## 当前最重要的事实（给 AI 的判断规则）

### 1）真正的业务核心不是“市场”，而是“转入 / 转出 / 担保 / 推广 / 反馈”

如果需求模糊，默认优先看这几条主链。

### 2）担保已不是后台手动打款

旧思路可能会误以为后台要手动完成担保转出；现在不是。

**当前规则：**

- 用户主动“转出申请” -> 后台人工处理
- “担保单卖家确认完成” -> 系统自动结算给买家

### 3）`fksTradMini` 里有“新业务页”和“旧原型页”并存

后续 AI 不要因为看到 `detail`、`publish`、`appeal` 这些页面就误判整体系统还是旧版流程。

### 4）后台是前端壳，Python 后端才是真中心

很多问题最终都要落到：

- `recharge_verify_server.py`
- `db_mysql.py`

### 5）这套系统是单体，不是微服务

不要默认去找独立 auth 服务、文件服务、消息服务、队列服务。当前都集中在一个 Python 后端里。

---

## 已知问题 / 技术债

## 一类：已经接真实接口，但实现上仍需持续优化

### 1）图片访问仍是 HTTP 语义

现状：

- 后端上传返回 `http://.../uploads/...`
- 小程序不能直接渲染 HTTP 图
- 目前前端通过下载成本地临时文件做兼容

建议：

- 长期应切 HTTPS / 合法域名
- 短期继续保持前端兼容逻辑

### 2）账号体系偏“本地 userKey”

现状：

- 主标识更接近本地 `x-user-key`
- 不是标准微信登录态闭环

风险：

- 换设备、清缓存、用户迁移时会受影响
- 真正的账号归属逻辑不够强

### 3）后台敏感配置暴露风险

现状：

- `config.py` 含外部接口敏感配置
- 后台账号密码通过环境变量，但代码语义里有默认值

建议：

- 严格从文档和 AI 上下文中排除敏感值
- 统一改环境变量 / 配置中心

## 二类：仍未完成或明显是占位功能

### 1）市场模块未真正接通

涉及：

- `pages/market`
- `pages/market-detail`
- `pages/market-publish`

现状：

- 前端仍是 mock 数据 / 假成功
- 虽然数据库存在 `market_listings` 表，但当前业务链未成型

### 2）旧担保链页面仍残留

涉及：

- `pages/detail`
- `pages/publish`
- `pages/appeal`

现状：

- 仍是旧模型
- 与当前正式担保页 `guarantee-order` 并存
- 容易误导新 AI 或新开发者

建议：

- 后续要么接通重写，要么明确标记废弃

---

## 后续 AI 的工作建议

### 如果任务是“修用户端 bug”

优先读：

1. `fksTradMini/app.js`
2. 对应页面
3. `fksapi/recharge_verify_server.py`
4. 如涉及数据结构再看 `db_mysql.py`

### 如果任务是“改后台管理”

优先读：

1. `fksAdmin/src/views/DashboardView.vue`
2. 对应 `src/components/*.vue`
3. `fksAdmin/src/lib/api.js`
4. 对应 `/api/manage/*` 后端实现

### 如果任务是“改接口 / 改业务规则”

优先读：

1. `fksapi/recharge_verify_server.py`
2. `fksapi/db_mysql.py`
3. 对应前端页面

### 如果任务是“继续补全未完成模块”

建议优先级：

1. `market` 全链路接通
2. `appeal` 真接口化
3. 清理旧版 `detail/publish` 页面歧义
4. 完善消息系统
5. 统一账号身份体系

---

## 建议给其他 AI 的使用提示词

可以把下面这段直接复制给其他 AI：

```text
先阅读项目根目录下的 `AI速读_系统总览_fksAdmin_fksapi_fksTradMini.md`，不要先全量扫描源码。
本次只关注 `fksAdmin`、`fksapi`、`fksTradMini` 三个目录。
请先根据文档判断本次需求属于：小程序前端、Python 后端、还是后台管理端；
再只读取与该任务直接相关的 3~8 个文件，不要默认遍历全部 pages 或全部组件。
注意：
1. 当前真实主链路是 转入 / 转出 / 担保 / 推广 / 反馈；
2. `market`、`detail`、`publish`、`appeal` 等部分页面仍含 mock 或旧逻辑；
3. 担保单已改为系统自动到账，不是后台手动转出；
4. 不要输出或扩散 `config.py` 等敏感配置内容。
```

---

## 最后结论

如果只记三句话：

1. **当前真正的正式系统是：`fksTradMini` + `fksapi` + `fksAdmin`。**
2. **业务核心是转入、转出、担保、推广、反馈；市场模块仍未完全成型。**
3. **真正的业务中心在 `fksapi`，前后台基本都是围绕它组织的。**
