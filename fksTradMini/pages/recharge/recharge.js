const { requestApi: sendRequest } = require('../../utils/request')
const {
  createPageLoadState,
  toErrorState,
  toSuccessState,
} = require('../../utils/page-load-state')


const ORDER_EXPIRE_MS = 10 * 60 * 1000
const CANCEL_LIMIT = 5
const DEFAULT_BEAST_INFO = {
  id: '9100503',
  nick: '面板小助手'
}

function pad(num) {
  return String(num).padStart(2, '0')
}

function formatCountdown(ms) {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${pad(minutes)}:${pad(seconds)}`
}

function formatHistoryTime(ts) {
  const ms = Number(ts || 0)
  if (!ms) return ''
  const date = new Date(ms)
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function getHistoryMeta(status) {
  const map = {
    success: {
      statusText: '已到账',
      statusClass: 'success',
      desc: '时间后四位验证通过',
      amountPrefix: '+'
    },
    cancelled: {
      statusText: '已取消',
      statusClass: 'cancelled',
      desc: '用户主动取消订单',
      amountPrefix: ''
    },
    expired: {
      statusText: '已超时',
      statusClass: 'expired',
      desc: '10分钟内未完成验证',
      amountPrefix: ''
    }
  }
  return map[status] || map.success
}

function normalizeOrder(order) {
  if (!order || !order.id) {
    return null
  }
  const createdAt = Number(order.createdAt || order.created_at_ms || 0)
  const expireAt = Number(order.expireAt || order.expire_at_ms || 0)
  return {
    id: order.id,
    amount: Number(order.amount || 0),
    beastId: order.beastId || order.beast_id || DEFAULT_BEAST_INFO.id,
    beastNick: order.beastNick || order.beast_nick || DEFAULT_BEAST_INFO.nick,
    status: order.status || 'pending',
    createdAt,
    expireAt,
    createdTimeText: order.createdTimeText || formatHistoryTime(createdAt)
  }
}

Page({
  data: {
    gemBalance: 0,
    currentStep: 1,
    rechargeAmount: '',
    rechargeOrderId: '',
    verifyCode: '',
    quickAmounts: [50, 100, 168, 171, 200, 500],
    appBeastId: DEFAULT_BEAST_INFO.id,
    appBeastNick: DEFAULT_BEAST_INFO.nick,
    rechargeHistory: [],
    currentOrder: null,
    countdownText: '10:00',
    createdTimeText: '',
    matchedLogTime: '',
    cancelCount: 0,
    cancelLimit: CANCEL_LIMIT,
    cancelRemain: CANCEL_LIMIT,
    orderExpireMinutes: ORDER_EXPIRE_MS / 60000,
    verifyModeText: 'MySQL真实校验模式',
    pageState: createPageLoadState('loading')
  },

  onLoad() {
    this._loadTs = 0
    this.loadRechargeState(true)
  },

  onShow() {
    if (Date.now() - (this._loadTs || 0) >= 1500) {
      this.loadRechargeState(true)
    }
    this.checkClipboardForTimeCode()
  },

  checkClipboardForTimeCode() {
    if (this.data.currentStep !== 2) return
    wx.getClipboardData({
      success: (res) => {
        const text = (res.data || '').trim()
        const timeMatch = text.match(/(\d{1,2}):(\d{2}):(\d{2})/)
        if (timeMatch) {
          const code = timeMatch[2] + timeMatch[3]
          wx.showModal({
            title: '检测到交易时间',
            content: `剪贴板中包含时间 ${timeMatch[0]}，提取后 4 位为 ${code}，是否直接填入验证？`,
            confirmText: '填入验证',
            success: (modalRes) => {
              if (modalRes.confirm) {
                this.setData({ verifyCode: code })
              }
            }
          })
        }
      },
      fail: () => {}
    })
  },

  retryLoadRechargeState() {
    this.loadRechargeState(false)
  },

  onHide() {
    this.clearTimer()
  },

  onUnload() {
    this.clearTimer()
  },

  requestApi(options) {
    return sendRequest(options, {
      showError: false
    })
  },


  mapHistoryItem(item) {
    const status = item.status || 'success'
    const meta = getHistoryMeta(status)
    return {
      id: item.id,
      amount: Number(item.amount || 0),
      amountPrefix: item.amountPrefix !== undefined ? item.amountPrefix : meta.amountPrefix,
      time: item.time || '',
      statusText: item.statusText || meta.statusText,
      statusClass: item.statusClass || meta.statusClass,
      desc: item.desc || meta.desc
    }
  },

  applyState(serverData, options = {}) {
    const wallet = serverData.wallet || {}
    const recharge = serverData.recharge || {}
    const cancelLimit = Number(recharge.cancelLimit || CANCEL_LIMIT)
    const cancelCount = Number(recharge.cancelCount || 0)
    const pendingOrder = normalizeOrder(recharge.pendingOrder)
    const history = Array.isArray(recharge.history) ? recharge.history.map(item => this.mapHistoryItem(item)) : []

    const nextData = {
      gemBalance: Number(wallet.gemBalance || 0),
      rechargeHistory: history,
      cancelCount,
      cancelLimit,
      cancelRemain: Math.max(0, cancelLimit - cancelCount),
      appBeastId: recharge.receiverBeastId || DEFAULT_BEAST_INFO.id,
      appBeastNick: recharge.receiverBeastNick || DEFAULT_BEAST_INFO.nick
    }

    if (pendingOrder) {
      Object.assign(nextData, {
        currentStep: 2,
        currentOrder: pendingOrder,
        rechargeAmount: pendingOrder.amount,
        rechargeOrderId: pendingOrder.id,
        createdTimeText: pendingOrder.createdTimeText,
        matchedLogTime: '',
        verifyCode: options.keepVerifyCode ? this.data.verifyCode : ''
      })
      this.setData({
        ...nextData,
        pageState: toSuccessState()
      })
      this.startCountdown(pendingOrder)
      return
    }

    this.clearTimer()
    if (!options.keepSuccessStep) {
      Object.assign(nextData, {
        currentStep: 1,
        currentOrder: null,
        rechargeOrderId: '',
        countdownText: '10:00',
        createdTimeText: '',
        matchedLogTime: '',
        verifyCode: ''
      })
    }
    this.setData({
      ...nextData,
      pageState: toSuccessState()
    })
  },

  loadRechargeState(silent = false) {
    this._loadTs = Date.now()
    this.requestApi({
      url: '/api/recharge/state',
      showLoading: !silent,
      loadingText: '加载中...'
    }).then(payload => {
      this.applyState(payload.data || {})
    }).catch(error => {
      this.setData({ pageState: toErrorState(error.message || error || '??????????????') })
    })
  },

  onAmountInput(e) {
    const value = e.detail.value.replace(/[^0-9]/g, '')
    this.setData({ rechargeAmount: value ? Number(value) : '' })
  },

  setQuickAmount(e) {
    this.setData({ rechargeAmount: Number(e.currentTarget.dataset.val) })
  },

  createRechargeOrder() {
    const { rechargeAmount, cancelCount, cancelLimit, appBeastId, appBeastNick } = this.data
    const amount = Number(rechargeAmount)

    if (cancelCount >= cancelLimit) {
      wx.showModal({
        title: '无法继续转入',
        content: `您已累计取消 ${cancelLimit} 次转入订单，当前账号已达到限制，请联系管理员处理。`,
        showCancel: false
      })
      return
    }

    if (!amount || amount <= 0) {
      wx.showToast({ title: '请输入正确的转入数量', icon: 'none' })
      return
    }

    this.requestApi({
      url: '/api/recharge/create',
      method: 'POST',
      data: {
        amount,
        beast_id: appBeastId,
        beast_nick: appBeastNick
      },
      showLoading: true,
      loadingText: '创建中...'
    }).then(payload => {
      this.applyState(payload.data || {})
      wx.showToast({ title: '订单已创建', icon: 'success' })
    }).catch(error => {
      wx.showToast({ title: error.message || error || '创建订单失败', icon: 'none' })
    })
  },

  startCountdown(order) {
    this.clearTimer()

    const tick = () => {
      const remain = Number(order.expireAt || 0) - Date.now()
      if (remain <= 0) {
        this.handleExpiredOrder(false)
        return
      }
      this.setData({ countdownText: formatCountdown(remain) })
    }

    tick()
    this.countdownTimer = setInterval(tick, 1000)
  },

  clearTimer() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
      this.countdownTimer = null
    }
  },

  handleExpiredOrder(silent) {
    this.clearTimer()
    this.requestApi({ url: '/api/recharge/state', showLoading: false }).then(payload => {
      this.applyState(payload.data || {})
      if (!silent) {
        wx.showToast({ title: '订单已超时失效', icon: 'none' })
      }
    }).catch(() => {
      if (!silent) {
        wx.showToast({ title: '订单已超时失效', icon: 'none' })
      }
    })
  },

  onVerifyInput(e) {
    const raw = e.detail.value || ''
    const timeMatch = raw.match(/(\d{1,2}):(\d{2}):(\d{2})/)
    if (timeMatch) {
      const extracted = timeMatch[2] + timeMatch[3]
      this.setData({ verifyCode: extracted.slice(0, 4) })
      wx.showToast({ title: `已自动提取: ${extracted.slice(0, 4)}`, icon: 'none', duration: 1500 })
      return
    }
    const value = raw.replace(/[^0-9]/g, '').slice(0, 4)
    this.setData({ verifyCode: value })
  },

  verifyOrder() {
    const { verifyCode, currentOrder } = this.data

    if (!currentOrder || !currentOrder.id) {
      wx.showToast({ title: '请先创建转入订单', icon: 'none' })
      return
    }

    if (Date.now() >= Number(currentOrder.expireAt || 0)) {
      this.handleExpiredOrder(false)
      return
    }

    if (verifyCode.length !== 4) {
      wx.showToast({ title: '请输入时间后4位数字', icon: 'none' })
      return
    }

    this.requestApi({
      url: '/api/recharge/verify',
      method: 'POST',
      data: {
        order_id: currentOrder.id,
        verify_code: verifyCode,
        expire_minutes: this.data.orderExpireMinutes
      },
      showLoading: true,
      loadingText: '验证中...'
    }).then(payload => {
      const data = payload.data || {}
      const matchedLog = data.matched || {}
      const recharge = data.recharge || {}
      const history = Array.isArray(recharge.history) ? recharge.history.map(item => this.mapHistoryItem(item)) : this.data.rechargeHistory
      const cancelLimit = Number(recharge.cancelLimit || this.data.cancelLimit)
      const cancelCount = Number(recharge.cancelCount || this.data.cancelCount)
      const newBalance = Number(data.newBalance !== undefined ? data.newBalance : this.data.gemBalance)

      this.clearTimer()
      this.setData({
        gemBalance: newBalance,
        rechargeHistory: history,
        cancelCount,
        cancelLimit,
        cancelRemain: Math.max(0, cancelLimit - cancelCount),
        currentStep: 3,
        currentOrder: null,
        rechargeAmount: currentOrder.amount,
        rechargeOrderId: '',
        verifyCode: '',
        matchedLogTime: matchedLog.datetime || ''
      })
    }).catch(error => {
      const message = error.message || error || '校验失败'
      wx.showToast({ title: message, icon: 'none' })
      if (message.includes('超时') || message.includes('失效')) {
        this.loadRechargeState(true)
      }
    })
  },

  cancelRechargeOrder() {
    const { currentOrder, cancelCount, cancelLimit } = this.data
    if (!currentOrder || !currentOrder.id) {
      return
    }

    wx.showModal({
      title: '取消转入订单',
      content: `取消后本单作废，且会累计取消次数（${cancelCount}/${cancelLimit}）。确认取消吗？`,
      success: res => {
        if (!res.confirm) {
          return
        }

        this.requestApi({
          url: '/api/recharge/cancel',
          method: 'POST',
          data: { order_id: currentOrder.id },
          showLoading: true,
          loadingText: '取消中...'
        }).then(payload => {
          this.applyState(payload.data || {})
          this.resetToCreateState(true)
          if (this.data.cancelCount >= this.data.cancelLimit) {
            wx.showModal({
              title: '已达到取消上限',
              content: '您已累计取消 5 次，当前账号不能再发起转入订单，请联系管理员处理。',
              showCancel: false
            })
            return
          }
          wx.showToast({ title: '订单已取消', icon: 'none' })
        }).catch(error => {
          wx.showToast({ title: error.message || error || '取消订单失败', icon: 'none' })
        })
      }
    })
  },

  resetToCreateState(clearAmount = true) {
    this.setData({
      currentStep: 1,
      currentOrder: null,
      rechargeOrderId: '',
      verifyCode: '',
      countdownText: '10:00',
      createdTimeText: '',
      matchedLogTime: '',
      rechargeAmount: clearAmount ? '' : this.data.rechargeAmount
    })
  },

  resetRecharge() {
    this.resetToCreateState(true)
    this.loadRechargeState(true)
  },

  copyBeastId() {
    wx.setClipboardData({
      data: this.data.appBeastId,
      success: () => wx.showToast({ title: '已复制方块兽ID', icon: 'success' })
    })
  },

  copyOrderId() {
    const orderId = this.data.rechargeOrderId || (this.data.currentOrder && this.data.currentOrder.id)
    if (!orderId) {
      return
    }
    wx.setClipboardData({
      data: orderId,
      success: () => wx.showToast({ title: '已复制订单号', icon: 'success' })
    })
  },

  showTutorial() {
    wx.showModal({
      title: '转入宝石操作指南',
      content: '1. 创建订单后请在10分钟内完成购买沙粒并转给指定方块兽ID。\n2. 点击“验证订单”后，系统会实时查询最近10分钟真实交易日志。\n3. 找到对应时间，例如 17:16:18，取后4位 1618。\n4. 输入后4位即可完成到账校验，并把余额写入本地 MySQL。',
      showCancel: false
    })
  },

  goGuarantee() {
    wx.switchTab({ url: '/pages/guarantee/guarantee' })
  }
})
