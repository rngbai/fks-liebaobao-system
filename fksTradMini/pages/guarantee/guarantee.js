const { requestApi: sendRequest } = require('../../utils/request')
const { normalizeGuaranteeItem } = require('../../utils/guarantee')

// onLoad/首次进入：1.5 秒去重；Tab 切换（onShow）：8 秒去重，避免每次切换都发请求
const LOAD_DEDUPE_MS = 1500
const SHOW_DEDUPE_MS = 8000
// 静默重试次数（在弹出错误提示前先自动重试一次）
const SILENT_RETRY_TIMES = 1

Page({
  data: {
    gemBalance: 0,
    queryOrderId: '',
    guaranteeList: [],
    publicOrders: [],
    publicPetTags: [],
    publicFilterPet: '',
    statusText: ['待买家匹配', '待卖家确认', '已完成', '申诉中'],
    // 是否第一次没有任何数据的加载失败（此时才显示红条）
    loadError: false,
    // 后台静默刷新中（有旧数据时用，不阻塞 UI）
    silentRefreshing: false,
  },

  onLoad() {
    this._loadTs = 0
    this._showTs = 0
    this._hasData = false
    this.loadData({ force: true })
  },

  onShow() {
    // Tab 切换：有旧数据则静默刷新（不清空，不显示红条）；没有数据才强制加载
    const now = Date.now()
    if (now - (this._showTs || 0) < SHOW_DEDUPE_MS) return
    this._showTs = now
    if (this._hasData) {
      this._silentRefresh()
    } else {
      this.loadData({ force: false })
    }
  },

  onHide() {
    this._clearCountdown()
  },

  onUnload() {
    this._clearCountdown()
  },

  onPullDownRefresh() {
    this._loadTs = 0
    this._showTs = 0
    this.loadData({ force: true, callback: () => wx.stopPullDownRefresh() })
  },

  requestApi(options) {
    return sendRequest(options, {
      showLoading: false,
      showError: false
    })
  },

  // 有旧数据时的静默后台刷新：失败不显示任何错误
  _silentRefresh() {
    if (this.data.silentRefreshing) return
    this.setData({ silentRefreshing: true })
    this._doFetch().then(({ myResult, publicResult }) => {
      this._applyResults(myResult, publicResult, { silent: true })
    }).catch(() => {}).finally(() => {
      this.setData({ silentRefreshing: false })
    })
  },

  loadData({ force = false, callback } = {}) {
    const now = Date.now()
    if (!force && now - (this._loadTs || 0) < LOAD_DEDUPE_MS) {
      callback && callback()
      return
    }
    this._loadTs = now
    if (!this._hasData) {
      this.setData({ loadError: false })
    }

    // 带静默重试的加载
    const tryLoad = (remainRetry) => {
      this._doFetch().then(({ myResult, publicResult }) => {
        const bothFailed = !myResult.ok && !publicResult.ok
        if (bothFailed && remainRetry > 0) {
          // 静默重试一次
          setTimeout(() => tryLoad(remainRetry - 1), 1500)
          return
        }
        this._applyResults(myResult, publicResult, { silent: false })
        callback && callback()
      }).catch(() => {
        if (remainRetry > 0) {
          setTimeout(() => tryLoad(remainRetry - 1), 1500)
        } else {
          if (!this._hasData) this.setData({ loadError: true })
          this._loadTs = 0
          callback && callback()
        }
      })
    }

    tryLoad(SILENT_RETRY_TIMES)
  },

  _doFetch() {
    return Promise.all([
      this.requestApi({ url: '/api/guarantee/list?limit=20' })
        .then(v => ({ ok: true, v })).catch(() => ({ ok: false, v: null })),
      this.requestApi({ url: '/api/guarantee/public?limit=30' })
        .then(v => ({ ok: true, v })).catch(() => ({ ok: false, v: null }))
    ]).then(([myResult, publicResult]) => ({ myResult, publicResult }))
  },

  _applyResults(myResult, publicResult, { silent = false } = {}) {
    const nextData = {}

    if (myResult.ok) {
      const data = (myResult.v && myResult.v.data) || {}
      const wallet = data.wallet || {}
      const orders = Array.isArray(data.orders) ? data.orders.map(normalizeGuaranteeItem) : []
      nextData.gemBalance = Number(wallet.gemBalance || 0)
      nextData.guaranteeList = orders.slice(0, 3)
      this._hasData = true
    }

    if (publicResult.ok) {
      const orders = Array.isArray(((publicResult.v && publicResult.v.data) || {}).orders)
        ? ((publicResult.v && publicResult.v.data) || {}).orders.map(normalizeGuaranteeItem)
        : []
      this._allPublicOrders = orders
      const petSet = new Set()
      orders.forEach(o => { if (o.pet_name) petSet.add(o.pet_name) })
      nextData.publicPetTags = Array.from(petSet).slice(0, 8)
      nextData.publicOrders = orders
      nextData.publicFilterPet = ''
      this._hasData = true
      this._startCountdown()
    }

    const bothFailed = !myResult.ok && !publicResult.ok
    if (bothFailed) {
      // 有旧数据时静默失败，没有数据时才显示红条
      if (!this._hasData && !silent) {
        nextData.loadError = true
        this._loadTs = 0
      }
      // 有旧数据就保留原来内容，什么都不改
    } else {
      nextData.loadError = false
    }

    if (Object.keys(nextData).length) {
      this.setData(nextData)
    }
  },

  retryLoad() {
    this._loadTs = 0
    this._showTs = 0
    this._hasData = false
    this.loadData({ force: true })
  },

  refreshPublicOrders() {
    this._showTs = 0  // 手动刷新后重置 Tab 切换去重
    this.requestApi({ url: '/api/guarantee/public?limit=30' }).then(payload => {
      const orders = Array.isArray(((payload && payload.data) || {}).orders)
        ? ((payload && payload.data) || {}).orders.map(normalizeGuaranteeItem)
        : []
      this._allPublicOrders = orders
      const petSet = new Set()
      orders.forEach(o => { if (o.pet_name) petSet.add(o.pet_name) })
      this.setData({
        publicOrders: orders,
        publicPetTags: Array.from(petSet).slice(0, 8),
        publicFilterPet: ''
      })
      wx.showToast({ title: '已刷新', icon: 'success', duration: 800 })
      this._startCountdown()
    }).catch(() => {
      wx.showToast({ title: '刷新失败，请稍候', icon: 'none' })
    })
  },

  filterPublicPet(e) {
    const pet = e.currentTarget.dataset.pet || ''
    const all = this._allPublicOrders || []
    this.setData({
      publicFilterPet: pet,
      publicOrders: pet ? all.filter(o => o.pet_name === pet) : all
    })
  },

  goQueryWithId(e) {
    const id = e.currentTarget.dataset.id
    if (id) {
      wx.navigateTo({ url: `/pages/guarantee-order/guarantee-order?tab=query&orderId=${id}` })
    }
  },

  goRecharge() {
    wx.navigateTo({ url: '/pages/recharge/recharge' })
  },

  goCreateGuarantee() {
    const { gemBalance } = this.data
    if (gemBalance < 2) {
      wx.showModal({
        title: '余额不足',
        content: '发布保单时卖家至少要承担“挂单宝石 + 0.5 宝石卖家手续费”；买家到账时平台还会再扣 0.5 宝石手续费，请先转入后再发布。',
        confirmText: '去转入',
        success: res => {


          if (res.confirm) this.goRecharge()
        }
      })
      return
    }
    wx.navigateTo({ url: '/pages/guarantee-order/guarantee-order' })
  },

  goQueryOrder() {
    wx.navigateTo({ url: '/pages/guarantee-order/guarantee-order?tab=query' })
  },

  goRecords() {
    wx.navigateTo({ url: '/pages/guarantee-records/guarantee-records' })
  },

  goFlowGuide() {
    wx.pageScrollTo({ selector: '#flow-guide', duration: 400 })
  },

  // ─── 30分钟倒计时 ───────────────────────────────────────────────
  _startCountdown() {
    this._clearCountdown()
    this._countdownTimer = setInterval(() => {
      const orders = this.data.publicOrders
      if (!orders || !orders.length) return
      const now = Date.now()
      let changed = false
      const next = orders.map(o => {
        const ms = Number(o.expire_at_ms || 0) - now
        let text = ''
        if (ms > 0) {
          const m = Math.floor(ms / 60000)
          const s = Math.floor((ms % 60000) / 1000)
          text = `${m}:${String(s).padStart(2, '0')}`
        }
        if (text !== o.expireCountdown) { changed = true }
        return { ...o, expireCountdown: text }
      })
      if (changed) this.setData({ publicOrders: next })
    }, 1000)
  },

  _clearCountdown() {
    if (this._countdownTimer) {
      clearInterval(this._countdownTimer)
      this._countdownTimer = null
    }
  },

  onQueryInput(e) {
    this.setData({ queryOrderId: e.detail.value })
  },

  queryOrder() {
    const id = this.data.queryOrderId.trim()
    if (!id) {
      wx.showToast({ title: '请输入保单号', icon: 'none' })
      return
    }
    wx.navigateTo({ url: `/pages/guarantee-order/guarantee-order?tab=query&orderId=${id}` })
  },

  goDetail(e) {
    wx.navigateTo({ url: `/pages/guarantee-order/guarantee-order?id=${e.currentTarget.dataset.id}` })
  }
})
