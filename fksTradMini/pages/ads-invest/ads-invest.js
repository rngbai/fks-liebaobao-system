Page({
  data: { form: { title: '', sub: '', contact: '' } },
  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: e.detail.value })
  },
  submitAds() {
    const { form } = this.data
    if (!form.title || !form.contact) {
      wx.showToast({ title: '请填写广告标题和联系方式', icon: 'none' })
      return
    }
    wx.showModal({
      title: '提交成功',
      content: '广告申请已提交，管理员审核后将联系您确认价格和上线时间',
      showCancel: false, confirmText: '知道了'
    })
  }
})
