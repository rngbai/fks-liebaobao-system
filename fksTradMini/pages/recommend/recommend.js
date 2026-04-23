const { requestApi: sendRequest } = require('../../utils/request')

const DEFAULT_HEADER_SUB = '推荐好友完成担保交易后，永久分佣会自动到账。'

function normalizeRule(item = {}) {
  const min = Number(item.min || 0)
  const max = item.max === null || item.max === undefined || item.max === '' ? null : Number(item.max)
  return {
    min,
    max,
    reward: Number(item.reward || 0),
    label: item.label || '',
    rangeText: max !== null && max >= min ? `${min}~${max}` : `${min}+`
  }
}

function normalizeInvitee(item = {}) {
  const status = Number(item.status || 0)
  const account = String(item.account || '').trim() || '未设置账号'
  const beastId = String(item.beastId || '').trim()

  return Object.assign({}, item, {
    displayName: String(item.nick || '').trim() || '方块兽玩家',
    metaText: beastId ? `${account} · ${beastId}` : account,
    timeText: String(item.promotionEffectiveAt || item.time || '未绑定时间'),
    statusClass: status === 1 ? 'invited-status-success' : 'invited-status-pending',
    statusLabel: status === 1 ? '已生效' : '待转化'
  })
}

function createDefaultRules() {
  return [
    { min: 1, max: null, reward: 0.3, label: '直推每单奖励 0.3 宝石' },
    { min: 1, max: null, reward: 0.2, label: '间推每单奖励 0.2 宝石' }
  ].map(normalizeRule)
}

Page({
  data: {
    loading: false,
    headerSubText: DEFAULT_HEADER_SUB,
    myRecommendCount: 0,
    myEffectiveCount: 0,
    myPendingCount: 0,
    myRewardGem: 0,
    myCode: '',
    myCodeText: '生成中',
    rules: createDefaultRules(),
    invitedList: []
  },

  onLoad() {
    this.loadPromotionData()
  },

  onShow() {
    this.loadPromotionData({ silent: true })
  },

  loadPromotionData({ silent = false } = {}) {
    if (!silent) {
      this.setData({ loading: true, headerSubText: '正在同步最新推广数据...' })
    }

    sendRequest({
      url: '/api/promotion/my?limit=30',
      showLoading: false,
      showError: !silent
    }).then(payload => {
      const promotion = (payload.data && payload.data.promotion) || {}
      const rules = Array.isArray(promotion.rules) && promotion.rules.length
        ? promotion.rules.map((item, index) => {
            const threshold = Number(item.threshold || 0)
            const nextThreshold = Number((promotion.rules[index + 1] || {}).threshold || 0)
            return normalizeRule({
              min: threshold,
              max: nextThreshold > threshold ? nextThreshold - 1 : null,
              reward: Number(item.reward || 0),
              label: item.label || ''
            })
          })
        : createDefaultRules()

      this.setData({
        loading: false,
        headerSubText: DEFAULT_HEADER_SUB,
        myRecommendCount: Number(promotion.totalInvited || 0),
        myEffectiveCount: Number(promotion.effectiveInvited || 0),
        myPendingCount: Number(promotion.pendingInvited || 0),
        myRewardGem: Number(promotion.totalRewardAmount || 0),
        myCode: String(promotion.inviteCode || ''),
        myCodeText: String(promotion.inviteCode || '') || '生成中',
        rules,
        invitedList: Array.isArray(promotion.invitees) ? promotion.invitees.map(normalizeInvitee) : []
      })
    }).catch(() => {
      if (!silent) {
        this.setData({ loading: false, headerSubText: DEFAULT_HEADER_SUB })
      }
    })
  },

  copyCode() {
    if (!this.data.myCode) {
      wx.showToast({ title: '推荐码生成中', icon: 'none' })
      return
    }
    wx.setClipboardData({
      data: this.data.myCode,
      success: () => wx.showToast({ title: '推荐码已复制', icon: 'success' })
    })
  },

  onShareAppMessage() {
    return {
      title: '方块兽担保平台，安全交易必备！',
      desc: '专业游戏宝石交易担保，杜绝跑路！',
      path: `/pages/index/index?ref=${this.data.myCode || ''}`
    }
  }
})
