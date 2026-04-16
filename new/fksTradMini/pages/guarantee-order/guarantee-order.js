const { requestApi: sendRequest } = require('../../utils/request')
const {
  normalizeGuaranteeItem: formatGuaranteeItem,
  resolveImageUrl: resolveGuaranteeImageUrl,
  resolveDisplayImageUrl: resolveGuaranteeDisplayImageUrl
} = require('../../utils/guarantee')


const PET_OPTIONS = [
  '兽王｜新叶螳',
  '兽王｜盾刀螳螂',
  '兽王｜巨剑螳螂',
  '兽王｜地狱犬',
  '兽王｜双头地狱犬',
  '兽王｜波波龙',
  '兽王｜海龙兽',
  '兽王｜小影豹',
  '兽王｜雷云豹',
  '兽王｜雷霆豹皇',
  '兽王｜锯齿鲨',
  '兽王｜裂地锯鲨',
  '兽王｜双旋锯鲨',
  '兽王｜兜虫小子'
]

function resolvePetIndex(petName = '') {
  const index = PET_OPTIONS.indexOf(petName)
  return index >= 0 ? index : 0
}

function extractFileName(filePath = '') {
  const cleanPath = String(filePath || '').split('?')[0]
  const segments = cleanPath.split('/')
  return segments[segments.length - 1] || 'proof.jpg'
}

function resolveImageUrl(imageUrl = '') {
  return resolveGuaranteeImageUrl(imageUrl)
}




function normalizeOrderDetail(raw = {}) {
  return formatGuaranteeItem(raw)
}

function buildGuaranteeDisplayState(state = {}) {
  const orderDetail = state.orderDetail || null
  const hasOrderDetailView = !!(orderDetail && (state.orderId || state.queryResult))

  return {
    hasOrderDetailView,
    buyerProofMetaText: (orderDetail && orderDetail.buyer_proof_uploaded_time) || '已上传'
  }
}

function attachBuyerProofDisplay(orderDetail = null) {
  const detail = orderDetail ? Object.assign({}, orderDetail) : null
  if (!detail) {
    return Promise.resolve(null)
  }

  const rawProofImage = String(detail.buyer_proof_image || '').trim()
  if (!rawProofImage) {
    detail.buyer_proof_image_display = ''
    return Promise.resolve(detail)
  }

  return resolveGuaranteeDisplayImageUrl(rawProofImage).then(displayUrl => {
    detail.buyer_proof_image_display = displayUrl || rawProofImage
    return detail
  }).catch(() => {
    detail.buyer_proof_image_display = rawProofImage
    return detail
  })
}

function readImageAsBase64(filePath = '') {



  return new Promise((resolve, reject) => {
    const targetPath = String(filePath || '').trim()
    if (!targetPath) {
      reject(new Error('缺少图片路径'))
      return
    }

    wx.getFileSystemManager().readFile({
      filePath: targetPath,
      encoding: 'base64',
      success: res => {
        const base64Data = String((res || {}).data || '').trim()
        if (!base64Data) {
          reject(new Error('图片内容为空'))
          return
        }
        resolve(base64Data)
      },
      fail: err => {
        reject(err || new Error('读取图片失败'))
      }
    })
  })
}




