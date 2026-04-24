const fs = require('fs')
const path = require('path')
const assert = require('assert')

function read(relPath) {
  const fullPath = path.join('E:/猎宝保系统2', relPath)
  return fs.readFileSync(fullPath, 'utf8')
}

function expectNotIncludes(relPath, snippets) {
  const content = read(relPath)
  snippets.forEach((snippet) => {
    assert(
      !content.includes(snippet),
      `${relPath} still contains forbidden snippet: ${snippet}`
    )
  })
}

function expectIncludes(relPath, snippets) {
  const content = read(relPath)
  snippets.forEach((snippet) => {
    assert(
      content.includes(snippet),
      `${relPath} is missing expected snippet: ${snippet}`
    )
  })
}

expectIncludes('fksTradMini/pages/guarantee/guarantee.wxml', [
  '买卖双方各扣 0.5 宝石',
])

expectNotIncludes('fksTradMini/pages/guarantee/guarantee.wxml', [
  '挂单宝石 + 1',
  '再扣 1 宝石手续费',
])

expectNotIncludes('fksTradMini/pages/guarantee-order/guarantee-order.wxml', [
  '约定返还 + 1 卖家手续费',
  '约定返还 + 1 宝石手续费',
  'gemAmount + 1',
  'N+1',
  '含1卖家手续费',
  '再扣 1 买家手续费',
  '扣除 1 宝石买家手续费',
])

expectNotIncludes('fksTradMini/pages/guarantee-order/guarantee-order.js', [
  'gemBalance >= gemAmount + 1',
])

expectNotIncludes('fksTradMini/utils/guarantee.js', [
  'item.feeAmount || 1',
])

expectNotIncludes('fksapi/db_mysql.py', [
  '????',
])

expectNotIncludes('fksAdmin/src/views/DashboardView.vue', [
  '月度推广结算',
  '阶梯分红',
  'Top5奖励',
  '/api/manage/promotion/settle-monthly',
])

expectNotIncludes('fksTradMini/pages/recharge/recharge.js', [
  '????????',
])

expectNotIncludes('fksTradMini/pages/transfer/transfer.js', [
  '????????',
])

console.log('launch readiness consistency assertions passed')
