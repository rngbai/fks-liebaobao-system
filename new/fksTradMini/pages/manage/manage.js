const { requestApi: sendRequest } = require('../../utils/request')


function normalizeDaily(item = {}) {
  return {
    date: item.date || '',
    rechargeCount: Number(item.rechargeCount || 0),
    rechargeAmount: Number(item.rechargeAmount || 0),
    guaranteeCreatedCount: Number(item.guaranteeCreatedCount || 0),
    transferCount: Number(item.transferCount || 0),
    transferAmount: Number(item.transferAmount || 0),
    platformFeeAmount: Number(item.platformFeeAmount || 0)
  }
}


function normalizeRecharge(item = {}) {
  return {
    id: item.id || '',
    userNickName: item.userNickName || '方块兽玩家',
    account: item.account || '',
    beastId: item.beastId || '',
    amount: Number(item.amount || 0),
    statusText: item.statusText || '未知状态',
    statusClass: item.statusClass || 'pending',
    verifyCode: item.verifyCode || '',
    matchedTime: item.matchedTime || '',
    time: item.time || ''
  }
}

function normalizeGuarantee(item = {}) {
  return {
    id: item.id || item.orderNo || '',
    sellerNickName: item.sellerNickName || '',
    sellerBeastId: item.sellerBeastId || item.seller_beast_id || '',
    buyerBeastId: item.buyerBeastId || item.buyer_beast_id || '',
    buyerBeastNick: item.buyerBeastNick || item.buyer_beast_nick || '',
    gemAmount: Number(item.gemAmount !== undefined ? item.gemAmount : item.gem_amount || 0),
    feeAmount: Number(item.feeAmount !== undefined ? item.feeAmount : item.fee_amount || 0),
    actualReceive: Number(item.actualReceive !== undefined ? item.actualReceive : item.actual_receive || Number(item.gemAmount !== undefined ? item.gemAmount : item.gem_amount || 0)),

    statusText: item.statusText || '',

    statusClass: item.statusClass || 'pending',
    remark: item.remark || '',
    adminNote: item.adminNote || item.admin_note || '',
    createTime: item.createTime || item.create_time || '',
    matchedTime: item.matchedTime || item.matched_time || '',
    finishedTime: item.finishedTime || item.finished_time || ''
  }
}

function normalizeWithdraw(item = {}) {
  return {
    id: item.id || '',
    userNickName: item.userNickName || '方块兽玩家',
    account: item.account || '',
    beastId: item.beastId || '',
    beastNick: item.beastNick || '',
    requestAmount: Number(item.requestAmount !== undefined ? item.requestAmount : item.request_amount || 0),
    actualAmount: Number(item.actualAmount !== undefined ? item.actualAmount : item.actual_amount || 0),
    feeAmount: Number(item.feeAmount !== undefined ? item.feeAmount : item.fee_amount || 0),
    statusText: item.statusText || '',
    statusClass: item.statusClass || 'pending',
    userNote: item.userNote || '',
    adminNote: item.adminNote || '',
    createTime: item.createTime || '',
    processedTime: item.processedTime || ''
  }
}

