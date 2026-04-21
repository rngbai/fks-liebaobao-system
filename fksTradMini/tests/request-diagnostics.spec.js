const assert = require('node:assert/strict')

const {
  classifyRequestError,
  shouldDisplayRequestToast,
  summarizeBatchRequestFailure,
} = require('../utils/request-diagnostics')

function run() {
  const domainResult = classifyRequestError(
    { errMsg: 'request:fail url not in domain list' },
    'https://liebaobao.site/api/user/balance'
  )
  assert.equal(domainResult.code, 'domain')
  assert.equal(domainResult.duration, 3500)

  const closedResult = classifyRequestError(
    { errMsg: 'request:fail net::ERR_CONNECTION_CLOSED' },
    'https://liebaobao.site/api/user/balance'
  )
  assert.equal(closedResult.code, 'connection_closed')
  assert.equal(closedResult.duration, 3500)

  const batchMessage = summarizeBatchRequestFailure([
    { ok: false, error: { message: closedResult.message } },
    { ok: false, error: { message: '网络波动，请重试' } },
  ])
  assert.equal(batchMessage, closedResult.message)

  const toastState = {}
  assert.equal(
    shouldDisplayRequestToast(toastState, { message: '网络波动，请重试', code: 'network', now: 1000 }),
    true
  )
  assert.equal(
    shouldDisplayRequestToast(toastState, { message: '网络波动，请重试', code: 'network', now: 2000 }),
    false
  )
  assert.equal(
    shouldDisplayRequestToast(toastState, { message: '网络波动，请重试', code: 'network', now: 10000 }),
    true
  )

  console.log('request diagnostics assertions passed')
}

run()
