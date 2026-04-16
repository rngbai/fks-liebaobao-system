const app = getApp()

Page({
  data: {
    item: {},
    detailType: 'sell'
  },

  onLoad(options) {
    this.setData({ detailType: options.type || 'sell' })
    this.loadItem(options.id, options.type)
  },

  loadItem(id, type) {
    // 模拟数据
    const sellMock = {
      id, title: '出售 炎龙兽×10 精品',
      quantity: 10, price_per: 150,
      desc: '精品炎龙兽，全属性，可小刀，诚信交易',
      qq: '987654321', wechat: 'dragon_seller',
      create_time: '2026-04-13 08:30'
    }
    const buyMock = {
      id, title: '求购 火焰狮×3 高价收',
      quantity: 3, price_per: 500,
      desc: '急需火焰狮，有货联系我，价格好谈',
      qq: '111222333', wechat: 'hunter_x',
      create_time: '2026-04-13 07:00'
    }
    this.setData({ item: type === 'sell' ? sellMock : buyMock })

    // 实际接口:
    // app.request({
    //   url: `/api/market/${id}`,
    //   success: res => this.setData({ item: res.data })
    // })
  },

  copyContact(e) {
    const { val, label } = e.currentTarget.dataset
    wx.setClipboardData({
      data: val,
      success: () => wx.showToast({ title: `${label}已复制`, icon: 'success' })
    })
  },

  goGuarantee() {
    wx.switchTab({ url: '/pages/guarantee/guarantee' })
  }
})
