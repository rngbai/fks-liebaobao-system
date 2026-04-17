const app = getApp()
const { resolveImageUrl } = require('../../utils/guarantee')

const CATEGORIES = [
  { id: 'captain',  icon: '👑', label: '大咖团队长', subTabs: ['地球猎人', '旅行世界', '人猿大陆', '乌龟海战', '保卫方块'] },
  { id: 'broker',   icon: '💼', label: '顶商中介',   subTabs: ['兽王/珍兽', '金币/超级币', '矿石/护甲', '宝石', '魔方'] },
  { id: 'streamer', icon: '🎙️', label: '主播抖/快',  subTabs: ['抖音', '快手'] },
  { id: 'blogger',  icon: '📖', label: '攻略博主',   subTabs: ['公众号'] },
  { id: 'guild',    icon: '🏰', label: '猎人公会',   subTabs: [] },
]
const APPLY_HIGHLIGHTS = ['人工审核', '每日限 2 次', '通过后展示']

function getCategoryById(id) {
  return CATEGORIES.find(item => item.id === id) || CATEGORIES[0]
}

function buildCurrentLocationText(categoryId, subTab) {
  const category = getCategoryById(categoryId)
  return [category.label, subTab].filter(Boolean).join(' · ')
}

Page({
  data: {
    categories: CATEGORIES,
    applyHighlights: APPLY_HIGHLIGHTS,
    activeCat: 'captain',
    activeSub: '地球猎人',
    currentSubTabs: CATEGORIES[0].subTabs,
    currentLocationText: buildCurrentLocationText('captain', '地球猎人'),
    currentList: [],
    loading: false,
  },

  onLoad() {
    this._fetchList()
  },

  onShow() {
    this._fetchList()
  },

  switchCat(e) {
    const id = e.currentTarget.dataset.id
    if (id === this.data.activeCat) return
    const cat = getCategoryById(id)
    const firstSub = cat.subTabs[0] || ''
    this.setData({
      activeCat: id,
      activeSub: firstSub,
      currentSubTabs: cat.subTabs,
      currentLocationText: buildCurrentLocationText(id, firstSub),
      currentList: []
    })
    this._fetchList()
  },

  switchSub(e) {
    const sub = e.currentTarget.dataset.sub
    if (sub === this.data.activeSub) return
    this.setData({
      activeSub: sub,
      currentLocationText: buildCurrentLocationText(this.data.activeCat, sub),
      currentList: []
    })
    this._fetchList()
  },

  _fetchList() {
    const { activeCat, activeSub } = this.data
    const cat = getCategoryById(activeCat)
    const hasSubTabs = cat && cat.subTabs.length > 0

    let query = `/api/community?category=${activeCat}&_t=${Date.now()}`
    if (hasSubTabs && activeSub) query += `&sub_tab=${encodeURIComponent(activeSub)}`

    this.setData({ loading: true })
    app.request({
      url: query,
      method: 'GET',
      showLoading: false,
      showError: false,
    }).then(payload => {
      const data = payload.data || {}
      const sourceList = Array.isArray(data.list)
        ? data.list
        : Array.isArray(payload.list)
          ? payload.list
          : []
      const list = sourceList.map(item => ({
        ...item,
        avatar: resolveImageUrl(item.avatar || item.avatar_url || ''),
        badgeType: item.badge_type || 'verified',
        badgeIcon: this._badgeIcon(item.badge_type),
        badgeLabel: item.badge_label || '认证',
        gameTag: item.game_tag || '',
      }))
      this.setData({ currentList: list, loading: false })
    }).catch(() => {
      this.setData({ currentList: [], loading: false })
    })
  },

  _badgeIcon(type) {
    const map = { gold: '👑', silver: '🥈', verified: '✅', streamer: '🎬', guild: '🏰' }
    return map[type] || '✅'
  },

  copyContact(e) {
    const { val, label } = e.currentTarget.dataset
    wx.setClipboardData({
      data: val,
      success: () => wx.showToast({ title: `${label}号已复制`, icon: 'success' })
    })
  },

  onCardTap() {},

  goApply() {
    const { activeCat, activeSub } = this.data
    const category = getCategoryById(activeCat)
    const params = [
      'scene=community_apply',
      `category=${encodeURIComponent(activeCat)}`,
      `category_label=${encodeURIComponent(category.label || '')}`,
    ]
    if (activeSub) {
      params.push(`sub_tab=${encodeURIComponent(activeSub)}`)
    }
    wx.navigateTo({ url: `/pages/feedback/feedback?${params.join('&')}` })
  },
})
