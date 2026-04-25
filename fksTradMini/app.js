const DEFAULT_BASE_URL = 'https://liebaobao.site'
const API_BASE_URL_STORAGE = 'api_base_url'
const USER_KEY_STORAGE = 'local_user_key_v1'
const COMMUNITY_PREFETCH_MAX_AGE = 60000

const {
  classifyRequestError,
  extractErrorMessage,
  shouldDisplayRequestToast,
} = require('./utils/request-diagnostics')

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
  const fallback = normalizeBaseUrl(DEFAULT_BASE_URL)

  if (isDevtoolsEnv()) {
    return runtimeBaseUrl || fallback
  }

  const ipPattern = /^https?:\/\/\d{1,3}(?:\.\d{1,3}){3}/
  if (storedBaseUrl && ipPattern.test(storedBaseUrl) && !/127\.0\.0\.1|localhost/i.test(storedBaseUrl)) {
    try {
      wx.removeStorageSync(API_BASE_URL_STORAGE)
    } catch (error) {}
    return fallback
  }

  if (fallback.startsWith('https://') && storedBaseUrl && storedBaseUrl.startsWith('http://')) {
    try {
      wx.removeStorageSync(API_BASE_URL_STORAGE)
    } catch (error) {}
    return fallback
  }

  return storedBaseUrl || runtimeBaseUrl || fallback
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

App({
  globalData: {
    userInfo: null,
    openid: '',
    userKey: '',
    baseUrl: DEFAULT_BASE_URL,
    loadingCount: 0,
    pendingCommunityRoute: null,
    requestToastState: {},
    communityProfilesCache: null,
    communityProfilesPending: null,
  },

  onLaunch() {
    const resolvedUrl = resolveStartupBaseUrl()
    this.globalData.baseUrl = resolvedUrl
    wx.setStorageSync(API_BASE_URL_STORAGE, resolvedUrl)
    console.log('[FKS] baseUrl resolved:', resolvedUrl)

    this.globalData.userKey = this.ensureUserKey()
    this.globalData.userInfo = wx.getStorageSync('userInfo') || null

    wx.login({
      success: () => {},
      fail: () => {},
    })

    setTimeout(() => {
      this.prefetchCommunityProfiles().catch(() => {})
    }, 300)
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
      'x-user-key': this.getUserKey(),
    }

    if (this.globalData.openid) {
      header.openid = this.globalData.openid
    }

    return {
      ...header,
      ...extraHeader,
    }
  },

  getCommunityProfilesCache(maxAge = COMMUNITY_PREFETCH_MAX_AGE) {
    const cache = this.globalData.communityProfilesCache
    if (!cache || !Array.isArray(cache.list) || !cache.ts) return null
    if (Date.now() - Number(cache.ts || 0) > maxAge) return null
    return cache
  },

  setCommunityProfilesCache(list = []) {
    const cache = {
      list: Array.isArray(list) ? list : [],
      ts: Date.now(),
    }
    this.globalData.communityProfilesCache = cache
    return cache
  },

  prefetchCommunityProfiles({ force = false } = {}) {
    const cached = this.getCommunityProfilesCache()
    if (!force && cached) return Promise.resolve(cached)
    if (this.globalData.communityProfilesPending) {
      return this.globalData.communityProfilesPending
    }

    const pending = this.request({
      url: '/api/community',
      method: 'GET',
      showLoading: false,
      showError: false,
      retry: 0,
      timeout: 6000,
    }).then(payload => {
      const data = (payload && payload.data) || {}
      const list = Array.isArray(data.list)
        ? data.list
        : Array.isArray(payload && payload.list)
          ? payload.list
          : []
      return this.setCommunityProfilesCache(list)
    }).finally(() => {
      this.globalData.communityProfilesPending = null
    })

    this.globalData.communityProfilesPending = pending
    return pending
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
      timeout = 15000,
      retry,
    } = options

    const maxRetry = retry !== undefined
      ? Math.max(0, Number(retry))
      : (/^get$/i.test(method) ? 2 : 0)

    const requestUrl = buildRequestUrl(this.getBaseUrl(), url)

    if (showLoading) {
      this.showGlobalLoading(loadingText)
    }

    const doOnce = () => new Promise((resolve, reject) => {
      wx.request({
        url: requestUrl,
        method,
        data,
        timeout,
        header: this.getRequestHeader(header),
        success: res => {
          const payload = res.data || {}
          if (res.statusCode !== 200) {
            reject({ ...payload, message: extractErrorMessage(payload, '请求失败'), statusCode: res.statusCode })
          } else if (payload.ok === false) {
            reject({ ...payload, message: extractErrorMessage(payload, '请求失败') })
          } else {
            resolve(payload)
          }
        },
        fail: err => {
          reject({ ...(err || {}), _network: true })
        },
      })
    })

    const attempt = (attemptIndex) => doOnce().catch(err => {
      if (err._network && attemptIndex < maxRetry) {
        return new Promise(resolve => setTimeout(resolve, 800 * (attemptIndex + 1)))
          .then(() => attempt(attemptIndex + 1))
      }
      return Promise.reject(err)
    })

    return attempt(0).then(
      payload => {
        if (showLoading) this.hideGlobalLoading()
        complete && complete()
        success && success(payload)
        return payload
      },
      err => {
        if (showLoading) this.hideGlobalLoading()
        complete && complete()

        const diagnosis = classifyRequestError(err, requestUrl)
        const errorMessage = diagnosis.message

        console.warn('[FKS] request error:', {
          url: requestUrl,
          method,
          errMsg: diagnosis.rawMessage,
          message: errorMessage,
          code: diagnosis.code,
          baseUrl: this.getBaseUrl(),
        })

        if (showError && shouldDisplayRequestToast(this.globalData.requestToastState, diagnosis)) {
          wx.showToast({
            title: errorMessage,
            icon: 'none',
            duration: diagnosis.duration,
          })
        }

        fail && fail(err)
        return Promise.reject({ ...err, message: errorMessage, errorCode: diagnosis.code })
      }
    )
  },
})
