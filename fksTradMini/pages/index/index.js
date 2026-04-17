const { requestApi: sendRequest } = require('../../utils/request')

const OFFICIAL_GROUP = {
  name: '方块兽交易交流群',
  qq: '769851293'
}

const DEFAULT_HOME_NOTICE = '首页顶部轮播和中部活动轮播都保留，官方群、榜单、担保入口统一集中。'

const topBanners = [
  {
    id: 'top-group',
    label: '广告',
    title: '官方群与攻略助手入口',
    desc: '点击广告位直接进群详情，群号 769851293，少走弯路。',
    brand: '官方社群推荐',
    cta: '立即查看',
    visualTitle: 'QQ 交流群',
    visualTag: '769851293',
    type: 'group',
    qq: '769851293',
    gradient: 'linear-gradient(135deg,#f7f8fc 0%,#ffffff 52%,#eef3ff 100%)'
  },
  {
    id: 'top-rank',
    label: '广告',
    title: '担保达人榜 / 推荐贡献榜',
    desc: '排行榜独立成页，顶部广告位也能直接点进去看完整榜单。',
    brand: '榜单中心',
    cta: '立即前往',
    visualTitle: '今日热榜',
    visualTag: '成功率榜',
    type: 'navigate',
    url: '/pages/rank/rank',
    gradient: 'linear-gradient(135deg,#f9f5ff 0%,#ffffff 52%,#eef8ff 100%)'
  },
  {
    id: 'top-guarantee',
    label: '广告',
    title: '担保、转入、市场一站直达',
    desc: '顶部轮播保留成广告位样式，直接跳转担保中心和常用功能。',
    brand: '交易服务',
    cta: '去担保',
    visualTitle: '担保交易',
    visualTag: '安全托底',
    type: 'switchTab',
    url: '/pages/guarantee/guarantee',
    gradient: 'linear-gradient(135deg,#f4fbff 0%,#ffffff 48%,#eaf6ff 100%)'
  }
]

const bannerCards = [
  {
    id: 'promo-group',
    title: '官方交易交流群',
    subtitle: '点进卡片直接获取加群方式，第一时间交流行情和担保经验。',
    badge: 'QQ 群',
    accent: '立即加群',
    type: 'group',
    qq: '769851293',
    gradient: 'linear-gradient(135deg,#171a3b 0%,#3247c5 55%,#60d7ff 100%)'
  },
  {
    id: 'promo-guarantee',
    title: '担保交易全流程护航',
    subtitle: '下单、转入、查询、申诉一条链路直达，减少来回找入口。',
    badge: '平台功能',
    accent: '去担保',
    type: 'switchTab',
    url: '/pages/guarantee/guarantee',
    gradient: 'linear-gradient(135deg,#21163d 0%,#7c3aed 45%,#f59e0b 100%)'
  },
  {
    id: 'promo-rank',
    title: '榜单中心全新上线',
    subtitle: '把担保达人榜和推荐贡献榜单独做成一个入口，首页不再挤。',
    badge: '独立导航',
    accent: '看榜单',
    type: 'navigate',
    url: '/pages/rank/rank',
    gradient: 'linear-gradient(135deg,#12243d 0%,#0f766e 45%,#38bdf8 100%)'
  }
]

const quickEntries = [
  { id: 'guarantee', icon: '🛡️', title: '担保中心', desc: '生成担保 / 查单', type: 'switchTab', url: '/pages/guarantee/guarantee' },
  { id: 'market', icon: '🏪', title: '市场大厅', desc: '买卖信息速览', type: 'switchTab', url: '/pages/market/market' },
  { id: 'rank', icon: '🏆', title: '排行榜', desc: '独立榜单入口', type: 'navigate', url: '/pages/rank/rank', highlight: true },
  { id: 'recharge', icon: '/assets/baoshi.png', iconType: 'image', title: '快速转入', desc: '真实校验到账', type: 'navigate', url: '/pages/recharge/recharge' },
  { id: 'messages', icon: '📩', title: '消息中心', desc: '系统通知 / 提醒', type: 'navigate', url: '/pages/messages/messages' },
  { id: 'mine', icon: '👤', title: '个人主页', desc: '资料 / 余额', type: 'switchTab', url: '/pages/mine/mine' }
]

const serviceCards = [
  {
    id: 'guarantee',
    icon: '⚡',
    title: '一键担保',
    desc: '卖家发布，买家匹配，平台中间托底。',
    actionText: '立即使用',
    type: 'switchTab',
    url: '/pages/guarantee/guarantee'
  },
  {
    id: 'rank',
    icon: '👑',
    title: '榜单中心',
    desc: '单独一栏展示担保达人与推荐贡献榜。',
    actionText: '查看排行',
    type: 'navigate',
    url: '/pages/rank/rank'
  }
]

function cloneData(data) {
  return JSON.parse(JSON.stringify(data))
}

function createDefaultHomeContent() {
  return {
    officialGroup: cloneData(OFFICIAL_GROUP),
    hotNotice: DEFAULT_HOME_NOTICE,
    topBanners: cloneData(topBanners),
    bannerCards: cloneData(bannerCards)
  }
}

function normalizeHomeContent(payload = {}) {
  const defaults = createDefaultHomeContent()
  const topList = Array.isArray(payload.topBanners) && payload.topBanners.length ? payload.topBanners : defaults.topBanners
  const promoList = Array.isArray(payload.bannerCards) && payload.bannerCards.length ? payload.bannerCards : defaults.bannerCards

  return {
    officialGroup: {
      ...defaults.officialGroup,
      ...(payload.officialGroup || {})
    },
    hotNotice: String(payload.hotNotice || defaults.hotNotice),
    topBanners: topList.map(item => ({ ...item, id: String(item.id || '') })),
    bannerCards: promoList.map(item => ({ ...item, id: String(item.id || '') }))
  }
}