Page({
  data: {
    totals: {
      userCount: 0,
      walletBalance: 0,
      lockedGems: 0,
      totalRechargeCount: 0,
      totalRechargeAmount: 0,
      completedGuaranteeCount: 0,
      totalGuaranteeFeeAmount: 0,
      totalWithdrawFeeAmount: 0,
      totalPlatformFeeAmount: 0,
      pendingTransferCount: 0,
      pendingWithdrawCount: 0,
      pendingActionCount: 0
    },
    today: {
      rechargeCount: 0,
      rechargeAmount: 0,
      transferCount: 0,
      transferAmount: 0,
      guaranteeFeeAmount: 0,
      withdrawFeeAmount: 0,
      platformFeeAmount: 0
    },

    dailyFlow: [],
    rechargeList: [],
    pendingTransferList: [],
    pendingWithdrawList: [],
    guaranteeList: []
  },

  onLoad() {
    this.loadDashboard()
  },

  onShow() {
    this.loadDashboard(true)
  },

  onPullDownRefresh() {
    this.loadDashboard(false, () => wx.stopPullDownRefresh())
  },

  requestApi(options) {
    return sendRequest(options, {
      showError: false
    })
  },


  loadDashboard(silent = false, callback) {
    this.requestApi({
      url: '/api/manage/dashboard?days=7&limit=20',
      showLoading: !silent,
      loadingText: '管理台加载中...'
    }).then(payload => {
      const data = payload.data || {}
      this.setData({
        totals: {
          userCount: Number((data.totals && data.totals.userCount) || 0),
          walletBalance: Number((data.totals && data.totals.walletBalance) || 0),
          lockedGems: Number((data.totals && data.totals.lockedGems) || 0),
          totalRechargeCount: Number((data.totals && data.totals.totalRechargeCount) || 0),
          totalRechargeAmount: Number((data.totals && data.totals.totalRechargeAmount) || 0),
          completedGuaranteeCount: Number((data.totals && data.totals.completedGuaranteeCount) || 0),
          totalGuaranteeFeeAmount: Number((data.totals && data.totals.totalGuaranteeFeeAmount) || 0),
          totalWithdrawFeeAmount: Number((data.totals && data.totals.totalWithdrawFeeAmount) || 0),
          totalPlatformFeeAmount: Number((data.totals && data.totals.totalPlatformFeeAmount) || 0),
          pendingTransferCount: Number((data.totals && data.totals.pendingTransferCount) || 0),
          pendingWithdrawCount: Number((data.totals && data.totals.pendingWithdrawCount) || 0),
          pendingActionCount: Number((data.totals && data.totals.pendingActionCount) || 0)
        },
        today: {
          rechargeCount: Number((data.today && data.today.rechargeCount) || 0),
          rechargeAmount: Number((data.today && data.today.rechargeAmount) || 0),
          transferCount: Number((data.today && data.today.transferCount) || 0),
          transferAmount: Number((data.today && data.today.transferAmount) || 0),
          guaranteeFeeAmount: Number((data.today && data.today.guaranteeFeeAmount) || 0),
          withdrawFeeAmount: Number((data.today && data.today.withdrawFeeAmount) || 0),
          platformFeeAmount: Number((data.today && data.today.platformFeeAmount) || 0)
        },

        dailyFlow: Array.isArray(data.dailyFlow) ? data.dailyFlow.map(normalizeDaily).reverse() : [],
        rechargeList: Array.isArray(data.rechargeList) ? data.rechargeList.map(normalizeRecharge) : [],
        pendingTransferList: Array.isArray(data.pendingTransferList) ? data.pendingTransferList.map(normalizeGuarantee) : [],
        pendingWithdrawList: Array.isArray(data.pendingWithdrawList) ? data.pendingWithdrawList.map(normalizeWithdraw) : [],
        guaranteeList: Array.isArray(data.guaranteeList) ? data.guaranteeList.map(normalizeGuarantee) : []
      })
      callback && callback()
    }).catch(error => {
      if (!silent) {
        wx.showToast({ title: error.message || error || '读取管理台失败', icon: 'none' })
      }
      callback && callback()
    })
  },

  copyText(e) {
    const text = String(e.currentTarget.dataset.text || '')
    const label = String(e.currentTarget.dataset.label || '内容')
    if (!text) return
    wx.setClipboardData({
      data: text,
      success: () => wx.showToast({ title: `${label}已复制`, icon: 'success' })
    })
  },

  completeTransfer() {
    wx.showToast({
      title: '担保单现已自动到账',
      icon: 'none'
    })
  },


  completeWithdraw(e) {
    const requestId = String(e.currentTarget.dataset.id || '')
    if (!requestId) return
    wx.showModal({
      title: '确认用户转出已处理',
      content: '请确认你已经按用户绑定的方块兽ID完成了人工转出，确认后会记入今日流水。',
      success: res => {
        if (!res.confirm) return
        this.requestApi({
          url: '/api/manage/transfer-request/complete',
          method: 'POST',
          data: { request_id: requestId, admin_note: '后台已完成用户转出' },
          showLoading: true,
          loadingText: '记录中...'
        }).then(() => {
          wx.showToast({ title: '已记录用户转出', icon: 'success' })
          this.loadDashboard(true)
        }).catch(error => {
          wx.showToast({ title: error.message || error || '记录失败', icon: 'none' })
        })
      }
    })
  }
})
