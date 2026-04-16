function getStoredUserInfo() {
  return wx.getStorageSync('userInfo') || {}
}

function hasBeastId(userInfo = {}) {
  return !!String(userInfo.beastId || '').trim()
}

function ensureBeastId(options = {}) {
  const {
    userInfo = getStoredUserInfo(),
    title = '请先绑定方块兽ID',
    content = '请先去个人设置绑定方块兽ID，再继续当前操作。',
    confirmText = '去绑定',
    cancelText = '稍后',
    profileUrl = '/pages/profile/profile'
  } = options

  if (hasBeastId(userInfo)) {
    return true
  }

  wx.showModal({
    title,
    content,
    confirmText,
    cancelText,
    success: res => {
      if (res.confirm) {
        wx.navigateTo({ url: profileUrl })
      }
    }
  })

  return false
}

module.exports = {
  ensureBeastId,
  getStoredUserInfo,
  hasBeastId
}