Page({
  data: {
    petOptions: PET_OPTIONS,
    petIndex: 0,
    tab: 'create',
    orderId: '',
    gemBalance: 0,
    gemAmount: '',
    tradeQuantity: '1',
    sellerGameId: '',
    sellerGameNick: '',
    remark: '',
    agreed: false,
    canCreate: false,
    showCreated: false,
    createdOrderId: '',
    queryId: '',
    queryResult: false,
    orderDetail: null,
    viewerRole: 'guest',
    isBuyer: true,
    buyerBeastId: '',
    buyerBeastNick: '',
    buyerTradeNote: '',
    buyerProofImage: '',
    buyerProofPreviewImage: '',
    showFeeModal: false,

    hasOrderDetailView: false,
    buyerProofMetaText: '',
    statusIconList: ['⏳', '🧾', '✅', '⚠️']
  },


  onLoad(options) {
    if (options.tab) this.setData({ tab: options.tab })
    if (options.id) {
      this.setData({ orderId: options.id })
      this.loadOrderDetail(options.id)
    }
    if (options.orderId) {
      this.setData({ queryId: options.orderId })
      this.loadOrderDetail(options.orderId)
    }
    this.loadBalance()
  },

  onShow() {
    if (this.data.orderId) {
      this.loadOrderDetail(this.data.orderId)
    }
  },

  requestApi(options) {
    return sendRequest(options, {
      showError: false
    })
  },

  syncDisplayState(patch = {}, callback) {
    const nextState = Object.assign({}, this.data, patch || {})
    const displayState = buildGuaranteeDisplayState(nextState)
    this.setData(Object.assign({}, patch, displayState), callback)
  },

  syncOrderDetailState(patch = {}, callback) {
    if (!patch || !Object.prototype.hasOwnProperty.call(patch, 'orderDetail')) {
      this.syncDisplayState(patch, callback)
      return
    }

    attachBuyerProofDisplay(patch.orderDetail).then(orderDetail => {
      this.syncDisplayState(Object.assign({}, patch, { orderDetail }), callback)
    })
  },

  loadBalance() {


    this.requestApi({
      url: '/api/user/balance',
      showLoading: false,
      showError: false
    }).then(payload => {

      const gemBalance = Number((payload.data && payload.data.gemBalance) || 0)
      this.setData({ gemBalance }, () => this.checkCanCreate())
    }).catch(() => {
      this.setData({ gemBalance: 0 }, () => this.checkCanCreate())
    })
  },

  switchTab(e) {
    this.syncOrderDetailState({
      tab: e.currentTarget.dataset.tab,
      queryResult: false,
      orderDetail: null,
      showCreated: false,
      queryId: '',
      viewerRole: 'guest',
      buyerBeastId: '',
      buyerBeastNick: '',
      buyerTradeNote: '',
      buyerProofImage: '',
      buyerProofPreviewImage: ''
    })
  },


  onPetChange(e) {
    this.setData({ petIndex: Number(e.detail.value || 0) }, () => this.checkCanCreate())
  },

  onGemInput(e) {
    const val = String(e.detail.value || '').replace(/[^0-9]/g, '')
    const gemAmount = val ? parseInt(val, 10) : ''
    this.setData({ gemAmount }, () => this.checkCanCreate())
  },

  onTradeQuantityInput(e) {
    const val = String(e.detail.value || '').replace(/[^0-9]/g, '')
    this.setData({ tradeQuantity: val ? String(Math.max(1, parseInt(val, 10))) : '' }, () => this.checkCanCreate())
  },

  onSellerGameIdInput(e) {
    this.setData({ sellerGameId: e.detail.value }, () => this.checkCanCreate())
  },

  onSellerGameNickInput(e) {
    this.setData({ sellerGameNick: e.detail.value }, () => this.checkCanCreate())
  },

  onRemarkInput(e) {
    this.setData({ remark: e.detail.value })
  },

  onBuyerIdInput(e) {
    this.setData({ buyerBeastId: e.detail.value })
  },

  onBuyerNickInput(e) {
    this.setData({ buyerBeastNick: e.detail.value })
  },

  onBuyerTradeNoteInput(e) {
    this.setData({ buyerTradeNote: e.detail.value })
  },

  chooseBuyerProof() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: res => {
        const firstFile = (((res || {}).tempFiles || [])[0] || {})
        const filePath = firstFile.path || firstFile.tempFilePath || (((res || {}).tempFilePaths || [])[0] || '')
        if (!filePath) {
          wx.showToast({ title: '未获取到截图文件', icon: 'none' })
          return
        }
        this.uploadBuyerProof(filePath)
      },
      fail: err => {
        if (err && /cancel/i.test(String(err.errMsg || ''))) return
        wx.showToast({ title: '选择截图失败', icon: 'none' })
      }
    })
  },


  uploadBuyerProof(filePath) {
    readImageAsBase64(filePath).then(base64Data => {
      this.requestApi({
        url: '/api/upload/image',
        method: 'POST',
        data: {
          folder: 'guarantee-proof',
          image_base64: base64Data,
          image_name: extractFileName(filePath)
        },
        showLoading: true,
        loadingText: '上传截图中...'
      }).then(payload => {
        const data = payload.data || {}
        const uploadedImage = String(data.path || data.url || '').trim()
        if (!uploadedImage) {
          wx.showToast({ title: '上传返回为空', icon: 'none' })
          return
        }
        this.setData({
          buyerProofImage: uploadedImage,
          buyerProofPreviewImage: filePath
        })
        wx.showToast({ title: '截图已上传', icon: 'success' })

      }).catch(error => {

        wx.showToast({ title: error.message || error || '上传失败', icon: 'none' })
      })
    }).catch(err => {
      console.error('buyer proof read failed:', err)
      wx.showToast({ title: '读取截图失败', icon: 'none' })
    })
  },


  previewBuyerProof(e) {
    const orderDetail = this.data.orderDetail || {}
    const url = e.currentTarget.dataset.url || this.data.buyerProofPreviewImage || this.data.buyerProofImage || orderDetail.buyer_proof_image_display || orderDetail.buyer_proof_image || ''
    if (!url) return
    wx.previewImage({ urls: [url], current: url })
  },

  removeBuyerProof() {
    this.setData({ buyerProofImage: '', buyerProofPreviewImage: '' })
  },


  toggleAgreed() {
    this.setData({ agreed: !this.data.agreed }, () => this.checkCanCreate())
  },

  checkCanCreate() {
    const { gemAmount, agreed, gemBalance, tradeQuantity, sellerGameId, sellerGameNick, petOptions, petIndex } = this.data
    const petName = petOptions[petIndex] || ''
    const canCreate = !!(
      petName &&
      gemAmount &&
      gemAmount > 0 &&
      Number(tradeQuantity || 0) > 0 &&
      sellerGameId.trim() &&
      sellerGameNick.trim() &&
      agreed &&
      gemBalance >= gemAmount + 1
    )
    this.setData({ canCreate })
  },

  goRecharge() {
    wx.navigateTo({ url: '/pages/recharge/recharge' })
  },

  createGuaranteeOrder() {
    if (!this.data.canCreate) return
    const { gemAmount, remark, petOptions, petIndex, tradeQuantity, sellerGameId, sellerGameNick } = this.data

    this.requestApi({
      url: '/api/guarantee/create',
      method: 'POST',
      data: {
        pet_name: petOptions[petIndex] || '',
        trade_quantity: Number(tradeQuantity || 1),
        seller_game_id: sellerGameId.trim(),
        seller_game_nick: sellerGameNick.trim(),
        gem_amount: gemAmount,
        remark
      },
      showLoading: true,
      loadingText: '发布保单中...'
    }).then(payload => {
      const data = payload.data || {}
      const wallet = data.wallet || {}
      const order = normalizeOrderDetail(data.order || {})
      this.syncOrderDetailState({
        showCreated: true,
        createdOrderId: order.id,
        gemBalance: Number(wallet.gemBalance || this.data.gemBalance),
        gemAmount: '',
        tradeQuantity: '1',
        sellerGameId: '',
        sellerGameNick: '',
        agreed: false,
        remark: '',
        canCreate: false,
        orderId: order.id,
        orderDetail: order,
        viewerRole: 'seller',
        isBuyer: false,
        petIndex: resolvePetIndex(order.pet_name)
      })


      wx.showToast({ title: '保单已发布', icon: 'success' })
    }).catch(error => {
      wx.showToast({ title: error.message || error || '发布失败', icon: 'none' })
    })
  },

  copyCreatedOrderId() {
    wx.setClipboardData({
      data: this.data.createdOrderId,
      success: () => wx.showToast({ title: '单号已复制', icon: 'success' })
    })
  },

  shareOrderCard() {
    const detail = this.data.orderDetail || {}
    const orderId = this.data.createdOrderId || detail.id || ''
    if (!orderId) return

    const query = this.createSelectorQuery()
    query.select('#shareCanvas').fields({ node: true, size: true }).exec((res) => {
      if (!res || !res[0] || !res[0].node) {
        wx.setClipboardData({ data: orderId })
        wx.showToast({ title: '保单号已复制，可直接发给买家', icon: 'none' })
        return
      }
      const canvas = res[0].node
      const ctx = canvas.getContext('2d')
      const dpr = wx.getWindowInfo().pixelRatio || 2
      canvas.width = 600 * dpr
      canvas.height = 400 * dpr
      ctx.scale(dpr, dpr)

      const gradient = ctx.createLinearGradient(0, 0, 600, 400)
      gradient.addColorStop(0, '#1e293b')
      gradient.addColorStop(0.6, '#334155')
      gradient.addColorStop(1, '#475569')
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.roundRect(0, 0, 600, 400, 24)
      ctx.fill()

      ctx.fillStyle = 'rgba(91, 110, 245, 0.15)'
      ctx.beginPath()
      ctx.arc(500, 60, 80, 0, Math.PI * 2)
      ctx.fill()

      ctx.fillStyle = '#94a3b8'
      ctx.font = '500 22px sans-serif'
      ctx.fillText('方块兽担保 · 保单分享', 32, 48)

      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 36px sans-serif'
      ctx.fillText(detail.pet_name || '兽王保单', 32, 100)

      ctx.fillStyle = '#5B6EF5'
      ctx.font = 'bold 28px sans-serif'
      ctx.fillText(`${detail.gem_amount || 0} 宝石`, 32, 145)

      ctx.fillStyle = '#64748b'
      ctx.font = '22px sans-serif'
      ctx.fillText(`卖家ID: ${detail.seller_game_id || '-'}`, 350, 100)
      ctx.fillText(`数量: ${detail.trade_quantity || 1} 只`, 350, 135)

      ctx.fillStyle = 'rgba(255,255,255,0.08)'
      ctx.beginPath()
      ctx.roundRect(24, 170, 552, 80, 16)
      ctx.fill()

      ctx.fillStyle = '#cbd5e1'
      ctx.font = '20px sans-serif'
      ctx.fillText('保单号', 44, 200)
      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 30px monospace'
      ctx.fillText(orderId, 44, 235)

      ctx.fillStyle = '#94a3b8'
      ctx.font = '20px sans-serif'
      ctx.fillText(`买家预计实收: ${detail.actual_receive || 0} 宝石 · 创建于 ${detail.create_time || ''}`, 32, 290)

      ctx.fillStyle = 'rgba(91, 110, 245, 0.9)'
      ctx.beginPath()
      ctx.roundRect(32, 320, 536, 56, 28)
      ctx.fill()
      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 24px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('打开方块兽担保小程序 · 输入保单号匹配', 300, 356)
      ctx.textAlign = 'left'

      wx.canvasToTempFilePath({
        canvas,
        success: (fileRes) => {
          wx.saveImageToPhotosAlbum({
            filePath: fileRes.tempFilePath,
            success: () => wx.showToast({ title: '卡片已保存到相册', icon: 'success' }),
            fail: () => {
              wx.previewImage({ urls: [fileRes.tempFilePath] })
            }
          })
        },
        fail: () => wx.showToast({ title: '生成卡片失败', icon: 'none' })
      })
    })
  },

  onQueryInput(e) {
    this.setData({ queryId: e.detail.value })
  },

  searchOrder() {
    const id = this.data.queryId.trim()
    if (!id) {
      wx.showToast({ title: '请输入担保单号', icon: 'none' })
      return
    }
    this.loadOrderDetail(id)
  },

  loadOrderDetail(id) {
    this.requestApi({
      url: `/api/guarantee/detail?order_no=${encodeURIComponent(id)}`,
      showLoading: true,
      loadingText: '查询中...'
    }).then(payload => {
      const data = payload.data || {}
      const orderDetail = normalizeOrderDetail(data.order || {})
      const wallet = data.wallet || {}
      this.syncOrderDetailState({
        orderId: orderDetail.id || id,
        orderDetail,
        queryResult: true,
        gemBalance: Number(wallet.gemBalance || this.data.gemBalance),
        viewerRole: data.viewerRole || 'guest',
        isBuyer: !!data.canMatch,
        buyerBeastId: orderDetail.buyer_beast_id || this.data.buyerBeastId,
        buyerBeastNick: orderDetail.buyer_beast_nick || this.data.buyerBeastNick,
        buyerTradeNote: orderDetail.buyer_trade_note || this.data.buyerTradeNote,
        buyerProofImage: orderDetail.buyer_proof_image || this.data.buyerProofImage,
        buyerProofPreviewImage: ''
      })


    }).catch(error => {
      wx.showToast({ title: error.message || error || '查询失败', icon: 'none' })
    })
  },

  copyOrderDetail() {
    if (!this.data.orderDetail || !this.data.orderDetail.id) return
    wx.setClipboardData({
      data: this.data.orderDetail.id,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    })
  },

  confirmMatch() {
    if (!this.data.buyerBeastId.trim()) {
      wx.showToast({ title: '请输入您的方块兽ID', icon: 'none' })
      return
    }
    if (!this.data.buyerBeastNick.trim()) {
      wx.showToast({ title: '请输入您的昵称', icon: 'none' })
      return
    }
    if (!this.data.buyerProofImage.trim()) {
      wx.showToast({ title: '请先上传交易截图', icon: 'none' })
      return
    }
    this.setData({ showFeeModal: true })
  },

  closeFeeModal() {
    this.setData({ showFeeModal: false })
  },

  noop() {},

  doConfirmMatch() {
    const { orderDetail, buyerBeastId, buyerBeastNick, buyerTradeNote, buyerProofImage } = this.data
    if (!orderDetail || !orderDetail.id) {
      this.setData({ showFeeModal: false })
      return
    }

    this.requestApi({
      url: '/api/guarantee/match',
      method: 'POST',
      data: {
        order_no: orderDetail.id,
        buyer_beast_id: buyerBeastId.trim(),
        buyer_beast_nick: buyerBeastNick.trim(),
        buyer_trade_note: buyerTradeNote.trim(),
        buyer_proof_image: buyerProofImage.trim()
      },
      showLoading: true,
      loadingText: '提交中...'
    }).then(payload => {
      const data = payload.data || {}
      const nextOrder = normalizeOrderDetail(data.order || {})
      this.syncOrderDetailState({
        showFeeModal: false,
        orderDetail: nextOrder,
        viewerRole: data.viewerRole || 'buyer',
        isBuyer: false,
        queryResult: true,
        buyerProofImage: nextOrder.buyer_proof_image || buyerProofImage,
        buyerProofPreviewImage: ''
      })


      wx.showToast({ title: '匹配成功，等待卖家确认', icon: 'success', duration: 2200 })
    }).catch(error => {
      this.setData({ showFeeModal: false })
      wx.showToast({ title: error.message || error || '匹配失败', icon: 'none' })
    })
  },

  confirmSellerComplete() {
    const { orderDetail } = this.data
    if (!orderDetail || !orderDetail.id) return

    wx.showModal({
      title: '确认交易完成',
      content: '请返回地球猎人APP核对买家是否真实拍下，并结合页面里的截图凭证与买家说明一起确认。你确认后，系统会自动把这笔宝石发给买家。',
      confirmText: '我已核对',
      success: (res) => {
        if (!res.confirm) return
        this.requestApi({
          url: '/api/guarantee/seller-confirm',
          method: 'POST',
          data: { order_no: orderDetail.id },
          showLoading: true,
          loadingText: '确认中...'
        }).then(payload => {
          const data = payload.data || {}
          this.syncOrderDetailState({
            orderDetail: normalizeOrderDetail(data.order || {}),
            viewerRole: data.viewerRole || 'seller',
            queryResult: true
          })
          wx.showToast({ title: '已确认并自动到账', icon: 'success' })
        }).catch(error => {
          wx.showToast({ title: error.message || error || '确认失败', icon: 'none' })
        })
      }
    })
  },

  rejectSellerConfirm() {
    const { orderDetail } = this.data
    if (!orderDetail || !orderDetail.id) return

    wx.showModal({
      title: '拒绝确认交易',
      content: '如果买家提交的截图不真实、信息不匹配或你在游戏内未收到对应交易，请填写原因后拒绝。拒绝后订单将进入人工仲裁流程，自动确认倒计时会暂停。',
      confirmText: '填写原因',
      confirmColor: '#e74c3c',
      success: (res) => {
        if (!res.confirm) return
        this.showRejectReasonInput()
      }
    })
  },

  showRejectReasonInput() {
    const { orderDetail } = this.data
    wx.showModal({
      title: '请输入拒绝原因',
      editable: true,
      placeholderText: '例：游戏内未收到交易 / 截图是旧图 / 金额不对...',
      success: (res) => {
        if (!res.confirm) return
        const reason = (res.content || '').trim()
        if (!reason) {
          wx.showToast({ title: '请填写拒绝原因', icon: 'none' })
          return
        }
        this.requestApi({
          url: '/api/guarantee/seller-reject',
          method: 'POST',
          data: { order_no: orderDetail.id, reason },
          showLoading: true,
          loadingText: '提交中...'
        }).then(payload => {
          const data = payload.data || {}
          this.syncOrderDetailState({
            orderDetail: normalizeOrderDetail(data.order || {}),
            viewerRole: data.viewerRole || 'seller',
            queryResult: true
          })
          wx.showToast({ title: '已拒绝，等待人工仲裁', icon: 'none' })
        }).catch(error => {
          wx.showToast({ title: error.message || error || '拒绝失败', icon: 'none' })
        })
      }
    })
  }
})
