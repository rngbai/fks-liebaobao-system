const { requestApi: sendRequest } = require('../../utils/request')

const DEFAULT_HEADER_SUB = '推荐好友使用平台，好友首次有效交易后您获得奖励'

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
    { min: 1, max: 5, reward: 10, label: '首位有效推荐' },
    { min: 6, max: 20, reward: 50, label: '达到 6 位有效推荐' },
    { min: 21, max: 50, reward: 200, label: '达到 21 位有效推荐' },
    { min: 51, max: null, reward: 600, label: '达到 51 位有效推荐' }
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
