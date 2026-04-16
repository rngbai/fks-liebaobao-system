const DEFAULT_GROUP_QQ = '769851293'

Page({
  data: {
    groupQQ: DEFAULT_GROUP_QQ,
    detailBlocks: [
      {
        title: '群里能拿到什么',
        items: [
          '硬核攻略探讨：通关技巧、阵容搭配、带你少走弯路',
          '最新活动解析：活动资讯第一时间同步，福利不容易错过',
          '问题互助反馈：遇到卡关、异常、转入疑问都能一起交流'

        ]
      },
      {
        title: '我们的氛围',
        items: [
          '老带新，共成长：鼓励老玩家分享经验，带飞新玩家',
          '绿色纯净，专注游戏：严格拒绝广告刷屏和乱七八糟的外链',
          '文明和谐，拒绝争端：遵守交流规则，专注交易与玩法沟通'
        ]
      }
    ]
  },

  onLoad(options) {
    if (options.qq) {
      this.setData({ groupQQ: options.qq })
    }
  },

  copyGroupQQ() {
    wx.setClipboardData({
      data: this.data.groupQQ,
      success: () => {
        wx.showModal({
          title: '群号已复制',
          content: `请打开 QQ 搜索群号 ${this.data.groupQQ} 申请加入。`,
          showCancel: false,
          confirmText: '知道了'
        })
      }
    })
  },

  goBack() {
    wx.navigateBack({
      fail: () => {
        wx.switchTab({ url: '/pages/index/index' })
      }
    })
  }
})
