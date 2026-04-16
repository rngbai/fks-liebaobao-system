const app = getApp()

Page({
  data: {
    publishType: 'sell',
    form: { title: '', quantity: '', price_per: '', qq: '', wechat: '', desc: '' },
    canSubmit: false
  },

  onLoad(options) {
    if (options.type) this.setData({ publishType: options.type })
  },

  setType(e) {
    this.setData({ publishType: e.currentTarget.dataset.type })
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    const form = { ...this.data.form, [field]: e.detail.value }
    this.setData({ form }, () => this.check())
  },

  check() {
    const { form } = this.data
    this.setData({ canSubmit: !!(form.title.trim() && form.quantity && form.price_per && form.qq) })
  },

  submitPublish() {
    if (!this.data.canSubmit) return
    wx.showLoading({ title: '发布中...' })
    setTimeout(() => {
      wx.hideLoading()
      wx.showToast({ title: '发布成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1200)
    }, 800)

    // 实际接口:
    // app.request({
    //   url: '/api/market/publish',
    //   method: 'POST',
    //   data: { type: this.data.publishType, ...this.data.form },
    //   success: () => { wx.hideLoading(); wx.showToast({ title: '发布成功', icon: 'success' }); setTimeout(() => wx.navigateBack(), 1200) }
    // })
  }
})
