// 生产环境地址（部署到服务器后改为 https://你的域名，微信小程序正式版必须 HTTPS）
// 当前使用服务器 IP 直接访问（仅用于开发调试，正式上线前需绑定域名并申请 SSL）
const DEFAULT_BASE_URL = 'http://124.223.80.102'
const API_BASE_URL_STORAGE = 'api_base_url'
const USER_KEY_STORAGE = 'local_user_key_v1'

function generateLocalUserKey() {
  return `local_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').trim().replace(/\/+$/, '')
}

function isDevtoolsEnv() {
  try {
    const systemInfo = wx.getSystemInfoSync()
    return String((systemInfo && systemInfo.platform) || '').toLowerCase() === 'devtools'
  } catch (error) {
    return false
  }
}

function resolveStartupBaseUrl() {
  const storedBaseUrl = normalizeBaseUrl(wx.getStorageSync(API_BASE_URL_STORAGE))
  const runtimeBaseUrl = typeof globalThis !== 'undefined' ? normalizeBaseUrl(globalThis.__FKS_BASE_URL__) : ''
  if (isDevtoolsEnv()) {
    return runtimeBaseUrl || DEFAULT_BASE_URL
  }
  return storedBaseUrl || runtimeBaseUrl || DEFAULT_BASE_URL
}


function buildRequestUrl(baseUrl, url) {
  const requestPath = String(url || '').trim()

  if (!requestPath) {
    return baseUrl
  }

  if (/^https?:\/\//i.test(requestPath)) {
    return requestPath
  }

  return requestPath.startsWith('/') ? `${baseUrl}${requestPath}` : `${baseUrl}/${requestPath}`
}

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

function shouldRetryWithLocalBaseUrl(err) {
  const errMsg = String((err && err.errMsg) || err || '').toLowerCase()
  return errMsg.includes('timeout') || errMsg.includes('timed out') || errMsg.includes('connect') || errMsg.includes('refused') || errMsg.includes('fail')
}


App({
  globalData: {
    userInfo: null,
    openid: '',
    userKey: '',
    baseUrl: DEFAULT_BASE_URL,
    loadingCount: 0
  },


  onLaunch() {
    this.globalData.baseUrl = resolveStartupBaseUrl()
    wx.setStorageSync(API_BASE_URL_STORAGE, this.globalData.baseUrl)
    this.globalData.userKey = this.ensureUserKey()
    this.globalData.userInfo = wx.getStorageSync('userInfo') || null

    wx.login({
      success: () => {},
      fail: () => {}
    })
  },

  normalizeBaseUrl(baseUrl) {
    return normalizeBaseUrl(baseUrl)
  },

  getBaseUrl() {
    if (!this.globalData.baseUrl) {
      this.globalData.baseUrl = resolveStartupBaseUrl()
    }

    return this.globalData.baseUrl || DEFAULT_BASE_URL
  },

  setBaseUrl(baseUrl) {
    const normalized = normalizeBaseUrl(baseUrl) || DEFAULT_BASE_URL
    this.globalData.baseUrl = normalized
    wx.setStorageSync(API_BASE_URL_STORAGE, normalized)
    return normalized
  },

  ensureUserKey() {
    let userKey = wx.getStorageSync(USER_KEY_STORAGE)
    if (!userKey) {
      userKey = generateLocalUserKey()
      wx.setStorageSync(USER_KEY_STORAGE, userKey)
    }
    return userKey
  },

  getUserKey() {
    if (!this.globalData.userKey) {
      this.globalData.userKey = this.ensureUserKey()
    }
    return this.globalData.userKey
  },

  getRequestHeader(extraHeader = {}) {
    const header = {
      'content-type': 'application/json',
      'x-user-key': this.getUserKey()
    }

    if (this.globalData.openid) {
      header.openid = this.globalData.openid
    }

    return {
      ...header,
      ...extraHeader
    }
  },

  showGlobalLoading(loadingText = '加载中...') {
    const nextCount = Number(this.globalData.loadingCount || 0) + 1
    this.globalData.loadingCount = nextCount
    wx.showLoading({ title: loadingText, mask: true })
  },

  hideGlobalLoading() {
    const currentCount = Number(this.globalData.loadingCount || 0)
    if (currentCount <= 0) {
      this.globalData.loadingCount = 0
      return
    }

    const nextCount = currentCount - 1
    this.globalData.loadingCount = nextCount
    if (nextCount === 0) {
      wx.hideLoading()
    }
  },

  request(options = {}) {

    const {
      url,
      method = 'GET',
      data = {},
      header = {},
      success,
      fail,
      complete,
      showLoading = true,
      loadingText = '加载中...',
      showError = true,
      timeout = 10000
    } = options

    const requestUrl = buildRequestUrl(this.getBaseUrl(), url)
    if (showLoading) {
      this.showGlobalLoading(loadingText)
    }


    return new Promise((resolve, reject) => {
      wx.request({
        url: requestUrl,
        method,
        data,
        timeout,
        header: this.getRequestHeader(header),
        success: res => {
          const payload = res.data || {}

          if (res.statusCode !== 200) {
            const errorMessage = extractErrorMessage(payload, '请求失败')
            showError && wx.showToast({ title: errorMessage, icon: 'none' })
            fail && fail(payload)
            reject({ ...payload, message: errorMessage, statusCode: res.statusCode })
            return
          }

          if (payload.ok === false) {
            const errorMessage = extractErrorMessage(payload, '请求失败')
            showError && wx.showToast({ title: errorMessage, icon: 'none' })
            fail && fail(payload)
            reject({ ...payload, message: errorMessage })
            return
          }

          success && success(payload)
          resolve(payload)
        },
        fail: err => {
          const errorMessage = extractErrorMessage(err, '网络异常')
          showError && wx.showToast({ title: errorMessage, icon: 'none' })
          fail && fail(err)
          reject({ ...err, message: errorMessage })
        },
        complete: res => {
          if (showLoading) {
            this.hideGlobalLoading()
          }

          complete && complete(res)
        }

      })
    })
  }
})

