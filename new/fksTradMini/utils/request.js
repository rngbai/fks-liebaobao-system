function getAppInstance() {
  try {
    return getApp()
  } catch (error) {
    return null
  }
}

function requestApi(options = {}, defaults = {}) {
  const app = getAppInstance()

  if (!app || typeof app.request !== 'function') {
    return Promise.reject(new Error('应用请求能力未初始化'))
  }

  return app.request({
    ...defaults,
    ...options
  })
}

module.exports = {
  requestApi
}
