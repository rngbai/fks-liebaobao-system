const { requestApi: sendRequest } = require('../../utils/request')
const { normalizeGuaranteeItem } = require('../../utils/guarantee')



Page({
  data: {
    filterStatus: -1,
    list: [],
    allList: [],
    statusText: ['待买家匹配', '待卖家确认', '已完成', '申诉中']
  },

  onLoad() {
    this.loadList()
  },

  onShow() {
    this.loadList()
  },

  onPullDownRefresh() {
    this.loadList(() => wx.stopPullDownRefresh())
  },

  requestApi(options) {
    return sendRequest(options, {
      showLoading: false,
      showError: false
    })
  },


  setFilter(e) {
    this.setData({ filterStatus: parseInt(e.currentTarget.dataset.s, 10) }, () => this.applyFilter())
  },

  applyFilter() {
    const { filterStatus, allList } = this.data
    const list = filterStatus === -1 ? allList : allList.filter(item => item.status === filterStatus)
    this.setData({ list })
  },

  loadList(cb) {
    this.requestApi({ url: '/api/guarantee/list?limit=50' }).then(payload => {
      const data = payload.data || {}
      const allList = Array.isArray(data.orders) ? data.orders.map(normalizeGuaranteeItem) : []
      this.setData({ allList }, () => this.applyFilter())
      cb && cb()
    }).catch(() => {
      this.setData({ list: [], allList: [] })
      cb && cb()
    })
  },

  goDetail(e) {
    wx.navigateTo({ url: `/pages/guarantee-order/guarantee-order?id=${e.currentTarget.dataset.id}` })
  }
})
