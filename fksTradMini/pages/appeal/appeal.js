const app = getApp()

Page({
  data: {
    orderId: '',
    appealReason: '',
    description: '',
    appealImages: [],
    reasons: [
      '已转账但未确认',
      '买家未转账',
      '金额有误',
      '对方失联',
      '其他问题'
    ],
    canSubmit: false
  },

  onLoad(options) {
    this.setData({ orderId: options.id || '' })
  },

  selectReason(e) {
    this.setData({ appealReason: e.currentTarget.dataset.reason }, () => this.checkSubmit())
  },

  onDescInput(e) {
    this.setData({ description: e.detail.value }, () => this.checkSubmit())
  },

  checkSubmit() {
    const { appealReason, description } = this.data
    this.setData({ canSubmit: !!(appealReason && description.trim().length >= 10) })
  },

  addImage() {
    wx.chooseMedia({
      count: 3 - this.data.appealImages.length,
      mediaType: ['image'],
      success: res => {
        const newUrls = res.tempFiles.map(f => f.tempFilePath)
        this.setData({ appealImages: [...this.data.appealImages, ...newUrls] })
      }
    })
  },

  previewImg(e) {
    wx.previewImage({ urls: this.data.appealImages, current: e.currentTarget.dataset.src })
  },

  delImg(e) {
    const list = [...this.data.appealImages]
    list.splice(e.currentTarget.dataset.index, 1)
    this.setData({ appealImages: list })
  },

  submitAppeal() {
    if (!this.data.canSubmit) return
    wx.showModal({
      title: '确认提交申诉',
      content: '提交后平台将介入处理，请确保信息真实',
      confirmText: '确认提交',
      confirmColor: '#FF5252',
      success: res => {
        if (!res.confirm) return
        wx.showLoading({ title: '提交中...' })
        // app.request({
        //   url: '/api/appeals/create',
        //   method: 'POST',
        //   data: {
        //     order_id: this.data.orderId,
        //     reason: this.data.appealReason,
        //     description: this.data.description,
        //     images: this.data.appealImages
        //   },
        //   success: () => { wx.hideLoading(); wx.navigateBack() }
        // })
        setTimeout(() => {
          wx.hideLoading()
          wx.showToast({ title: '申诉已提交', icon: 'success' })
          setTimeout(() => wx.navigateBack(), 1500)
        }, 800)
      }
    })
  }
})
