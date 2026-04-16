const app = getApp()
const { requestApi: sendRequest } = require('../../utils/request')
const { ensureBeastId: ensureBeastIdGuard } = require('../../utils/user')


const DEFAULT_USER = {
  nickName: '方块兽玩家',
  avatarUrl: '',
  account: '',
  beastId: '',
  phone: '',
  email: '',
  accountDisplay: ''
}

function isSystemAccount(account) {
  const value = String(account || '').trim()
  return !value || value === 'player_local' || /^player_[a-z0-9]+$/i.test(value)
}

function normalizeUserInfo(user = {}) {
  const nextUser = {
    ...DEFAULT_USER,
    ...user
  }

  nextUser.nickName = String(nextUser.nickName || '').trim() || DEFAULT_USER.nickName
  nextUser.avatarUrl = String(nextUser.avatarUrl || '').trim()
  nextUser.account = String(nextUser.account || '').trim()
  nextUser.beastId = String(nextUser.beastId || '').trim()
  nextUser.phone = String(nextUser.phone || '').trim()
  nextUser.email = String(nextUser.email || '').trim()
  nextUser.accountDisplay = !isSystemAccount(nextUser.account) && nextUser.account !== nextUser.nickName
    ? nextUser.account
    : ''

  return nextUser
}

function buildMineViewData(userInfo = {}) {
  const beastId = String(userInfo.beastId || '').trim()
  const accountDisplay = String(userInfo.accountDisplay || '').trim()

  return {
    displayAvatarUrl: String(userInfo.avatarUrl || '').trim() || '/assets/default_avatar.png',
    displayNickName: String(userInfo.nickName || '').trim() || DEFAULT_USER.nickName,
    displayAccountText: accountDisplay ? `账号：${accountDisplay}` : '点击头像设置微信头像与昵称',
    displayBeastIdText: `方块兽ID：${beastId || '未绑定'}`,
    gemBindTipClass: beastId ? 'gem-bind-ok' : 'gem-bind-pending',
    gemBindTipText: beastId ? `已绑定方块兽ID：${beastId}` : '未绑定方块兽ID，转入转出前请先绑定'
  }
}


Page({

  data: {
    userInfo: {},
    gemBalance: 0,
    unreadCount: 2,
    stats: { guaranteeTotal: 0, guaranteeDone: 0, recommendCount: 0, earnedGem: 0 }
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  loadData() {
    const savedUser = normalizeUserInfo(wx.getStorageSync('userInfo') || {})

    sendRequest({
      url: '/api/user/profile',
      showLoading: false,
      showError: false
    }).then(payload => {

      const data = payload.data || {}
      const remoteUser = data.user || {}
      const wallet = data.wallet || {}
      const stats = data.stats || {}
      const userInfo = normalizeUserInfo({
        ...savedUser,
        ...remoteUser
      })

      wx.setStorageSync('userInfo', userInfo)
      app.globalData.userInfo = userInfo

      this.setData({
        userInfo,
        gemBalance: Number(wallet.gemBalance || 0),
        stats: {
          guaranteeTotal: Number(stats.guaranteeTotal || 0),
          guaranteeDone: Number(stats.guaranteeDone || 0),
          recommendCount: Number(stats.recommendCount || 0),
          earnedGem: Number(stats.earnedGem || 0)
        }
      })
    }).catch(() => {
      this.setData(Object.assign({
        userInfo: savedUser,
        gemBalance: 0,
        stats: { guaranteeTotal: 0, guaranteeDone: 0, recommendCount: 0, earnedGem: 0 }
      }, buildMineViewData(savedUser)))

    })
  },


  ensureBeastId(actionText, onReady) {
    const passed = ensureBeastIdGuard({
      userInfo: this.data.userInfo,
      content: `${actionText}前请先去个人设置绑定方块兽ID，后续转入、转出和流水记录都会更清楚。`
    })

    if (passed) {
      onReady && onReady()
    }

    return passed
  },


  goProfile() {
    wx.navigateTo({ url: '/pages/profile/profile' })
  },

  goGems() {
    wx.navigateTo({ url: '/pages/gems/gems' })
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
  },

  goMessages() {
    wx.navigateTo({ url: '/pages/messages/messages' })
  },

  goGuaranteeRecords() {
    wx.navigateTo({ url: '/pages/guarantee-records/guarantee-records' })
  },

  goAdsInvest() {

    wx.navigateTo({ url: '/pages/ads-invest/ads-invest' })
  },

  goRecommend() {
    wx.navigateTo({ url: '/pages/recommend/recommend' })
  },

  goFeedback() {
    wx.navigateTo({ url: '/pages/feedback/feedback' })
  },

  showDisclaimer() {
    wx.showModal({
      title: '免责声明',
      content: '本平台仅提供方块兽游戏宝石交易担保服务，不参与交易定价，平台对因个人操作失误导致的损失不承担责任。请确认对方身份后谨慎交易。',
      showCancel: false,
      confirmText: '我已了解'
    })
  },

  logout() {
    wx.showModal({
      title: '退出登录',
      content: '确认退出当前账号？',
      success: res => {
        if (res.confirm) {
          wx.removeStorageSync('userInfo')
          wx.removeStorageSync('token')
          app.globalData.userInfo = null
          app.globalData.openid = ''
          wx.showToast({ title: '已退出', icon: 'success' })
          this.setData({ userInfo: {}, gemBalance: 0 })
        }
      }
    })
  }
})
