const displayImageCache = Object.create(null)

function getBaseUrl() {
  try {
    const app = getApp()
    return String((app && app.globalData && app.globalData.baseUrl) || '').replace(/\/+$/, '')
  } catch (error) {
    return ''
  }
}

function resolveImageUrl(imageUrl = '') {
  const rawUrl = String(imageUrl || '').trim()
  if (!rawUrl) return ''
  if (/^(https?:)?\/\//i.test(rawUrl) || /^wxfile:\/\//i.test(rawUrl) || /^data:/i.test(rawUrl)) {
    return rawUrl
  }

  const normalizedPath = rawUrl.startsWith('/') ? rawUrl : `/${rawUrl}`
  const baseUrl = getBaseUrl()
  return baseUrl ? `${baseUrl}${normalizedPath}` : normalizedPath
}

function resolveDisplayImageUrl(imageUrl = '') {
  const absoluteUrl = resolveImageUrl(imageUrl)
  if (!absoluteUrl) {
    return Promise.resolve('')
  }

  if (!/^http:\/\//i.test(absoluteUrl)) {
    return Promise.resolve(absoluteUrl)
  }

  if (displayImageCache[absoluteUrl]) {
    return Promise.resolve(displayImageCache[absoluteUrl])
  }

  return new Promise(resolve => {
    wx.downloadFile({
      url: absoluteUrl,
      success: res => {
        const tempFilePath = String((res || {}).tempFilePath || '').trim()
        if (Number((res || {}).statusCode) === 200 && tempFilePath) {
          displayImageCache[absoluteUrl] = tempFilePath
          resolve(tempFilePath)
          return
        }
        resolve(absoluteUrl)
      },
      fail: () => {
        resolve(absoluteUrl)
      }
    })
  })
}

function resolveProofUploadedTime(item = {}) {
  return item.buyer_proof_uploaded_time || item.buyerProofUploadedTime || item.buyer_proof_uploaded_at || item.buyerProofUploadedAt || ''
}

function normalizeGuaranteeItem(item = {}) {
  const status = Number(item.statusIndex !== undefined ? item.statusIndex : item.status || 0)
  const gemAmount = Number(item.gem_amount !== undefined ? item.gem_amount : item.gemAmount || 0)
  const feeAmount = Number(item.fee_amount !== undefined ? item.fee_amount : item.feeAmount || 0.5)

  return {
    id: item.id || item.orderNo || '',
    pet_name: item.pet_name || item.petName || '',
    trade_quantity: Number(item.trade_quantity !== undefined ? item.trade_quantity : item.tradeQuantity || 1),
    seller_game_id: item.seller_game_id || item.sellerGameId || '',
    seller_game_nick: item.seller_game_nick || item.sellerGameNick || '',
    gem_amount: gemAmount,
    fee_amount: feeAmount,
    seller_fee_amount: Number(item.seller_fee_amount !== undefined ? item.seller_fee_amount : item.sellerFeeAmount || feeAmount),
    buyer_fee_amount: Number(item.buyer_fee_amount !== undefined ? item.buyer_fee_amount : item.buyerFeeAmount || feeAmount),
    total_fee_amount: Number(item.total_fee_amount !== undefined ? item.total_fee_amount : item.totalFeeAmount || feeAmount * 2),
    seller_total_cost: Number(item.seller_total_cost !== undefined ? item.seller_total_cost : item.sellerTotalCost || (gemAmount + feeAmount)),
    actual_receive: Number(item.actual_receive !== undefined ? item.actual_receive : item.actualReceive || Math.max(gemAmount - feeAmount, 0)),
      market_price: Number(item.market_price !== undefined ? item.market_price : item.marketPrice || 0),
    seller_nick_name: item.seller_nick_name || item.sellerNickName || '',
    buyer_beast_id: item.buyer_beast_id || item.buyerBeastId || '',
    buyer_beast_nick: item.buyer_beast_nick || item.buyerBeastNick || '',
    buyer_trade_note: item.buyer_trade_note || item.buyerTradeNote || '',
    buyer_proof_image: resolveImageUrl(item.buyer_proof_image || item.buyerProofImage || item.path || ''),
    buyer_proof_uploaded_time: resolveProofUploadedTime(item),
    auto_confirm_time: item.auto_confirm_time || item.autoConfirmTime || '',
    seller_beast_id: item.seller_beast_id || item.sellerBeastId || '',
    seller_confirmed: !!(item.seller_confirmed !== undefined ? item.seller_confirmed : item.sellerConfirmed),
    seller_confirmed_time: item.seller_confirmed_time || item.sellerConfirmedTime || '',
    remark: item.remark || '',
    admin_note: item.admin_note || item.adminNote || '',
    status_text: item.status_text || item.statusText || '',
    status_desc: item.status_desc || item.statusDesc || '',
    create_time: item.create_time || item.createTime || '',
    matched_time: item.matched_time || item.matchedTime || '',
    finished_time: item.finished_time || item.finishedTime || '',
    expire_at_ms: Number(item.expire_at_ms !== undefined ? item.expire_at_ms : item.expireAtMs || 0),
    abandon_proof_expire_at_ms: Number(
      item.abandon_proof_expire_at_ms !== undefined ? item.abandon_proof_expire_at_ms : item.abandonProofExpireAtMs || 0
    ),
    status
  }
}

module.exports = {
  normalizeGuaranteeItem,
  resolveImageUrl,
  resolveDisplayImageUrl
}
