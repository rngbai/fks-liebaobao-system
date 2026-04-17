const { requestApi: sendRequest } = require('../../utils/request')

const DEFAULT_TYPE_OPTIONS = ['Bug', '建议', '体验', '其他']
const COMMUNITY_APPLY_SCENE = 'community_apply'
const COMMUNITY_APPLY_TYPE = '社区认证申请'

function trimText(value) {
  return String(value || '').trim()
}

function decodeParam(value) {
  const raw = trimText(value)
  if (!raw) return ''
  try {
    return decodeURIComponent(raw)
  } catch (error) {
    return raw
  }
}

function normalizeScene(value) {
  return trimText(value).toLowerCase().replace(/-/g, '_')
}

function buildCommunityApplyTitle(categoryLabel, subTab) {
  const targetLabel = [trimText(categoryLabel), trimText(subTab)].filter(Boolean).join(' · ')
  return targetLabel ? `申请加入 ${targetLabel}` : '申请加入社区名流'
}

function buildTipsText(sceneMode, dailyLimit) {
  return sceneMode
    ? `为避免恶意认证，社区名流申请每天最多可提交 ${dailyLimit} 次，提交后会进入人工审核。`
    : `为避免恶意刷屏，单个用户每天最多可提交 ${dailyLimit} 次反馈。`
}

function resolveTypeClass(type, scene) {
  const normalizedType = trimText(type)
  if (normalizeScene(scene) === COMMUNITY_APPLY_SCENE || normalizedType === COMMUNITY_APPLY_TYPE) {
    return 'community'
  }
  if (normalizedType === 'Bug') {
    return 'bug'
  }
  return 'suggest'
}

function decorateFeedbackList(list, scene) {
  return (Array.isArray(list) ? list : []).map(item => ({
    ...item,
    typeClass: resolveTypeClass(item.type, scene)
  }))
}

function buildSceneConfig(options = {}) {
  const scene = normalizeScene(options.scene)
  const category = trimText(options.category)
  const categoryLabel = decodeParam(options.category_label || options.categoryLabel || '')
  const subTab = decodeParam(options.sub_tab || options.subTab || '')

  if (scene === COMMUNITY_APPLY_SCENE) {
    const targetLabel = [categoryLabel, subTab].filter(Boolean).join(' · ') || '社区名流'
    return {
      scene,
      sceneMode: true,
      category,
      categoryLabel,
      subTab,
      targetLabel,
      pageTitle: '名流认证申请',
      pageSubtitle: '提交真实资料后进入人工审核，通过后会展示到对应板块。',
      sceneBadgeList: ['人工审核', '当天最多 2 次', '审核通过后展示'],
      tabs: [{ key: 'mine', label: '我的申请' }],
      activeTab: 'mine',
      typeOptions: [COMMUNITY_APPLY_TYPE],
      typeIndex: 0,
      presetType: COMMUNITY_APPLY_TYPE,
      title: buildCommunityApplyTitle(categoryLabel, subTab),
      tipsText: buildTipsText(true, 2),
      emptyTitleAll: '暂时还没有认证申请',
      emptyTitleMine: '你还没有提交过认证申请',
      emptySub: '点击下方按钮提交资料，我们会尽快审核。',
      composerTitle: '提交认证申请',
      titlePlaceholder: '例如：申请加入 大咖团队长 · 地球猎人',
      descPlaceholder: '请填写你的擅长领域、服务内容、交易经验、为什么值得被认证等，建议至少 10 个字。',
      contactPlaceholder: '请填写微信 / QQ / 手机号，方便审核联系',
      submitButtonText: '提交申请',
      submitSuccessText: '认证申请已提交',
      limitReachedText: '今天认证申请次数已用完',
      loadingText: '提交申请中...',
      navigationBarTitle: '名流申请'
    }
  }

  return {
    scene: '',
    sceneMode: false,
    category: '',
    categoryLabel: '',
    subTab: '',
    targetLabel: '',
    pageTitle: '问题反馈',
    pageSubtitle: '你的每条建议和 Bug 反馈，我们都会认真处理。',
    sceneBadgeList: [],
    tabs: [
      { key: 'all', label: '全部' },
      { key: 'mine', label: '我的' }
    ],
    activeTab: 'all',
    typeOptions: DEFAULT_TYPE_OPTIONS,
    typeIndex: 0,
    presetType: '',
    title: '',
    tipsText: buildTipsText(false, 3),
    emptyTitleAll: '暂时还没有反馈内容',
    emptyTitleMine: '你还没有提交过反馈',
    emptySub: '点击右下角按钮，告诉我们你遇到的问题或建议。',
    composerTitle: '提交反馈',
    titlePlaceholder: '例如：技能数据不对 / 增加某个功能',
    descPlaceholder: '请尽量写清楚问题现象、出现位置、希望如何优化...',
    contactPlaceholder: 'QQ / 微信 / 手机号，方便我们联系你',
    submitButtonText: '确认提交',
    submitSuccessText: '反馈提交成功',
    limitReachedText: '今天反馈次数已用完',
    loadingText: '提交反馈中...',
    navigationBarTitle: '问题反馈'
  }
}

