const { requestApi: sendRequest } = require('../../utils/request')
const { ensureBeastId: ensureBeastIdGuard } = require('../../utils/user')


Page({
  data: {
    balance: 0,
    lockedGems: 0,
    totalRecharged: 0,
    totalSpent: 0,
    totalEarned: 0,
    records: [],
    userInfo: {},
    pendingTransfer: null,
    transferHistory: []
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  loadData() {
    sendRequest({
      url: '/api/user/wallet-records',
      showLoading: false,
      showError: false
    }).then(payload => {

      const data = payload.data || {}
      this.setData({
        balance: Number(data.balance || 0),
        lockedGems: Number(data.lockedGems || 0),
        totalRecharged: Number(data.totalRecharged || 0),
        totalSpent: Number(data.totalSpent || 0),
        totalEarned: Number(data.totalEarned || 0),
        records: Array.isArray(data.records) ? data.records : [],
        userInfo: data.user || {},
        pendingTransfer: data.pendingTransfer || null,
        transferHistory: Array.isArray(data.transferHistory) ? data.transferHistory : []
      })
    }).catch(() => {
      this.setData({
        balance: 0,
        lockedGems: 0,
        totalRecharged: 0,
        totalSpent: 0,
        totalEarned: 0,
        records: [],
        userInfo: {},
        pendingTransfer: null,
        transferHistory: []
      })
    })
  },

  ensureBeastId(actionText, onReady) {
    const passed = ensureBeastIdGuard({
      userInfo: this.data.userInfo,
      content: `${actionText}前请先去个人设置绑定方块兽ID，方便把转入、转出和流水都对应到你的游戏账号。`
    })

    if (passed) {
      onReady && onReady()
    }

    return passed
  },


  goProfile() {
    wx.navigateTo({ url: '/pages/profile/profile' })
  },

  goRecharge() {
    this.ensureBeastId('转入宝石', () => {
      wx.navigateTo({ url: '/pages/recharge/recharge' })
    })
  },

  goTransfer() {
    this.ensureBeastId('转出宝石', () => {
      wx.navigateTo({ url: '/pages/transfer/transfer' })
    })
  }
})
