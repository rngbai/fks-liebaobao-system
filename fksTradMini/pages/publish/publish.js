const app = getApp()

Page({
  data: {
    form: {
      game_id_seller: '',
      game_id_buyer: '',
      back_gem: '',
      fee_gem: ''
    },
    totalGem: 0,
    screenshotUrl: '',
    agreed: false,
    canSubmit: false
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    const val = e.detail.value
    const form = { ...this.data.form, [field]: val }
    this.setData({ form }, () => this.checkSubmit())
  },

  onGemInput(e) {
    const field = e.currentTarget.dataset.field
    const val = e.detail.value.replace(/[^0-9]/g, '')
    const form = { ...this.data.form, [field]: val }
    const back = parseInt(form.back_gem) || 0
    const fee = parseInt(form.fee_gem) || 0
    this.setData({ form, totalGem: back + fee }, () => this.checkSubmit())
  },

  checkSubmit() {
    const { form, agreed, screenshotUrl } = this.data
    const canSubmit = !!(
      form.game_id_seller.trim() &&
      form.back_gem &&
      form.fee_gem &&
      screenshotUrl &&
      agreed
    )
    this.setData({ canSubmit })
  },

  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: res => {
        const tempFile = res.tempFiles[0].tempFilePath
        // 实际项目：上传到云存储/后端，获取url
        this.setData({ screenshotUrl: tempFile }, () => this.checkSubmit())
        // wx.uploadFile({ url: '...', filePath: tempFile, name: 'file', success: ... })
      }
    })
  },

  previewImage() {
    wx.previewImage({
      urls: [this.data.screenshotUrl],
      current: this.data.screenshotUrl
    })
  },

  toggleAgreement() {
    this.setData({ agreed: !this.data.agreed }, () => this.checkSubmit())
  },

  showRule() {
    wx.showModal({
      title: '担保交易规则',
      content: '1. 卖家需先押入约定宝石总额（返还+手续费）\n2. 买家确认收到宝石后，平台释放押金并扣除手续费\n3. 如有纠纷，双方可发起申诉，平台审核截图后处理\n4. 恶意欺诈将被封号处理',
      showCancel: false,
      confirmText: '我知道了'
    })
  },

  submitOrder() {
    if (!this.data.canSubmit) return

    const { form, totalGem, screenshotUrl } = this.data
    wx.showModal({
      title: '确认发布',
      content: `您需要押入 💎${totalGem} 宝石，确认发布担保单？`,
      confirmText: '确认发布',
      success: res => {
        if (!res.confirm) return
        wx.showLoading({ title: '发布中...' })

        // 实际接口提交
        // app.request({
        //   url: '/api/orders/create',
        //   method: 'POST',
        //   data: { ...form, total_gem: totalGem, screenshot: screenshotUrl },
        //   success: res => {
        //     wx.hideLoading()
        //     wx.navigateTo({ url: `/pages/detail/detail?id=${res.data.id}` })
        //   }
        // })

        // 模拟成功
        setTimeout(() => {
          wx.hideLoading()
          wx.showToast({ title: '发布成功', icon: 'success' })
          setTimeout(() => {
            wx.navigateBack()
          }, 1500)
        }, 800)
      }
    })
  }
})
