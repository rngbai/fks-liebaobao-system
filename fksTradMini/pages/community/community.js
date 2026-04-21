const app = getApp()
const { resolveImageUrl } = require('../../utils/guarantee')
const {
  createPageLoadState,
  toEmptyState,
  toErrorState,
  toSuccessState,
} = require('../../utils/page-load-state')

const CATEGORIES = [
  { id: 'captain',  icon: '👑', label: '大咖团队长', subTabs: ['地球猎人', '旅行世界', '人猿大陆', '乌龟海战', '保卫方块'] },
  { id: 'broker',   icon: '💼', label: '顶商中介',   subTabs: ['兽王/珍兽', '金币/超级币', '矿石/护甲', '宝石', '魔方'] },
  { id: 'streamer', icon: '🎙️', label: '主播抖/快',  subTabs: ['抖音', '快手'] },
  { id: 'blogger',  icon: '📖', label: '攻略博主',   subTabs: ['公众号'] },
  { id: 'guild',    icon: '🏰', label: '猎人公会',   subTabs: [] },
]

/** 大咖团队长分区：与 images/img 文件名缩写对应 */
const CAPTAIN_GAME_SHORTCUTS = [
  { id: 'dqlr', name: '地球猎人', image: '/images/img/dqlr.webp' },
  { id: 'lxsj', name: '旅行世界', image: '/images/img/lxsj.webp' },
  { id: 'rycq', name: '人猿大陆', image: '/images/img/rycq.webp' },
  { id: 'wghz', name: '乌龟海战', image: '/images/img/wghz.webp' },
  { id: 'bwfk', name: '保卫方块', image: '/images/img/bwfk.webp' },
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
    activeCatLabel: '大咖团队长',
    captainGameShortcuts: CAPTAIN_GAME_SHORTCUTS,
    activeSub: '地球猎人',
    currentSubTabs: CATEGORIES[0].subTabs,
    currentLocationText: buildCurrentLocationText('captain', '地球猎人'),
    currentList: [],
    loading: false,
    pageState: createPageLoadState('loading'),
  },

  _applyPendingCommunityRouteIfAny() {
    const app = getApp()
    const pending = app.globalData && app.globalData.pendingCommunityRoute
    if (!pending || typeof pending !== 'object') return
    app.globalData.pendingCommunityRoute = null

    const catId = String(pending.category || 'captain').trim() || 'captain'
    const cat = getCategoryById(catId)
    const subs = cat.subTabs || []
    const wantSub = String(pending.sub_tab || pending.subTab || '').trim()
    const resolvedSub = wantSub && subs.includes(wantSub) ? wantSub : (subs[0] || '')

    this.setData({
      activeCat: cat.id,
      activeCatLabel: cat.label,
      activeSub: resolvedSub,
      currentSubTabs: subs,
      currentLocationText: buildCurrentLocationText(cat.id, resolvedSub),
    })
  },

  onLoad() {
    this._loadTs = 0
    this._applyPendingCommunityRouteIfAny()
    this._fetchList()
  },

  onShow() {
    this._applyPendingCommunityRouteIfAny()
    if (Date.now() - (this._loadTs || 0) >= 1500) {
      this._fetchList()
    }
  },

  switchCat(e) {
    const id = e.currentTarget.dataset.id
    if (id === this.data.activeCat) return
    const cat = getCategoryById(id)
    const firstSub = cat.subTabs[0] || ''
    this.setData({
      activeCat: id,
      activeCatLabel: cat.label,
      activeSub: firstSub,
      currentSubTabs: cat.subTabs,
      currentLocationText: buildCurrentLocationText(id, firstSub),
    })
    this._fetchList()
  },

  switchSub(e) {
    const sub = e.currentTarget.dataset.sub
    if (sub === this.data.activeSub) return
    this.setData({
      activeSub: sub,
      currentLocationText: buildCurrentLocationText(this.data.activeCat, sub),
    })
    this._fetchList()
  },

  _fetchList() {
    this._loadTs = Date.now()
    const { activeCat, activeSub } = this.data
    const cat = getCategoryById(activeCat)
    const hasSubTabs = cat && cat.subTabs.length > 0

    let query = `/api/community?category=${activeCat}&_t=${Date.now()}`
    if (hasSubTabs && activeSub) query += `&sub_tab=${encodeURIComponent(activeSub)}`

    this.setData({ loading: true })

    const appInst = getApp()
    if (!appInst || typeof appInst.request !== 'function') {
      this.setData({ currentList: [], loading: false, pageState: toErrorState('社区名流加载失败，请点击重试') })
      return
    }

    try {
      appInst.request({
        url: query,
        method: 'GET',
        showLoading: false,
        showError: false,
      }).then(payload => {
        const data = (payload && payload.data) || {}
        const sourceList = Array.isArray(data.list)
          ? data.list
          : Array.isArray(payload && payload.list)
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
        this.setData({
          currentList: list,
          loading: false,
          pageState: list.length ? toSuccessState() : toEmptyState(),
        })
      }).catch(() => {
        this.setData({ currentList: [], loading: false, pageState: toErrorState('社区名流加载失败，请点击重试') })
      })
    } catch (e) {
      this.setData({ currentList: [], loading: false, pageState: toErrorState('社区名流加载失败，请点击重试') })
    }
  },

  retryFetchList() {
    this._fetchList()
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
