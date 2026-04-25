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
  { id: 'dqlr', name: '地球猎人', image: '/images/img/dqlr.png' },
  { id: 'lxsj', name: '旅行世界', image: '/images/img/lxsj.png' },
  { id: 'rycq', name: '人猿大陆', image: '/images/img/rycq.png' },
  { id: 'wghz', name: '乌龟海战', image: '/images/img/wghz.png' },
  { id: 'bwfk', name: '保卫方块', image: '/images/img/bwfk.png' },
]
const APPLY_HIGHLIGHTS = ['人工审核', '每日限 2 次', '通过后展示']
const SHOW_DEDUPE_MS = 10000
const COMMUNITY_CACHE_MS = 60000
const COMMUNITY_STALE_CACHE_MS = 24 * 60 * 60 * 1000
const COMMUNITY_STORAGE_KEY = 'community_profiles_cache_v1'

function getCategoryById(id) {
  return CATEGORIES.find(item => item.id === id) || CATEGORIES[0]
}

function buildCurrentLocationText(categoryId, subTab) {
  const category = getCategoryById(categoryId)
  return [category.label, subTab].filter(Boolean).join(' · ')
}

function buildCacheKey(activeCat, activeSub) {
  return `${activeCat || 'captain'}::${activeSub || ''}`
}

function normalizeCommunityProfile(item = {}) {
  return {
    ...item,
    category: String(item.category || '').trim(),
    sub_tab: String(item.sub_tab || item.subTab || '').trim(),
    avatar: resolveImageUrl(item.avatar || item.avatar_url || ''),
    badgeType: item.badge_type || 'verified',
    badgeIcon: '',
    badgeLabel: item.badge_label || '认证',
    gameTag: item.game_tag || '',
  }
}

