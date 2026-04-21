const assert = require('node:assert/strict')

const {
  createPageLoadState,
  toSuccessState,
  toEmptyState,
  toErrorState,
} = require('../utils/page-load-state')

function run() {
  const initial = createPageLoadState()
  assert.equal(initial.status, 'loading')
  assert.equal(initial.errorMessage, '')

  const success = toSuccessState()
  assert.equal(success.status, 'success')
  assert.equal(success.errorMessage, '')

  const empty = toEmptyState()
  assert.equal(empty.status, 'empty')
  assert.equal(empty.errorMessage, '')

  const error = toErrorState('网络异常，请稍后重试')
  assert.equal(error.status, 'error')
  assert.equal(error.errorMessage, '网络异常，请稍后重试')

  const defaultError = toErrorState()
  assert.equal(defaultError.status, 'error')
  assert.equal(defaultError.errorMessage, '加载失败，请稍后重试')

  console.log('page load state assertions passed')
}

run()
