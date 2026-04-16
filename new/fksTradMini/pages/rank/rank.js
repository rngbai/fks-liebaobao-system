const rankTabs = [
  { key: 'guarantee', title: '担保达人榜', desc: '按担保成交和活跃度综合排序' },
  { key: 'recommend', title: '推荐贡献榜', desc: '按有效推荐人数与奖励贡献排序' }
]

const rankDataMap = {
  guarantee: [
    { id: 1, nickname: '星辰大主宰', score: 328, unit: '次担保', reward: 500, slogan: '成交快、纠纷少、平台护航经验丰富' },
    { id: 2, nickname: '龙王传说', score: 256, unit: '次担保', reward: 300, slogan: '长期稳定在线，担保流程配合度高' },
    { id: 3, nickname: '暗影猎手', score: 199, unit: '次担保', reward: 200, slogan: '冲榜状态，近期热度持续上升' },
    { id: 4, nickname: '火凤凰888', score: 145, unit: '次担保', reward: 100, slogan: '中高频卖家，处理速度快' },
    { id: 5, nickname: '冰狼战士', score: 98, unit: '次担保', reward: 50, slogan: '活跃商家，评价稳定' },
    { id: 6, nickname: '烈焰骑士', score: 76, unit: '次担保', reward: 30, slogan: '新人冲刺中，增长迅速' }
  ],
  recommend: [
    { id: 1, nickname: '推广达人', score: 128, unit: '位推荐', reward: 600, slogan: '社群传播强，拉新能力第一梯队' },
    { id: 2, nickname: '宣传小能手', score: 96, unit: '位推荐', reward: 400, slogan: '朋友圈与群推广效率很高' },
    { id: 3, nickname: '社区先锋', score: 72, unit: '位推荐', reward: 250, slogan: '持续推荐，转化质量稳定' },
    { id: 4, nickname: '玩家C', score: 45, unit: '位推荐', reward: 120, slogan: '近期涨势明显' },
    { id: 5, nickname: '玩家D', score: 30, unit: '位推荐', reward: 60, slogan: '稳步积累中' },
    { id: 6, nickname: '玩家E', score: 18, unit: '位推荐', reward: 30, slogan: '新晋上榜成员' }
  ]
}

function formatRankList(tabKey) {
  return (rankDataMap[tabKey] || []).map((item, index) => ({
    ...item,
    rankNo: index + 1,
    rewardText: `${item.reward} 宝石`,
    scoreText: `${item.score} ${item.unit}`,
    crown: index === 0 ? '👑' : index === 1 ? '🥈' : index === 2 ? '🥉' : ''
  }))
}

Page({
  data: {
    activeTab: 'guarantee',
    tabs: rankTabs,
    topThree: [],
    rankList: []
  },

  onLoad() {
    this.applyTab('guarantee')
  },

  switchTab(e) {
    const key = e.currentTarget.dataset.key
    this.applyTab(key)
  },

  applyTab(key) {
    const list = formatRankList(key)
    this.setData({
      activeTab: key,
      topThree: list.slice(0, 3),
      rankList: list.slice(3)
    })
  },

  goGroupDetail() {
    wx.navigateTo({ url: '/pages/group-detail/group-detail?qq=769851293' })
  }
})