const DEFAULT_SCENE_CONFIG = buildSceneConfig()

Page({
  data: {
    ...DEFAULT_SCENE_CONFIG,
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

  onLoad(options = {}) {
    const sceneConfig = buildSceneConfig(options)
    this.setData({
      ...sceneConfig,
      feedbackMeta: {
        dailyLimit: sceneConfig.sceneMode ? 2 : 3,
        todayCount: 0,
        remainingCount: sceneConfig.sceneMode ? 2 : 3,
        mineOnly: !!sceneConfig.sceneMode
      }
    })

    if (sceneConfig.navigationBarTitle) {
      wx.setNavigationBarTitle({ title: sceneConfig.navigationBarTitle })
    }

    this.loadFeedbackList({ tab: sceneConfig.activeTab })
  },

  onShow() {
    this.loadFeedbackList({ tab: this.data.sceneMode ? 'mine' : this.data.activeTab, silent: true })
  },

  onPullDownRefresh() {
    this.loadFeedbackList({ tab: this.data.sceneMode ? 'mine' : this.data.activeTab, silent: true, stopRefresh: true })
  },

  loadFeedbackList({ tab, silent = false, stopRefresh = false } = {}) {
    const activeTab = this.data.sceneMode ? 'mine' : (tab || this.data.activeTab)
    const query = [
      `mine=${activeTab === 'mine' ? 1 : 0}`,
      'limit=50'
    ]

    if (this.data.scene) {
      query.push(`scene=${encodeURIComponent(this.data.scene)}`)
    }
    if (this.data.presetType) {
      query.push(`type=${encodeURIComponent(this.data.presetType)}`)
    }

    this.setData({
      activeTab,
      loading: !silent
    })

    return sendRequest({
      url: `/api/feedback/list?${query.join('&')}`,
      showLoading: !silent,
      loadingText: this.data.sceneMode ? '加载申请记录中...' : '加载反馈中...'
    }).then(payload => {
      const data = payload.data || {}
      const feedback = data.feedback || {}
      const dailyLimit = Number(feedback.dailyLimit || (this.data.sceneMode ? 2 : 3))
      const todayCount = Number(feedback.todayCount || 0)
      const remainingCount = Number(feedback.remainingCount || 0)

      this.setData({
        list: decorateFeedbackList(feedback.list || [], this.data.scene),
        feedbackMeta: {
          dailyLimit,
          todayCount,
          remainingCount,
          mineOnly: !!feedback.mineOnly
        },
        tipsText: buildTipsText(this.data.sceneMode, dailyLimit)
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
    if (this.data.sceneMode) return
    const tab = e.currentTarget.dataset.tab
    if (!tab || tab === this.data.activeTab) return
    this.loadFeedbackList({ tab })
  },

  openComposer() {
    if ((this.data.feedbackMeta.remainingCount || 0) <= 0) {
      wx.showToast({ title: this.data.limitReachedText, icon: 'none' })
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
    if (this.data.sceneMode) return
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
      title: this.data.sceneMode ? buildCommunityApplyTitle(this.data.categoryLabel, this.data.subTab) : '',
      desc: '',
      contact: '',
      showComposer: false,
      submitting: false
    })
  },

  submitFeedback() {
    if (this.data.submitting) return

    const title = trimText(this.data.title)
    const desc = trimText(this.data.desc)
    const contact = trimText(this.data.contact)
    const type = this.data.sceneMode ? this.data.presetType : (this.data.typeOptions[this.data.typeIndex] || '其他')

    if (title.length < 2) {
      wx.showToast({ title: '请填写反馈标题', icon: 'none' })
      return
    }

    if (this.data.sceneMode) {
      if (desc.length < 10) {
        wx.showToast({ title: '申请说明至少 10 个字', icon: 'none' })
        return
      }
      if (contact.length < 2) {
        wx.showToast({ title: '请填写联系方式', icon: 'none' })
        return
      }
    } else if (desc.length < 5) {
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
        limit: 50,
        scene: this.data.scene,
        category: this.data.category,
        category_label: this.data.categoryLabel,
        sub_tab: this.data.subTab
      },
      loadingText: this.data.loadingText
    }).then(payload => {
      const data = payload.data || {}
      const feedback = data.feedback || {}
      const dailyLimit = Number(feedback.dailyLimit || this.data.feedbackMeta.dailyLimit || (this.data.sceneMode ? 2 : 3))

      wx.showToast({ title: this.data.submitSuccessText, icon: 'success' })
      this.resetForm()
      this.setData({
        activeTab: 'mine',
        list: decorateFeedbackList(feedback.list || [], this.data.scene),
        feedbackMeta: {
          dailyLimit,
          todayCount: Number(feedback.todayCount || 0),
          remainingCount: Number(feedback.remainingCount || 0),
          mineOnly: this.data.sceneMode ? true : !!feedback.mineOnly
        },
        tipsText: buildTipsText(this.data.sceneMode, dailyLimit)
      })
      this.loadFeedbackList({ tab: 'mine', silent: true })
    }).catch(() => {
      this.setData({ submitting: false })
    })
  }
})