Page({
  data: {
    categories: CATEGORIES,
    applyHighlights: APPLY_HIGHLIGHTS,
    skeletonRows: [1, 2, 3],
    activeCat: 'captain',
    activeCatLabel: '大咖团队长',
    captainGameShortcuts: CAPTAIN_GAME_SHORTCUTS,
    activeSub: '地球猎人',
    currentSubTabs: CATEGORIES[0].subTabs,
    currentLocationText: buildCurrentLocationText('captain', '地球猎人'),
    activeListKey: buildCacheKey('captain', '地球猎人'),
    currentListKey: '',
    currentList: [],
    loading: false,
    contentReady: false,
    pageState: createPageLoadState('loading'),
  },

  _applyPendingCommunityRouteIfAny() {
    const app = getApp()
    const pending = app.globalData && app.globalData.pendingCommunityRoute
    if (!pending || typeof pending !== 'object') return false
    app.globalData.pendingCommunityRoute = null

    const prevKey = this._getCacheKey(this.data.activeCat, this.data.activeSub)
    const catId = String(pending.category || 'captain').trim() || 'captain'
    const cat = getCategoryById(catId)
    const subs = cat.subTabs || []
    const wantSub = String(pending.sub_tab || pending.subTab || '').trim()
    const resolvedSub = wantSub && subs.includes(wantSub) ? wantSub : (subs[0] || '')
    const nextKey = this._getCacheKey(cat.id, resolvedSub)

    this.setData({
      activeCat: cat.id,
      activeCatLabel: cat.label,
      activeSub: resolvedSub,
      currentSubTabs: subs,
      currentLocationText: buildCurrentLocationText(cat.id, resolvedSub),
      activeListKey: nextKey,
    })

    return prevKey !== nextKey
  },

  onLoad() {
    this._loadTs = 0
    this._requestSeq = 0
    this._listCache = {}
    this._allProfiles = []
    this._allProfilesTs = 0
    this._applyPendingCommunityRouteIfAny()
    this._warmShortcutImages()
    if (this._restoreGlobalProfilesCache()) {
      this._applyCurrentListFromLocal({ allowStale: true })
    } else if (this._restoreAllProfilesCache()) {
      this._applyCurrentListFromLocal({ allowStale: true })
    }
    this._fetchList({ preferCache: true, silent: this.data.currentList.length > 0 })
  },

  onShow() {
    const routeChanged = this._applyPendingCommunityRouteIfAny()
    if (routeChanged) {
      this._fetchList({ preferCache: true })
      return
    }
    if (Date.now() - (this._loadTs || 0) >= SHOW_DEDUPE_MS) {
      this._fetchList({ preferCache: true })
    }
  },

  switchCat(e) {
    const id = e.currentTarget.dataset.id
    if (id === this.data.activeCat) return
    const cat = getCategoryById(id)
    const firstSub = cat.subTabs[0] || ''
    const nextKey = this._getCacheKey(id, firstSub)
    const nextPatch = {
      activeCat: id,
      activeCatLabel: cat.label,
      activeSub: firstSub,
      currentSubTabs: cat.subTabs,
      currentLocationText: buildCurrentLocationText(id, firstSub),
      activeListKey: nextKey,
    }
    const listPatch = this._buildLocalListPatch(id, firstSub, { allowStale: true })
    if (listPatch) {
      this.setData({ ...nextPatch, ...listPatch })
      if (!this._hasFreshAllProfiles()) {
        this._fetchList({ preferCache: true, silent: true })
      }
    } else {
      this.setData({
        ...nextPatch,
        currentList: [],
        currentListKey: '',
        loading: true,
        contentReady: false,
        pageState: createPageLoadState('loading'),
      })
      this._fetchList({ preferCache: true })
    }
  },

  switchSub(e) {
    const sub = e.currentTarget.dataset.sub
    if (sub === this.data.activeSub) return
    const nextKey = this._getCacheKey(this.data.activeCat, sub)
    const nextPatch = {
      activeSub: sub,
      currentLocationText: buildCurrentLocationText(this.data.activeCat, sub),
      activeListKey: nextKey,
    }
    const listPatch = this._buildLocalListPatch(this.data.activeCat, sub, { allowStale: true })
    if (listPatch) {
      this.setData({ ...nextPatch, ...listPatch })
      if (!this._hasFreshAllProfiles()) {
        this._fetchList({ preferCache: true, silent: true })
      }
    } else {
      this.setData({
        ...nextPatch,
        currentList: [],
        currentListKey: '',
        loading: true,
        contentReady: false,
        pageState: createPageLoadState('loading'),
      })
      this._fetchList({ preferCache: true })
    }
  },

  _getCacheKey(activeCat, activeSub) {
    return buildCacheKey(activeCat, activeSub)
  },

  _readListCache(key) {
    const cache = this._listCache && this._listCache[key]
    if (!cache) return null
    if (Date.now() - cache.ts > COMMUNITY_CACHE_MS) return null
    return cache
  },

  _writeListCache(key, list, pageState) {
    this._listCache = this._listCache || {}
    this._listCache[key] = {
      list,
      pageState,
      ts: Date.now(),
    }
  },

  _hasFreshAllProfiles() {
    return Array.isArray(this._allProfiles) &&
      this._allProfilesTs > 0 &&
      Date.now() - (this._allProfilesTs || 0) <= COMMUNITY_CACHE_MS
  },

  _hasUsableAllProfiles() {
    return Array.isArray(this._allProfiles) &&
      this._allProfilesTs > 0 &&
      Date.now() - (this._allProfilesTs || 0) <= COMMUNITY_STALE_CACHE_MS
  },

  _getFilteredList(activeCat, activeSub) {
    const cat = getCategoryById(activeCat)
    const hasSubTabs = cat && cat.subTabs.length > 0
    return (this._allProfiles || []).filter(item => {
      if (item.category !== activeCat) return false
      if (hasSubTabs) return item.sub_tab === activeSub
      return true
    })
  },

  _getCurrentFilteredList() {
    return this._getFilteredList(this.data.activeCat, this.data.activeSub)
  },

  _buildLocalListPatch(activeCat, activeSub, { allowStale = false } = {}) {
    if (!(allowStale ? this._hasUsableAllProfiles() : this._hasFreshAllProfiles())) return null
    const cacheKey = this._getCacheKey(activeCat, activeSub)
    const cached = this._readListCache(cacheKey)
    const list = cached ? cached.list : this._getFilteredList(activeCat, activeSub)
    const pageState = cached ? cached.pageState : (list.length ? toSuccessState() : toEmptyState())
    if (!cached) {
      this._writeListCache(cacheKey, list, pageState)
    }
    return {
      currentList: list,
      currentListKey: cacheKey,
      loading: false,
      contentReady: true,
      pageState,
    }
  },

  _applyCurrentListFromLocal({ allowStale = false } = {}) {
    const patch = this._buildLocalListPatch(this.data.activeCat, this.data.activeSub, { allowStale })
    if (!patch) return false
    this.setData(patch)
    return true
  },

  _restoreAllProfilesCache() {
    try {
      const cache = wx.getStorageSync(COMMUNITY_STORAGE_KEY)
      if (!cache || !Array.isArray(cache.list) || !cache.ts) return false
      if (Date.now() - Number(cache.ts || 0) > COMMUNITY_STALE_CACHE_MS) return false
      this._allProfiles = cache.list.map(item => {
        const profile = normalizeCommunityProfile(item)
        profile.badgeIcon = this._badgeIcon(profile.badgeType)
        return profile
      })
      this._allProfilesTs = Number(cache.ts || 0)
      this._listCache = {}
      return true
    } catch (error) {
      return false
    }
  },

  _persistAllProfilesCache() {
    try {
      wx.setStorageSync(COMMUNITY_STORAGE_KEY, {
        ts: this._allProfilesTs,
        list: this._allProfiles || [],
      })
    } catch (error) {}
  },

  _applyAllProfilesSource(sourceList = [], ts = Date.now()) {
    this._allProfiles = (Array.isArray(sourceList) ? sourceList : []).map(item => {
      const profile = normalizeCommunityProfile(item)
      profile.badgeIcon = this._badgeIcon(profile.badgeType)
      return profile
    })
    this._allProfilesTs = Number(ts || Date.now())
    this._listCache = {}
    return true
  },

  _restoreGlobalProfilesCache() {
    try {
      const appInst = getApp()
      const cache = appInst && typeof appInst.getCommunityProfilesCache === 'function'
        ? appInst.getCommunityProfilesCache(COMMUNITY_STALE_CACHE_MS)
        : null
      if (!cache || !Array.isArray(cache.list) || !cache.ts) return false
      return this._applyAllProfilesSource(cache.list, cache.ts)
    } catch (error) {
      return false
    }
  },

  _fetchList({ preferCache = false, silent = false } = {}) {
    this._loadTs = Date.now()
    const requestSeq = (this._requestSeq || 0) + 1
    this._requestSeq = requestSeq
    const usedLocalCache = preferCache && this._applyCurrentListFromLocal()

    const activeListKey = this._getCacheKey(this.data.activeCat, this.data.activeSub)
    const hasCurrentContent = this.data.currentListKey === activeListKey && this.data.currentList.length > 0
    const query = '/api/community'
    const loadingPatch = {
      loading: !silent && !usedLocalCache,
      contentReady: hasCurrentContent,
    }
    if (!hasCurrentContent && !usedLocalCache) {
      loadingPatch.currentList = []
      loadingPatch.currentListKey = ''
      loadingPatch.pageState = createPageLoadState('loading')
    }
    if (!usedLocalCache || !silent) {
      this.setData(loadingPatch)
    }

    const appInst = getApp()
    if (!appInst || typeof appInst.request !== 'function') {
      this.setData({
        currentList: [],
        currentListKey: activeListKey,
        loading: false,
        contentReady: true,
        pageState: toErrorState('社区名流加载失败，请点击重试'),
      })
      return
    }

    try {
      const requestTask = typeof appInst.prefetchCommunityProfiles === 'function'
        ? appInst.prefetchCommunityProfiles({ force: true })
        : appInst.request({
            url: query,
            method: 'GET',
            showLoading: false,
            showError: false,
            retry: 0,
            timeout: 6000,
          })

      requestTask.then(payload => {
        if (requestSeq !== this._requestSeq) return
        const data = (payload && payload.data) || {}
        const sourceList = Array.isArray(data.list)
          ? data.list
          : Array.isArray(payload && payload.list)
            ? payload.list
            : []
        const sourceTs = Number(payload && payload.ts) || Date.now()
        this._applyAllProfilesSource(sourceList, sourceTs)
        this._persistAllProfilesCache()
        const list = this._getCurrentFilteredList()
        const pageState = list.length ? toSuccessState() : toEmptyState()
        const nextListKey = this._getCacheKey(this.data.activeCat, this.data.activeSub)
        this._writeListCache(nextListKey, list, pageState)
        this._warmProfileImages(this._allProfiles)
        this.setData({
          currentList: list,
          currentListKey: nextListKey,
          loading: false,
          contentReady: true,
          pageState,
        })
      }).catch(() => {
        if (requestSeq !== this._requestSeq) return
        if (this._applyCurrentListFromLocal({ allowStale: true })) {
          return
        }
        this.setData({
          currentList: [],
          currentListKey: activeListKey,
          loading: false,
          contentReady: true,
          pageState: toErrorState('社区名流加载失败，请点击重试'),
        })
      })
    } catch (e) {
      if (requestSeq !== this._requestSeq) return
      if (this._applyCurrentListFromLocal({ allowStale: true })) {
        return
      }
      this.setData({
        currentList: [],
        currentListKey: activeListKey,
        loading: false,
        contentReady: true,
        pageState: toErrorState('社区名流加载失败，请点击重试'),
      })
    }
  },

  retryFetchList() {
    this._fetchList()
  },

  _warmProfileImages(list = []) {
    if (!wx.getImageInfo) return
    const urls = Array.from(new Set(
      list.map(item => item.avatar).filter(Boolean)
    )).slice(0, 16)
    urls.forEach(url => {
      wx.getImageInfo({
        src: url,
        success: () => {},
        fail: () => {},
      })
    })
  },

  _warmShortcutImages() {
    if (!wx.getImageInfo) return
    CAPTAIN_GAME_SHORTCUTS.forEach(item => {
      wx.getImageInfo({
        src: item.image,
        success: () => {},
        fail: () => {},
      })
    })
  },

  handleShortcutImageError(e) {
    const shortcutId = String(e.currentTarget.dataset.id || '')
    const nextShortcuts = (this.data.captainGameShortcuts || []).map(item => (
      item.id === shortcutId ? { ...item, image: '/assets/baoshi.png' } : item
    ))
    this.setData({ captainGameShortcuts: nextShortcuts })
  },

  handleAvatarImageError(e) {
    const profileId = String(e.currentTarget.dataset.id || '')
    const fallbackAvatar = '/assets/default_avatar.png'
    const nextList = (this.data.currentList || []).map(item => (
      String(item.id || '') === profileId ? { ...item, avatar: fallbackAvatar } : item
    ))
    this._allProfiles = (this._allProfiles || []).map(item => (
      String(item.id || '') === profileId ? { ...item, avatar: fallbackAvatar } : item
    ))
    this._writeListCache(
      this._getCacheKey(this.data.activeCat, this.data.activeSub),
      nextList,
      this.data.pageState
    )
    this.setData({ currentList: nextList })
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
