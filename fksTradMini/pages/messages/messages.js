Page({
  data: { messages: [] },
  onLoad() {
    this._loadMessages()
  },
  onShow() {
    this._loadMessages()
  },
  _loadMessages() {
    const rawMessages = [
      { id: 1, type: 'guarantee', title: '担保单已匹配', content: '您的担保单 GUA20260413001 买家已匹配成功，宝石已打出', time: '2026-04-13 09:30', read: false },
      { id: 2, type: 'gem', title: '宝石转入成功', content: '成功转入 💎200 宝石，当前余额 256', time: '2026-04-12 18:05', read: false },
      { id: 3, type: 'system', title: '系统通知', content: '欢迎使用方块兽担保平台，诚信交易从这里开始！', time: '2026-04-12 08:00', read: true }
    ]
    // mark all as read when page is open
    const messages = rawMessages.map(m => ({ ...m, read: true }))
    this.setData({ messages })
    wx.setStorageSync('msg_unread_count', 0)
  }
})