function formatRankItem(item, index) {
  return {
    ...item,
    rankNo: index + 1,
    scoreText: `${item.score || 0} 次担保`,
    rewardText: `${item.reward || 0} 宝石`
  }
}

Page({
  data: {
    userInfo: {},
    gemBalance: 0,
    topBanners,
    bannerCards,
    quickEntries,
    serviceCards,
    officialGroup: OFFICIAL_GROUP,
    rankPreview: [],
    hotNotice: DEFAULT_HOME_NOTICE,
    pendingSummary: { total: 0, pendingConfirm: 0, pendingMatch: 0, waitingSeller: 0, pendingTransfer: 0, unreadMessages: 0 }
  },

  onLoad(options = {}) {
    this.consumePromotionRef(options.ref)
    this.loadHomeData()
  },

  onShow() {
    this.loadHomeData()
  },

  consumePromotionRef(ref) {
    const inviteCode = String(ref || '').trim().toUpperCase()
    if (!inviteCode || inviteCode === this.lastHandledRef) return

    this.lastHandledRef = inviteCode
    sendRequest({
      url: '/api/promotion/bind',
      method: 'POST',
      data: { ref: inviteCode },
      showLoading: false,
      showError: false
    }).catch(() => {})
  },

  loadHomeData() {
    const savedUser = wx.getStorageSync('userInfo') || {}
    this.setData({ userInfo: savedUser, rankPreview: [] })

    Promise.all([
      sendRequest({ url: '/api/user/balance', showLoading: false, showError: false })
        .then(value => ({ ok: true, value })).catch(error => ({ ok: false, error })),
      sendRequest({ url: `/api/home/content?_t=${Date.now()}`, showLoading: false, showError: false })
        .then(value => ({ ok: true, value })).catch(error => ({ ok: false, error })),
      sendRequest({ url: '/api/user/pending-summary', showLoading: false, showError: false })
        .then(value => ({ ok: true, value })).catch(error => ({ ok: false, error }))
    ]).then(([balanceResult, homeResult, pendingResult]) => {
      const nextData = {}

      if (balanceResult.ok) {
        nextData.gemBalance = Number((balanceResult.value.data && balanceResult.value.data.gemBalance) || 0)
      }

      if (homeResult.ok) {
        const homeContent = normalizeHomeContent(homeResult.value.data || {})
        nextData.topBanners = homeContent.topBanners
        nextData.bannerCards = homeContent.bannerCards
        nextData.hotNotice = homeContent.hotNotice
        nextData.officialGroup = homeContent.officialGroup
      }

      if (pendingResult.ok) {
        nextData.pendingSummary = pendingResult.value.data || { total: 0 }
      }

      if (Object.keys(nextData).length) {
        this.setData(nextData)
      }
    })
  },

  handleTopBannerTap(e) {
    const bannerId = String(e.currentTarget.dataset.id || '')
    const banner = (this.data.topBanners || []).find(item => String(item.id || '') === bannerId) || {}
    this.handleAction(banner)
  },

  handleBannerTap(e) {
    const cardId = String(e.currentTarget.dataset.id || '')
    const card = (this.data.bannerCards || []).find(item => String(item.id || '') === cardId) || {}
    this.handleAction(card)
  },

  handleQuickEntryTap(e) {
    const entryId = String(e.currentTarget.dataset.id || '')
    const entry = (this.data.quickEntries || []).find(item => item.id === entryId) || {}
    this.handleAction(entry)
  },

  handleServiceTap(e) {
    const entryId = String(e.currentTarget.dataset.id || '')
    const entry = (this.data.serviceCards || []).find(item => item.id === entryId) || {}
    this.handleAction(entry)
  },

  handleAction(action) {
    if (!action || !action.type) return

    if (action.type === 'group') {
      const qq = String(action.qq || this.data.officialGroup.qq || OFFICIAL_GROUP.qq)
      wx.navigateTo({ url: `/pages/group-detail/group-detail?qq=${qq}` })
      return
    }

    if (action.type === 'switchTab' && action.url) {
      wx.switchTab({ url: action.url })
      return
    }

    if (action.type === 'navigate' && action.url) {
      wx.navigateTo({ url: action.url })
    }
  },

  handlePendingTap() {
    const summary = this.data.pendingSummary || {}
    if (summary.pendingConfirm > 0 || summary.pendingMatch > 0) {
      wx.switchTab({ url: '/pages/guarantee/guarantee' })
    } else if (summary.pendingTransfer > 0) {
      wx.navigateTo({ url: '/pages/transfer/transfer' })
    } else if (summary.unreadMessages > 0) {
      wx.switchTab({ url: '/pages/messages/messages' })
    } else {
      wx.switchTab({ url: '/pages/guarantee/guarantee' })
    }
  },

  goRankPage() {
    wx.navigateTo({ url: '/pages/rank/rank' })
  },

  goGroupDetail() {
    const qq = String(this.data.officialGroup.qq || OFFICIAL_GROUP.qq)
    wx.navigateTo({ url: `/pages/group-detail/group-detail?qq=${qq}` })
  },

  copyGroupQQ() {
    wx.setClipboardData({
      data: String(this.data.officialGroup.qq || OFFICIAL_GROUP.qq),
      success: () => wx.showToast({ title: '群号已复制', icon: 'success' })
    })
  }
})
