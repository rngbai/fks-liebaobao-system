# 游戏货币交易担保小程序

## 功能概览

| 页面 | 功能 |
|------|------|
| 交易市场（首页） | 卖单/买单切换、搜索、状态筛选、担保单列表 |
| 发布担保单 | 填写游戏ID、设置宝石数量、上传截图、发布 |
| 担保单详情 | 状态流转、买家接单、确认收货、申诉入口 |
| 我的 | 个人信息、统计、我的卖单/买单 |
| 申诉 | 选择原因、填写描述、上传截图 |

## 担保单状态流转

```
0: 待卖家转账  →  1: 待买家确认  →  2: 已完成
                              ↘  3: 已申诉
```

## 数据结构

```js
Order {
  id            // 订单号 GT+时间戳
  seller_openid // 卖家微信openid
  buyer_openid  // 买家微信openid（可选）
  game_id_seller // 卖家游戏ID
  game_id_buyer  // 买家游戏ID（可选）
  back_gem       // 约定返还宝石
  fee_gem        // 手续费
  total_gem      // 卖家需押总额 = back_gem + fee_gem
  status         // 0/1/2/3
  screenshot     // 截图url
  create_time
  confirm_time
}
```

## 对接后端步骤

1. 修改 `app.js` 中的 `baseUrl`
2. 在 `app.js` 的 `onLaunch` 中发送 `code` 换取 `openid`
3. 替换各页面 JS 中标注 `// 实际接口` 的注释部分

## 开发环境

- 微信开发者工具导入 `d:/codewx` 目录
- 在 `project.config.json` 中填入你的 `appid`
- `assets/icons/` 目录放入 tabBar 图标（trade.png / mine.png 等）
