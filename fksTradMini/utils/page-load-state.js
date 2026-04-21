function createPageLoadState(status = 'loading', errorMessage = '') {
  return {
    status,
    errorMessage: String(errorMessage || '').trim(),
  }
}

function toSuccessState() {
  return createPageLoadState('success')
}

function toEmptyState() {
  return createPageLoadState('empty')
}

function toErrorState(errorMessage = '加载失败，请稍后重试') {
  return createPageLoadState('error', errorMessage || '加载失败，请稍后重试')
}

module.exports = {
  createPageLoadState,
  toSuccessState,
  toEmptyState,
  toErrorState,
}
