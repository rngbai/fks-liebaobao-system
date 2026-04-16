const app = getApp()

Page({
  data: {
    marketTab: 'sell',
    sellList: [],
    buyList: []
  },

  onLoad() {
    this.loadMarket()
  },

  onShow() {
    this.loadMarket()
  },

  onPullDownRefresh() {
    this.loadMarket(() => wx.stopPullDownRefresh())
  },

  loadMarket(callback) {
    const sellList = [
      { id: 'MKT_S001', title: '出售 炎龙兽×10 精品', quantity: 10, price_per: 150, seller_nick: 'DragonSlayer', create_time: '2026-04-13 08:30' },
      { id: 'MKT_S002', title: '出售 冰晶狼×5 完美属性', quantity: 5, price_per: 300, seller_nick: '星辰大主宰', create_time: '2026-04-12 20:00' },
      { id: 'MKT_S003', title: '出售 宝石兽×20 打折出', quantity: 20, price_per: 80, seller_nick: '暗影猎手', create_time: '2026-04-12 15:00' }
    ]
    const buyList = [
      { id: 'MKT_B001', title: '求购 火焰狮×3 高价收', quantity: 3, price_per: 500, buyer_nick: 'HunterX', create_time: '2026-04-13 07:00' },
      { id: 'MKT_B002', title: '求购 雷霆鹰×1 急需', quantity: 1, price_per: 800, buyer_nick: '玩家NightOwl', create_time: '2026-04-12 18:00' }
    ]
    this.setData({ sellList, buyList })
    callback && callback()

    // 实际接口:
    // app.request({
    //   url: '/api/market/list',
    //   success: res => {
    //     this.setData({ sellList: res.data.sell, buyList: res.data.buy })
    //     callback && callback()
    //   }
    // })
  },

  syncMarketView(nextTab) {
    const marketTab = nextTab === 'buy' ? 'buy' : 'sell'
    this.setData({
      marketTab,
      sellTabClass: marketTab === 'sell' ? 'active' : '',
      buyTabClass: marketTab === 'buy' ? 'active' : '',
      publishActionText: marketTab === 'sell' ? '出售' : '求购'
    })
  },

  switchTab(e) {
    this.syncMarketView(e.currentTarget.dataset.tab)
  },


  goPublish() {
    wx.navigateTo({ url: `/pages/market-publish/market-publish?type=${this.data.marketTab}` })
  },

  goDetail(e) {
    const { id, type } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/market-detail/market-detail?id=${id}&type=${type}` })
  }
})
