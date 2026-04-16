const app = getApp()

Page({
  data: {
    tabs: [
      { key: 'all', label: '全部' },
      { key: 'mine', label: '我的' }
    ],
    activeTab: 'all',
    typeOptions: ['Bug', '建议', '体验', '其他'],
    typeIndex: 0,
    title: '',
    desc: '',
    contact: '',
    showComposer: false,
    submitting: false,
    loading: false,
    list: [],
    feedbackMeta: {
      dailyLimit: 3,
      todayCount: 0,
      remainingCount: 3,
      mineOnly: false
    }
  },

  onLoad() {
    this.loadFeedbackList()
  },

  onShow() {
    this.loadFeedbackList({ silent: true })
  },

  onPullDownRefresh() {
    this.loadFeedbackList({ silent: true, stopRefresh: true })
  },

  loadFeedbackList({ tab, silent = false, stopRefresh = false } = {}) {
    const activeTab = tab || this.data.activeTab
    this.setData({
      activeTab,
      loading: !silent
    })

    return sendRequest({
      url: `/api/feedback/list?mine=${activeTab === 'mine' ? 1 : 0}&limit=50`,
      showLoading: !silent,
      loadingText: '加载反馈中...'
    }).then(payload => {

      const data = payload.data || {}
      const feedback = data.feedback || {}
      this.setData({
        list: feedback.list || [],
        feedbackMeta: {
          dailyLimit: Number(feedback.dailyLimit || 3),
          todayCount: Number(feedback.todayCount || 0),
          remainingCount: Number(feedback.remainingCount || 0),
          mineOnly: !!feedback.mineOnly
        }
      })
    }).catch(() => {
      if (!silent) {
        this.setData({ list: [] })
      }
    }).finally(() => {
      this.setData({ loading: false })
      if (stopRefresh) {
        wx.stopPullDownRefresh()
      }
    })
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    if (!tab || tab === this.data.activeTab) return
    this.loadFeedbackList({ tab })
  },

  openComposer() {
    if ((this.data.feedbackMeta.remainingCount || 0) <= 0) {
      wx.showToast({ title: '今天反馈次数已用完', icon: 'none' })
      return
    }
    this.setData({ showComposer: true })
  },

  closeComposer() {
    if (this.data.submitting) return
    this.setData({ showComposer: false })
  },

  noop() {},

  onTypeChange(e) {
    this.setData({ typeIndex: parseInt(e.detail.value, 10) || 0 })
  },

  onTitleInput(e) {
    this.setData({ title: e.detail.value })
  },

  onDescInput(e) {
    this.setData({ desc: e.detail.value })
  },

  onContactInput(e) {
    this.setData({ contact: e.detail.value })
  },

  resetForm() {
    this.setData({
      typeIndex: 0,
      title: '',
      desc: '',
      contact: '',
      showComposer: false,
      submitting: false
    })
  },

  submitFeedback() {
    if (this.data.submitting) return

    const title = String(this.data.title || '').trim()
    const desc = String(this.data.desc || '').trim()
    const contact = String(this.data.contact || '').trim()
    const type = this.data.typeOptions[this.data.typeIndex] || '其他'

    if (title.length < 2) {
      wx.showToast({ title: '请填写反馈标题', icon: 'none' })
      return
    }

    if (desc.length < 5) {
      wx.showToast({ title: '请至少描述 5 个字', icon: 'none' })
      return
    }

    this.setData({ submitting: true })

    sendRequest({
      url: '/api/feedback/create',
      method: 'POST',
      data: {
        type,
        title,
        content: desc,
        contact,
        limit: 50
      },
      loadingText: '提交反馈中...'
    }).then(payload => {

      const data = payload.data || {}
      const feedback = data.feedback || {}
      wx.showToast({ title: '反馈提交成功', icon: 'success' })
      this.resetForm()
      this.setData({
        activeTab: 'mine',
        list: feedback.list || [],
        feedbackMeta: {
          dailyLimit: Number(feedback.dailyLimit || 3),
          todayCount: Number(feedback.todayCount || 0),
          remainingCount: Number(feedback.remainingCount || 0),
          mineOnly: false
        }
      })
      this.loadFeedbackList({ tab: 'mine', silent: true })
    }).catch(() => {
      this.setData({ submitting: false })
    })
  }
})
