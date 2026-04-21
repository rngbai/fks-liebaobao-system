function extractErrorMessage(payload, fallbackText) {
  if (typeof payload === 'string' && payload.trim()) {
    return payload.trim()
  }

  if (payload && typeof payload.message === 'string' && payload.message.trim()) {
    return payload.message.trim()
  }

  if (payload && typeof payload.msg === 'string' && payload.msg.trim()) {
    return payload.msg.trim()
  }

  return fallbackText
}

function classifyRequestError(err = {}, requestUrl = '') {
  const errMsg = String(err.errMsg || '')
  let message = extractErrorMessage(err, '网络异常')
  let duration = 2000
  let code = 'unknown'

  if (/not in domain list|url not in domain list|合法域名|domain list|不合法|非法域名/i.test(errMsg)) {
    message = '当前域名未配置到小程序合法域名白名单'
    duration = 3500
    code = 'domain'
  } else if (/ssl|certificate|证书/i.test(errMsg)) {
    message = 'HTTPS 证书无效，请检查服务器证书链'
    duration = 3500
    code = 'certificate'
  } else if (err._network && /http:\/\//i.test(requestUrl)) {
    message = '正式版必须使用 HTTPS 域名'
    duration = 3500
    code = 'https_required'
  } else if (/timeout|超时/i.test(errMsg)) {
    message = '请求超时，请稍后重试'
    code = 'timeout'
  } else if (/ERR_CONNECTION_CLOSED|connection closed|ECONNRESET|socket hang up|abort/i.test(errMsg)) {
    message = '服务器连接被关闭，请检查域名解析、HTTPS 证书或 443/Nginx 配置'
    duration = 3500
    code = 'connection_closed'
  } else if (err._network) {
    message = '网络波动，请重试'
    code = 'network'
  }

  return {
    message,
    duration,
    code,
    rawMessage: errMsg,
  }
}

function shouldDisplayRequestToast(state = {}, payload = {}) {
  const now = Number(payload.now || Date.now())
  const message = String(payload.message || '').trim()
  const code = String(payload.code || '').trim()
  const fingerprint = `${code}::${message}`
  const repeatWindowMs = /^(network|timeout|connection_closed|domain|certificate|https_required)$/.test(code)
    ? 8000
    : 2500

  if (state.lastFingerprint === fingerprint && now - Number(state.lastShownAt || 0) < repeatWindowMs) {
    return false
  }

  state.lastFingerprint = fingerprint
  state.lastShownAt = now
  return true
}

function summarizeBatchRequestFailure(results = []) {
  const firstFailed = results.find(item => item && item.ok === false)
  if (!firstFailed || !firstFailed.error) {
    return ''
  }

  const preferredMessage = String(firstFailed.error.message || '').trim()
  if (preferredMessage) {
    return preferredMessage
  }

  const fallback = classifyRequestError(firstFailed.error, '').message
  return String(fallback || '').trim()
}

module.exports = {
  classifyRequestError,
  extractErrorMessage,
  shouldDisplayRequestToast,
  summarizeBatchRequestFailure,
}
