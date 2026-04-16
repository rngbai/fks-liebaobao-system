const app = getApp()

const CATEGORIES = [
  { id: 'captain',  icon: '👑', label: '大咖团队长', subTabs: ['地球猎人', '旅行世界', '人猿大陆', '乌龟海战', '保卫方块'] },
  { id: 'broker',   icon: '💼', label: '顶商中介',   subTabs: ['兽王/珍兽', '金币/超级币', '矿石/护甲', '宝石', '魔方'] },
  { id: 'streamer', icon: '🎙️', label: '主播抖/快',  subTabs: ['抖音', '快手'] },
  { id: 'blogger',  icon: '📖', label: '攻略博主',   subTabs: ['公众号'] },
  { id: 'guild',    icon: '🏰', label: '猎人公会',   subTabs: [] },
]

Page({
  data: {
    categories: CATEGORIES,
    activeCat: 'captain',
    activeSub: '地球猎人',
    currentSubTabs: CATEGORIES[0].subTabs,
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
    const cat = CATEGORIES.find(c => c.id === id)
    const firstSub = cat.subTabs[0] || ''
    this.setData({ activeCat: id, activeSub: firstSub, currentSubTabs: cat.subTabs, currentList: [] })
    this._fetchList()
  },

  switchSub(e) {
    const sub = e.currentTarget.dataset.sub
    if (sub === this.data.activeSub) return
    this.setData({ activeSub: sub, currentList: [] })
    this._fetchList()
  },

  _fetchList() {
    const { activeCat, activeSub } = this.data
    const cat = CATEGORIES.find(c => c.id === activeCat)
    const hasSubTabs = cat && cat.subTabs.length > 0

    let query = `/api/community?category=${activeCat}`
    if (hasSubTabs && activeSub) query += `&sub_tab=${encodeURIComponent(activeSub)}`

    this.setData({ loading: true })
    app.request({
      url: query,
      method: 'GET',
      showLoading: false,
      showError: false,
    }).then(res => {
      const list = (res.list || []).map(item => ({
        ...item,
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
    wx.navigateTo({ url: '/pages/feedback/feedback' })
  },
})
