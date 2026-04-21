const { requestApi: sendRequest } = require('../../utils/request')
const { ensureBeastId: ensureBeastIdGuard } = require('../../utils/user')
const {
  createPageLoadState,
  toErrorState,
  toSuccessState,
} = require('../../utils/page-load-state')


Page({
  data: {
    userInfo: {},
    balance: 0,
    lockedGems: 0,
    amount: '',
    remark: '',
    feeAmount: 0,
    actualAmount: 0,
    feeRateText: '0.5%',
    feeBasisPoints: 50,
    dailyLimit: 1,
    todayCount: 0,
    canCreate: false,
    pendingRequest: null,
    history: [],
    pageState: createPageLoadState('loading')
  },

  onLoad() {
    this._loadTs = 0
    this.loadData()
  },

  onShow() {
    if (Date.now() - (this._loadTs || 0) >= 1500) {
      this.loadData(true)
    }
  },

  requestApi(options) {
    return sendRequest(options, {
      showError: false
    })
  },


  loadData(silent = false) {
    this._loadTs = Date.now()
    this.requestApi({
      url: '/api/transfer/state?limit=20',
      showLoading: !silent,
      loadingText: '加载中...'
    }).then(payload => {
      this.applyState(payload.data || {})
    }).catch(error => {
      this.setData({ pageState: toErrorState(error.message || error || '??????????????') })
    })
  },

  applyState(serverData = {}) {
    const user = serverData.user || {}
    const wallet = serverData.wallet || {}
    const transfer = serverData.transfer || {}
    this.setData({
      userInfo: user,
      balance: Number(wallet.gemBalance || 0),
      lockedGems: Number(wallet.lockedGems || 0),
      feeRateText: transfer.feeRateText || '0.5%',
      feeBasisPoints: Number(transfer.feeBasisPoints || 50),
      dailyLimit: Number(transfer.dailyLimit || 1),
      todayCount: Number(transfer.todayCount || 0),
      canCreate: !!transfer.canCreate,
      pendingRequest: transfer.pendingRequest || null,
      history: Array.isArray(transfer.history) ? transfer.history : [],
      pageState: toSuccessState()
    })
    this.syncAmountMeta(this.data.amount)
  },

  retryLoadData() {
    this.loadData(false)
  },

  calculateFee(amount) {
    const numeric = Number(amount || 0)
    if (!numeric || numeric <= 0) {
      return 0
    }
    return Math.floor(numeric * Number(this.data.feeBasisPoints || 0) / 10000)
  },

  syncAmountMeta(rawValue) {
    const digits = String(rawValue || '').replace(/[^0-9]/g, '')
    const numeric = digits ? Number(digits) : 0
    const feeAmount = this.calculateFee(numeric)
    const actualAmount = Math.max(numeric - feeAmount, 0)
    this.setData({
      amount: digits,
      feeAmount,
      actualAmount
    })
  },

  onAmountInput(e) {
    this.syncAmountMeta(e.detail.value)
  },

  setMaxAmount() {
    this.syncAmountMeta(String(this.data.balance || 0))
  },

  onRemarkInput(e) {
    this.setData({ remark: String(e.detail.value || '').slice(0, 60) })
  },

  goProfile() {
    wx.navigateTo({ url: '/pages/profile/profile' })
  },

  ensureBeastId() {
    return ensureBeastIdGuard({
      userInfo: this.data.userInfo,
      content: '转出前请先去个人设置绑定方块兽ID，后台会按照这个ID人工处理你的转出申请。'
    })
  },


  showTutorial() {
    wx.showModal({
      title: '转出宝石说明',
      content: '1. 提交前请确认你绑定的是要收宝石的方块兽ID。\n2. 每个账号每天最多申请 10 次转出。\n3. 提交后宝石会先锁定，处理结果会显示为待处理、拒绝转出或已完成。\n4. 如果后台拒绝转出，锁定宝石会自动退回你的账户。\n5. 当前手续费为 0.5%，页面会自动显示预计实转数量。',

      showCancel: false
    })
  },

  submitTransfer() {
    const amount = Number(this.data.amount || 0)

    if (!this.ensureBeastId()) {
      return
    }

    if (!this.data.canCreate) {
      const message = this.data.pendingRequest
        ? '已有待处理的转出申请，请等待后台处理完成'
        : `当前账号今日已达到 ${this.data.dailyLimit} 次转出限制`
      wx.showToast({ title: message, icon: 'none' })
      return
    }

    if (!amount || amount <= 0) {
      wx.showToast({ title: '请输入正确的转出数量', icon: 'none' })
      return
    }

    if (amount > Number(this.data.balance || 0)) {
      wx.showToast({ title: '宝石余额不足', icon: 'none' })
      return
    }

    wx.showModal({
      title: '确认提交转出申请',
      content: `本次将锁定 ${amount} 宝石，预计实转 ${this.data.actualAmount} 宝石，手续费 ${this.data.feeAmount} 宝石。确认提交吗？`,
      success: res => {
        if (!res.confirm) {
          return
        }
        this.requestApi({
          url: '/api/transfer/create',
          method: 'POST',
          data: {
            amount,
            remark: this.data.remark
          },
          showLoading: true,
          loadingText: '提交中...'
        }).then(() => {
          wx.showToast({ title: '提交成功', icon: 'success' })
          this.setData({ amount: '', remark: '', feeAmount: 0, actualAmount: 0 })
          this.loadData(true)
        }).catch(error => {
          wx.showToast({ title: error.message || error || '提交失败', icon: 'none' })
        })
      }
    })
  }
})
