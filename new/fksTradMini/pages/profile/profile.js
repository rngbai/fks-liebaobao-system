const app = getApp()
const { requestApi: sendRequest } = require('../../utils/request')

const DEFAULT_FORM = {
  avatarUrl: '',
  nickName: '',
  account: '',
  phone: '',
  email: '',
  beastId: ''
}

function normalizeProfileForm(form = {}) {
  return {
    ...DEFAULT_FORM,
    ...form,
    avatarUrl: String(form.avatarUrl || '').trim(),
    nickName: String(form.nickName || '').trim(),
    account: String(form.account || '').trim(),
    phone: String(form.phone || '').trim(),
    email: String(form.email || '').trim(),
    beastId: String(form.beastId || '').trim()
  }
}

Page({
  data: {
    form: DEFAULT_FORM
  },

  onLoad() {
    const saved = normalizeProfileForm(wx.getStorageSync('userInfo') || {})
    this.setData({ form: saved })

    sendRequest({
      url: '/api/user/profile',
      showLoading: false,
      showError: false
    }).then(payload => {
      const remoteUser = (payload.data && payload.data.user) || {}
      const form = normalizeProfileForm({ ...saved, ...remoteUser })
      this.setData({ form })
      wx.setStorageSync('userInfo', form)
      app.globalData.userInfo = form
    }).catch(() => {})
  },

  onChooseAvatar(e) {
    const avatarUrl = String((e.detail && e.detail.avatarUrl) || '').trim()
    if (!avatarUrl) {
      return
    }
    this.setData({ 'form.avatarUrl': avatarUrl })
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: String(e.detail.value || '') })
  },


  changePassword() {
    wx.showModal({
      title: '修改密码',
      content: '密码修改功能需要绑定手机号验证，请在绑定手机号后使用',
      showCancel: false,
      confirmText: '知道了'
    })
  },

  saveProfile() {
    const form = normalizeProfileForm(this.data.form)
    if (!form.nickName) {
      wx.showToast({ title: '请填写昵称', icon: 'none' })
      return
    }

    sendRequest({
      url: '/api/user/profile',
      method: 'POST',
      data: form,
      showLoading: true,
      loadingText: '保存中...',
      showError: false
    }).then(payload => {
      const nextForm = normalizeProfileForm((payload.data && payload.data.user) || form)
      this.setData({ form: nextForm })
      wx.setStorageSync('userInfo', nextForm)
      app.globalData.userInfo = nextForm
      wx.showToast({ title: '保存成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1200)
    }).catch(error => {
      wx.showToast({ title: error.message || error || '保存失败', icon: 'none' })
    })
  }
})

