const app = getApp()

Page({
  data: {
    order: {},
    isSeller: false,
    isBuyer: false,
    buyerGameId: '',
    statusTitle: ['待卖家押金', '待买家确认', '交易完成', '申诉处理中'],
    statusDesc: [
      '卖家需先押入约定宝石，交易才能开始',
      '买家请确认已收到宝石，确认后释放押金',
      '交易已圆满完成',
      '平台正在审核申诉材料'
    ],
    statusIcon: ['⏳', '🔄', '✅', '⚠️']
  },

  onLoad(options) {
    const { id } = options
    this.loadOrder(id)
  },

  loadOrder(id) {
    // 模拟数据，实际替换为接口
    const mockOrder = {
      id: id || 'GT20260412001',
      seller_openid: 'oxxx002',
      buyer_openid: '',
      game_id_seller: 'DragonSlayer',
      game_id_buyer: '',
      back_gem: 5000,
      fee_gem: 200,
      total_gem: 5200,
      status: 0,
      screenshot: '',   // 实际填截图url
      create_time: '2026-04-12 10:30',
      confirm_time: ''
    }

    const myOpenid = app.globalData.openid || 'oxxx002'  // 测试用
    this.setData({
      order: mockOrder,
      isSeller: mockOrder.seller_openid === myOpenid,
      isBuyer: mockOrder.buyer_openid === myOpenid
    })

    // 实际接口:
    // app.request({
    //   url: `/api/orders/${id}`,
    //   success: res => {
    //     const order = res.data
    //     const myOpenid = app.globalData.openid
    //     this.setData({
    //       order,
    //       isSeller: order.seller_openid === myOpenid,
    //       isBuyer: order.buyer_openid === myOpenid
    //     })
    //   }
    // })
  },

  copyOrderId() {
    wx.setClipboardData({
      data: this.data.order.id,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    })
  },

  previewScreenshot() {
    wx.previewImage({
      urls: [this.data.order.screenshot],
      current: this.data.order.screenshot
    })
  },

  onBuyerIdInput(e) {
    this.setData({ buyerGameId: e.detail.value })
  },

  // 买家接单
  acceptOrder() {
    if (!this.data.buyerGameId.trim()) {
      wx.showToast({ title: '请输入游戏ID', icon: 'none' })
      return
    }
    wx.showModal({
      title: '确认接单',
      content: `您的游戏ID：${this.data.buyerGameId}\n确认后卖家将开始转账流程`,
      confirmText: '确认接单',
      success: res => {
        if (!res.confirm) return
        wx.showLoading({ title: '接单中...' })
        // app.request({ url: `/api/orders/${this.data.order.id}/accept`, method: 'POST', data: { game_id_buyer: this.data.buyerGameId } })
        setTimeout(() => {
          wx.hideLoading()
          const order = { ...this.data.order, status: 1, game_id_buyer: this.data.buyerGameId, buyer_openid: app.globalData.openid }
          this.setData({ order, isBuyer: true })
          wx.showToast({ title: '接单成功', icon: 'success' })
        }, 600)
      }
    })
  },

  // 买家确认收货
  confirmReceived() {
    wx.showModal({
      title: '⚠️ 谨慎操作',
      content: '确认收到宝石后，押金将释放给卖家（扣除手续费），此操作不可撤销！',
      confirmText: '已收到，确认',
      confirmColor: '#4CAF50',
      success: res => {
        if (!res.confirm) return
        wx.showLoading({ title: '确认中...' })
        // app.request({ url: `/api/orders/${this.data.order.id}/confirm`, method: 'POST' })
        setTimeout(() => {
          wx.hideLoading()
          const order = { ...this.data.order, status: 2, confirm_time: new Date().toLocaleString() }
          this.setData({ order })
          wx.showToast({ title: '交易完成！', icon: 'success' })
        }, 600)
      }
    })
  },

  // 申诉
  goAppeal() {
    wx.navigateTo({ url: `/pages/appeal/appeal?id=${this.data.order.id}` })
  }
})
