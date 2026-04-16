export function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatExpireText(expiresAt) {
  const expire = Number(expiresAt || 0)
  if (!expire) return '未同步'

  const diff = expire - Date.now()
  if (diff <= 0) {
    return '已过期'
  }

  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)

  if (hours <= 0) {
    return `${minutes} 分钟后过期`
  }

  return `${hours} 小时 ${minutes} 分钟后过期`
}
