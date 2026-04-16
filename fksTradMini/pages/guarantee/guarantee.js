const { requestApi: sendRequest } = require('../../utils/request')
const { normalizeGuaranteeItem } = require('../../utils/guarantee')


Page({
  data: {
    gemBalance: 0,
    queryOrderId: '',
    guaranteeList: [],
    publicOrders: [],
    publicPetTags: [],
    publicFilterPet: '',
    statusText: ['待买家匹配', '待卖家确认', '已完成', '申诉中']
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  onPullDownRefresh() {
    this.loadData(() => wx.stopPullDownRefresh())
  },

  requestApi(options) {
    return sendRequest(options, {
      showLoading: false,
      showError: false
    })
  },

  loadData(callback) {
    Promise.all([
      this.requestApi({ url: '/api/guarantee/list?limit=20' })
        .then(v => ({ ok: true, v })).catch(() => ({ ok: false })),
      this.requestApi({ url: '/api/guarantee/public?limit=30' })
        .then(v => ({ ok: true, v })).catch(() => ({ ok: false }))
    ]).then(([myResult, publicResult]) => {
      const nextData = {}
      if (myResult.ok) {
        const data = myResult.v.data || {}
        const wallet = data.wallet || {}
        const orders = Array.isArray(data.orders) ? data.orders.map(normalizeGuaranteeItem) : []
        nextData.gemBalance = Number(wallet.gemBalance || 0)
        nextData.guaranteeList = orders.slice(0, 3)
      }
      if (publicResult.ok) {
        const orders = Array.isArray((publicResult.v.data || {}).orders)
          ? (publicResult.v.data || {}).orders.map(normalizeGuaranteeItem)
          : []
        this._allPublicOrders = orders
        const petSet = new Set()
        orders.forEach(o => { if (o.pet_name) petSet.add(o.pet_name) })
        nextData.publicPetTags = Array.from(petSet).slice(0, 8)
        nextData.publicOrders = orders
        nextData.publicFilterPet = ''
      }
      this.setData(nextData)
      callback && callback()
    })
  },

  refreshPublicOrders() {
    this.requestApi({ url: '/api/guarantee/public?limit=30' }).then(payload => {
      const orders = Array.isArray((payload.data || {}).orders)
        ? (payload.data || {}).orders.map(normalizeGuaranteeItem)
        : []
      this._allPublicOrders = orders
      const petSet = new Set()
      orders.forEach(o => { if (o.pet_name) petSet.add(o.pet_name) })
      this.setData({
        publicOrders: orders,
        publicPetTags: Array.from(petSet).slice(0, 8),
        publicFilterPet: ''
      })
    }).catch(() => {})
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
        content: '发布保单时卖家至少要承担“挂单宝石 + 1 宝石卖家手续费”；买家到账时平台还会再扣 1 宝石手续费，请先转入后再发布。',
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
