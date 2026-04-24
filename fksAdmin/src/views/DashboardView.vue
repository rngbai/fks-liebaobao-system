<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Connection,
  DataAnalysis,
  EditPen,
  Files,
  HomeFilled,
  Key,
  Money,
  Promotion,
  User,
} from '@element-plus/icons-vue'
import HomeContentManagePanel from '../components/HomeContentManagePanel.vue'
import LayoutFeedbackManagePanel from '../components/LayoutFeedbackManagePanel.vue'
import PromotionManagePanel from '../components/PromotionManagePanel.vue'
import TokenManagePanel from '../components/TokenManagePanel.vue'
import CommunityApplyManagePanel from '../components/CommunityApplyManagePanel.vue'
import CommunityManagePanel from '../components/CommunityManagePanel.vue'
import UserManagePanel from '../components/UserManagePanel.vue'

import { DASHBOARD_SECTIONS } from '../constants/dashboard'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/auth'
import { formatNumber } from '../utils/format'

const router = useRouter()
const auth = useAuthStore()
const LIST_PAGE_SIZES = [10, 20, 50]
const FILTER_PLACEHOLDERS = {
  pendingWithdraw: '搜索申请单号 / 用户 / 方块兽 ID / 备注',
  pendingFeedback: '搜索标题 / 内容 / 用户 / 联系方式',
  recharge: '搜索订单号 / 账号 / 方块兽 ID / 校验码',
  guarantee: '搜索保单号 / 卖家 / 买家 / 地球猎人 ID',
  feedback: '搜索标题 / 内容 / 用户 / 联系方式',
  daily: '搜索日期 / 充值 / 转出 / 新担保 / 反馈',
}
const LIST_STATUS_OPTIONS = {
  pendingWithdraw: [
    { label: '待处理', value: 'pending' },
  ],
  pendingFeedback: [
    { label: '待处理', value: 'pending' },
  ],
  recharge: [
    { label: '待验证', value: 'pending' },
    { label: '已到账', value: 'success' },
    { label: '已取消', value: 'cancelled' },
    { label: '已超时', value: 'expired' },
  ],
  guarantee: [
    { label: '等待买家匹配', value: 'pending' },
    { label: '待卖家确认', value: 'matched' },
    { label: '已完成', value: 'done' },
    { label: '申诉中', value: 'appeal' },
    { label: '已关闭', value: 'closed' },
  ],
  feedback: [
    { label: '待处理', value: 'pending' },
    { label: '已采纳', value: 'adopted' },
    { label: '已完成', value: 'completed' },
    { label: '暂不处理', value: 'rejected' },
  ],
}
const MANAGE_LIST_CONFIG = {
  pendingWithdraw: {
    moduleId: 'pending-withdraw',
    api: '/api/manage/transfer-requests',
    dataKey: 'pendingWithdrawList',
    defaultPageSize: 10,
  },
  pendingFeedback: {
    moduleId: 'pending-feedback',
    api: '/api/manage/pending-feedbacks',
    dataKey: 'pendingFeedbackList',
    defaultPageSize: 10,
  },
  recharge: {
    moduleId: 'recharge',
    api: '/api/manage/recharges',
    dataKey: 'rechargeList',
    defaultPageSize: 10,
  },
  guarantee: {
    moduleId: 'guarantee',
    api: '/api/manage/guarantees',
    dataKey: 'guaranteeList',
    defaultPageSize: 10,
  },
  feedback: {
    moduleId: 'feedback',
    api: '/api/manage/feedbacks',
    dataKey: 'feedbackList',
    defaultPageSize: 10,
  },
}
const SNAPSHOT_PRESET_OPTIONS = [
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '自定义', value: 'custom' },
]


function createEmptySnapshot() {
  return {
    rechargeCount: 0,
    rechargeAmount: 0,
    transferCount: 0,
    transferAmount: 0,
    guaranteeFeeAmount: 0,
    withdrawFeeAmount: 0,
    platformFeeAmount: 0,
    feedbackCount: 0,
  }
}


function createEmptyDashboard() {
  return {
    range: {
      startDate: '',
      endDate: '',
      dayCount: 1,
    },
    totals: {
      userCount: 0,
      walletBalance: 0,
      lockedGems: 0,
      totalRechargeCount: 0,
      totalRechargeAmount: 0,
      rechargeRecordCount: 0,
      completedGuaranteeCount: 0,
      guaranteeRecordCount: 0,
      totalFeedbackCount: 0,
      feedbackRecordCount: 0,
      totalGuaranteeFeeAmount: 0,
      totalWithdrawFeeAmount: 0,
      totalPlatformFeeAmount: 0,
      pendingTransferCount: 0,
      pendingWithdrawCount: 0,
      pendingFeedbackCount: 0,
      communityApplyPendingCount: 0,
      pendingActionCount: 0,
      totalPromotionReward: 0,

      platformAccountBalance: 0,
      allUsersWalletBalance: 0,
    },
    snapshot: createEmptySnapshot(),
    today: createEmptySnapshot(),
    dailyFlow: [],
    rechargeList: [],
    pendingTransferList: [],
    pendingWithdrawList: [],
    pendingFeedbackList: [],
    guaranteeList: [],
    feedbackList: [],
  }
}


function createPagerState(pageSize = 10) {
  return {
    page: 1,
    pageSize,
  }
}

function createFilterState() {
  return {
    query: '',
    status: 'all',
  }
}

function createDrawerDetail() {
  return {
    eyebrow: '',
    title: '',
    subtitle: '',
    description: '',
    statusLabel: '',
    statusTone: 'neutral',
    highlights: [],
    rows: [],
    imageUrl: '',
    imageLabel: '',
    notes: [],
  }
}

function normalizeText(value) {
  return String(value ?? '').trim()
}

function normalizeSearchText(value) {
  return normalizeText(value).toLowerCase()
}

function pickText(...values) {
  for (const value of values) {
    if (value === 0) return '0'
    const text = String(value ?? '').trim()
    if (text) return text
  }
  return ''
}

function displayText(...values) {
  return pickText(...values) || '—'
}



function matchKeyword(query, values = []) {
  const keyword = normalizeSearchText(query)
  if (!keyword) return true
  return values.some((value) => normalizeSearchText(value).includes(keyword))
}

function matchStatus(item = {}, expected = 'all') {
  if (!expected || expected === 'all') return true
  return [item.statusClass, item.statusText, item.status, item.statusDesc, item.status_desc]
    .map((value) => normalizeText(value))
    .filter(Boolean)
    .includes(expected)
}

function filterRows(rows = [], filter = {}, getSearchValues = () => []) {
  return (Array.isArray(rows) ? rows : []).filter((item) => {
    if (!matchStatus(item, filter.status)) return false
    return matchKeyword(filter.query, getSearchValues(item))
  })
}

function createHighlight(label, value) {
  return {
    label,
    value: displayText(value),
  }
}

function createDetailRow(label, value, copyValue = '') {
  const row = {
    label,
    value: displayText(value),
  }
  const copied = pickText(copyValue)
  if (copied) row.copyValue = copied
  return row
}

function normalizeImageUrl(url = '') {
  const raw = String(url || '').trim()
  if (!raw) return ''
  if (/^(https?:)?\/\//i.test(raw) || /^data:/i.test(raw)) return raw
  if (raw.startsWith('/')) return raw
  return `/${raw.replace(/^\.?\//, '')}`
}

function resolveTone(statusClass = '') {
  if (statusClass === 'success' || statusClass === 'done' || statusClass === 'adopted') return 'success'
  if (statusClass === 'matched' || statusClass === 'info' || statusClass === 'completed') return 'info'
  if (statusClass === 'pending') return 'warning'
  if (statusClass === 'cancelled' || statusClass === 'expired' || statusClass === 'appeal' || statusClass === 'rejected') return 'danger'
  return 'neutral'
}

function toTagType(statusClass = '') {
  const tone = resolveTone(statusClass)
  if (tone === 'success') return 'success'
  if (tone === 'warning') return 'warning'
  if (tone === 'danger') return 'danger'
  if (tone === 'info') return 'primary'
  return 'info'
}

function getTotalPages(total, pageSize) {
  const safeSize = Math.max(1, Number(pageSize || 1))
  return Math.max(1, Math.ceil(Number(total || 0) / safeSize))
}

function clampPage(page, totalPages) {
  return Math.min(Math.max(1, Number(page || 1)), Math.max(1, Number(totalPages || 1)))
}

function buildPaginationMeta(rows = [], state = {}) {
  const sourceRows = Array.isArray(rows) ? rows : []
  const safePageSize = Math.max(1, Number(state.pageSize || 10))
  const total = sourceRows.length
  const totalPages = getTotalPages(total, safePageSize)
  const currentPage = clampPage(state.page, totalPages)
  const start = total ? (currentPage - 1) * safePageSize + 1 : 0
  const end = total ? Math.min(currentPage * safePageSize, total) : 0
  const sliceStart = start > 0 ? start - 1 : 0
  return {
    rows: sourceRows.slice(sliceStart, end),
    total,
    totalPages,
    currentPage,
    pageSize: safePageSize,
    start,
    end,
  }
}

function padDatePart(value) {
  return String(value).padStart(2, '0')
}

function formatLocalDate(date = new Date()) {
  const current = date instanceof Date ? date : new Date(date)
  return `${current.getFullYear()}-${padDatePart(current.getMonth() + 1)}-${padDatePart(current.getDate())}`
}

function getTodayRange() {
  const today = formatLocalDate()
  return [today, today]
}

function getCurrentWeekRange() {
  const now = new Date()
  const current = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const day = current.getDay() || 7
  current.setDate(current.getDate() - day + 1)
  return [formatLocalDate(current), formatLocalDate(now)]
}

function getCurrentMonthRange() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  return [formatLocalDate(start), formatLocalDate(now)]
}

function getSnapshotRangeByMode(mode = 'day', customRange = []) {
  if (mode === 'week') {
    const [startDate, endDate] = getCurrentWeekRange()
    return {
      startDate,
      endDate,
      dayCount: Math.max(1, Math.round((new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000) + 1),
    }
  }
  if (mode === 'month') {
    const [startDate, endDate] = getCurrentMonthRange()
    return {
      startDate,
      endDate,
      dayCount: Math.max(1, Math.round((new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000) + 1),
    }
  }
  if (mode === 'custom' && Array.isArray(customRange) && customRange.length === 2 && customRange[0] && customRange[1]) {
    return {
      startDate: customRange[0],
      endDate: customRange[1],
      dayCount: Math.max(1, Math.round((new Date(customRange[1]).getTime() - new Date(customRange[0]).getTime()) / 86400000) + 1),
    }
  }
  const [startDate, endDate] = getTodayRange()
  return {
    startDate,
    endDate,
    dayCount: 1,
  }
}

function formatSnapshotRangeText(startDate = '', endDate = '') {
  if (!startDate && !endDate) return '未选择日期范围'
  if (startDate && endDate && startDate === endDate) return startDate
  return `${startDate || '未设开始'} 至 ${endDate || '未设结束'}`
}

function getSnapshotLabelPrefix(mode = 'day') {
  if (mode === 'week') return '本周'
  if (mode === 'month') return '本月'
  if (mode === 'custom') return '所选区间'
  return '今日'
}

function buildRechargeDetail(item = {}) {

  return {
    eyebrow: 'RECHARGE DETAIL',
    title: `${pickText(item.userNickName, '方块兽玩家')} · 充值记录`,
    subtitle: `订单 ${displayText(item.id)}`,
    description: item.matchedTime
      ? `这笔充值已完成到账，到账时间为 ${displayText(item.matchedTime)}。`
      : '这条充值记录可用于核对账号、方块兽 ID、校验码与到账状态。',
    statusLabel: displayText(item.statusText, '未知状态'),
    statusTone: item.statusClass || item.status,
    highlights: [
      createHighlight('到账数量', `+${formatNumber(item.amount || 0)}`),
      createHighlight('订单状态', displayText(item.statusText, '未知状态')),
      createHighlight('记录时间', displayText(item.time)),
      createHighlight('到账时间', displayText(item.matchedTime, '未到账')),
    ],
    rows: [
      createDetailRow('订单号', item.id, item.id),
      createDetailRow('账号', item.account, item.account),
      createDetailRow('方块兽 ID', item.beastId, item.beastId),
      createDetailRow('校验码', item.verifyCode, item.verifyCode),
      createDetailRow('订单状态', item.statusText),
      createDetailRow('记录时间', item.time),
      createDetailRow('到账时间', item.matchedTime, item.matchedTime),
    ],
    notes: [
      item.statusClass === 'success' ? '这笔充值已经成功记账。' : '建议结合后端日志进一步核验。',
      '如需二次确认，请同时对照用户账号、方块兽 ID 与校验码。',
    ],
  }
}

function buildGuaranteeDetail(item = {}, { fromQueue = false } = {}) {
  const proofImage = normalizeImageUrl(item.buyerProofImage || item.buyer_proof_image)
  const proofUploadedTime = item.buyerProofUploadedTime || item.buyer_proof_uploaded_time || item.buyerProofUploadedAt || item.buyer_proof_uploaded_at || ''
  const sellerName = displayText(item.sellerNickName, '未设置卖家')
  const buyerName = displayText(item.buyerBeastNick, item.buyer_beast_nick, '未填写买家')
  return {
    eyebrow: fromQueue ? 'PENDING GUARANTEE' : 'GUARANTEE DETAIL',
    title: `${displayText(item.petName, item.pet_name, '未填写兽王')} · ${formatNumber(item.tradeQuantity ?? item.trade_quantity ?? 0)} 只`,
    subtitle: `订单 ${displayText(item.id || item.orderNo)} · ${displayText(item.statusDesc, item.statusText)}`,
    description: `卖家 ${sellerName} 与买家 ${buyerName} 的担保交易。${proofImage ? '买家已上传截图凭证，可直接查看大图。' : '当前还没有截图凭证。'}${fromQueue ? ' 当前队列仅用于跟踪卖家确认与系统自动到账进度。' : ''}`,
    statusLabel: displayText(item.statusText, '未知状态'),
    statusTone: item.statusClass || item.statusRaw,
    highlights: [
      createHighlight('保单标价', formatNumber(item.gemAmount ?? item.gem_amount ?? 0)),
      createHighlight('卖家实扣', formatNumber(item.sellerTotalCost ?? item.seller_total_cost ?? ((item.gemAmount ?? item.gem_amount ?? 0) + (item.feeAmount ?? item.fee_amount ?? 0)))),
      createHighlight('买家实收', formatNumber(item.actualReceive ?? item.actual_receive ?? 0)),
      createHighlight('匹配时间', displayText(item.matchedTime, item.matched_time)),
    ],
    rows: [
      createDetailRow('担保单号', item.id || item.orderNo, item.id || item.orderNo),
      createDetailRow('卖家昵称', item.sellerNickName),
      createDetailRow('卖家猎人 ID', item.sellerGameId || item.seller_game_id, item.sellerGameId || item.seller_game_id),
      createDetailRow('卖家方块兽 ID', item.sellerBeastId || item.seller_beast_id, item.sellerBeastId || item.seller_beast_id),
      createDetailRow('买家昵称', item.buyerBeastNick || item.buyer_beast_nick),
      createDetailRow('买家方块兽 ID', item.buyerBeastId || item.buyer_beast_id, item.buyerBeastId || item.buyer_beast_id),
      createDetailRow('交易数量', `${formatNumber(item.tradeQuantity ?? item.trade_quantity ?? 0)} 只`),
      createDetailRow('保单标价', formatNumber(item.gemAmount ?? item.gem_amount ?? 0)),
      createDetailRow('卖家实扣', formatNumber(item.sellerTotalCost ?? item.seller_total_cost ?? ((item.gemAmount ?? item.gem_amount ?? 0) + (item.feeAmount ?? item.fee_amount ?? 0)))),
      createDetailRow('买家到账手续费', formatNumber(item.buyerFeeAmount ?? item.buyer_fee_amount ?? item.feeAmount ?? item.fee_amount ?? 0)),
      createDetailRow('总手续费', formatNumber(item.totalFeeAmount ?? item.total_fee_amount ?? ((item.feeAmount ?? item.fee_amount ?? 0) * 2))),
      createDetailRow('买家实收', formatNumber(item.actualReceive ?? item.actual_receive ?? 0)),
      createDetailRow('买家备注', item.buyerTradeNote || item.buyer_trade_note),
      createDetailRow('后台备注', item.adminNote || item.admin_note),
      createDetailRow('创建时间', item.createTime || item.create_time),
      createDetailRow('匹配时间', item.matchedTime || item.matched_time),
      createDetailRow('截图上传', proofUploadedTime),
      createDetailRow('卖家确认', item.sellerConfirmedTime || item.seller_confirmed_time),
      createDetailRow('完成时间', item.finishedTime || item.finished_time),
    ],
    imageUrl: proofImage,
    imageLabel: 'BUYER PROOF',
    notes: [
      displayText(item.statusDesc, '这笔担保单已进入后台处理链路。'),
      item.sellerConfirmed ? '卖家已确认交易完成，系统会按“买卖双方各扣 1 宝石”的规则自动结算。' : '卖家尚未确认交易完成，系统会在确认后自动按双边手续费规则到账。',
      fromQueue ? '该队列用于跟踪担保进度与留痕，不需要后台手动转出。' : '可通过截图时间、匹配时间、手续费与后台备注快速复盘整笔担保流程。',
    ],
  }
}



function buildWithdrawDetail(item = {}) {
  return {
    eyebrow: 'USER TRANSFER',
    title: `${pickText(item.userNickName, '方块兽玩家')} · 转出申请`,
    subtitle: `申请 ${displayText(item.id)} · ${displayText(item.statusText)}`,
    description: '用户主动发起的人工转出申请会集中在这里复核。建议先确认账号、方块兽 ID 和预计实转数量，再登记完成。',
    statusLabel: displayText(item.statusText, '待处理'),
    statusTone: item.statusClass || item.status,
    highlights: [
      createHighlight('申请数量', formatNumber(item.requestAmount ?? item.request_amount ?? 0)),
      createHighlight('手续费', formatNumber(item.feeAmount ?? item.fee_amount ?? 0)),
      createHighlight('预计实转', formatNumber(item.actualAmount ?? item.actual_amount ?? 0)),
      createHighlight('提交时间', displayText(item.createTime)),
    ],
    rows: [
      createDetailRow('申请编号', item.id, item.id),
      createDetailRow('用户昵称', item.userNickName),
      createDetailRow('账号', item.account, item.account),
      createDetailRow('方块兽 ID', item.beastId, item.beastId),
      createDetailRow('方块兽昵称', item.beastNick),
      createDetailRow('申请数量', formatNumber(item.requestAmount ?? item.request_amount ?? 0)),
      createDetailRow('手续费', formatNumber(item.feeAmount ?? item.fee_amount ?? 0)),
      createDetailRow('预计实转', formatNumber(item.actualAmount ?? item.actual_amount ?? 0)),
      createDetailRow('费率', item.feeRateText),
      createDetailRow('用户备注', item.userNote),
      createDetailRow('后台备注', item.adminNote),
      createDetailRow('提交时间', item.createTime),
      createDetailRow('处理时间', item.processedTime),
    ],
    notes: [
      '处理前建议先在游戏内核对该用户的方块兽 ID，避免误转。',
      displayText(item.statusDesc, '该申请仍等待后台人工确认。'),
    ],
  }
}

function buildFeedbackDetail(item = {}, { fromQueue = false } = {}) {
  return {
    eyebrow: fromQueue ? 'PENDING FEEDBACK' : 'FEEDBACK DETAIL',
    title: displayText(item.title, '未命名反馈'),
    subtitle: `反馈 #${displayText(item.id)} · ${displayText(item.type, '其他')}`,
    description: displayText(item.content, '暂无反馈内容'),
    statusLabel: displayText(item.statusText, '待处理'),
    statusTone: item.statusClass || item.status,
    highlights: [
      createHighlight('反馈类型', displayText(item.type, '其他')),
      createHighlight('当前状态', displayText(item.statusText, '待处理')),
      createHighlight('提交用户', displayText(item.userNickName, '方块兽玩家')),
      createHighlight('提交时间', displayText(item.time)),
    ],
    rows: [
      createDetailRow('反馈编号', item.id, item.id),
      createDetailRow('用户昵称', item.userNickName),
      createDetailRow('账号', item.account, item.account),
      createDetailRow('方块兽 ID', item.beastId, item.beastId),
      createDetailRow('联系方式', item.contact, item.contact),
      createDetailRow('反馈内容', item.content),
      createDetailRow('处理说明', item.adminReply),
      createDetailRow('提交时间', item.time),
      createDetailRow('处理时间', item.handledTime),
    ],
    notes: [
      displayText(item.statusDesc, '建议先判断是否属于 Bug，再决定采纳、完成或暂不处理。'),
      fromQueue ? '这条反馈仍位于待处理工作池，可直接在表格中快捷处理。' : '这条反馈已进入归档区，适合做复盘和问题闭环跟踪。',
    ],
  }
}

const dashboard = ref(createEmptyDashboard())
const loading = ref(true)
const refreshing = ref(false)
const settlingMonth = ref(false)
const activeModule = ref('overview')
const drawerVisible = ref(false)
const drawerDetail = ref(createDrawerDetail())
const lastLoadedAt = ref(0)
const snapshotFilter = reactive({
  mode: 'day',
  customRange: getTodayRange(),
})
const userPanelRef = ref(null)

const promotionPanelRef = ref(null)
const homeContentPanelRef = ref(null)
const tokenPanelRef = ref(null)
const communityApplyPanelRef = ref(null)
const layoutFeedbackPanelRef = ref(null)
const moduleCounts = reactive({
  'user-manage': 0,
  'promotion-manage': 0,
  'home-content': 0,
  'token-manage': 0,
  'community-manage': 0,
  'community-apply-manage': 0,
  'layout-feedback-manage': 0,
})


const pagination = reactive({
  pendingWithdraw: createPagerState(10),
  pendingFeedback: createPagerState(10),
  recharge: createPagerState(10),
  guarantee: createPagerState(10),
  feedback: createPagerState(10),
})
const listFilters = reactive({
  pendingWithdraw: createFilterState(),
  pendingFeedback: createFilterState(),
  recharge: createFilterState(),
  guarantee: createFilterState(),
  feedback: createFilterState(),
  daily: createFilterState(),
})
const listTotals = reactive({
  pendingWithdraw: 0,
  pendingFeedback: 0,
  recharge: 0,
  guarantee: 0,
  feedback: 0,
})
const actionBusy = reactive({
  withdraw: '',
  feedback: '',
})



const countMap = computed(() => ({
  overview: dashboard.value.totals.pendingActionCount ?? 0,
  'user-manage': moduleCounts['user-manage'],
  'promotion-manage': moduleCounts['promotion-manage'],
  'home-content': moduleCounts['home-content'],
  'token-manage': moduleCounts['token-manage'],
  'community-apply-manage': moduleCounts['community-apply-manage'] || dashboard.value.totals.communityApplyPendingCount || 0,
  'layout-feedback-manage': moduleCounts['layout-feedback-manage'],

  'pending-withdraw': listTotals.pendingWithdraw || dashboard.value.totals.pendingWithdrawCount || dashboard.value.pendingWithdrawList.length,
  'pending-feedback': listTotals.pendingFeedback || dashboard.value.totals.pendingFeedbackCount || dashboard.value.pendingFeedbackList.length,
  recharge: listTotals.recharge || dashboard.value.totals.rechargeRecordCount || dashboard.value.rechargeList.length,
  guarantee: listTotals.guarantee || dashboard.value.totals.guaranteeRecordCount || dashboard.value.guaranteeList.length,
  feedback: listTotals.feedback || dashboard.value.totals.feedbackRecordCount || dashboard.value.feedbackList.length,
  daily: filteredDailyRows.value.length || dashboard.value.dailyFlow.length,
}))




const currentSection = computed(() => DASHBOARD_SECTIONS.find((item) => item.id === activeModule.value) || DASHBOARD_SECTIONS[0])
const sectionIconMap = {
  overview: HomeFilled,
  'user-manage': User,
  'promotion-manage': Connection,
  'home-content': HomeFilled,
  'pending-withdraw': Promotion,
  'pending-feedback': ChatDotRound,
  recharge: Money,
  guarantee: Files,
  feedback: ChatDotRound,
  daily: DataAnalysis,
  'token-manage': Key,
  'community-manage': Promotion,
  'community-apply-manage': ChatDotRound,
  'layout-feedback-manage': EditPen,
}
const pendingBadgeSections = new Set(['overview', 'pending-withdraw', 'pending-feedback', 'token-manage', 'community-apply-manage'])

const currentSectionCount = computed(() => formatNumber(countMap.value[currentSection.value?.id] ?? 0))
// ── 账户宝石余额实时刷新 ──────────────────────────────────────────────
const liveGemBalance = ref(null)       // null=未查 | number=已查
const liveGemLoading = ref(false)
const liveGemError = ref('')
let liveGemAutoTimer = null

async function fetchLiveGemBalance() {
  liveGemLoading.value = true
  liveGemError.value = ''
  try {
    const data = await api.get('/api/manage/gem-balance')
    liveGemBalance.value = data.balance ?? data.data?.balance ?? null
  } catch (err) {
    liveGemError.value = err.message || '查询失败'
    liveGemBalance.value = null
  } finally {
    liveGemLoading.value = false
  }
}

function stopLiveGemAutoRefresh() {
  if (liveGemAutoTimer) {
    clearInterval(liveGemAutoTimer)
    liveGemAutoTimer = null
  }
}

function startLiveGemAutoRefresh() {
  stopLiveGemAutoRefresh()
  if (activeModule.value !== 'overview') return
  liveGemAutoTimer = setInterval(() => {
    if (!liveGemLoading.value) {
      fetchLiveGemBalance()
    }
  }, 60000)
}

const summaryCards = computed(() => [
  {
    label: '累计充值',
    value: formatNumber(dashboard.value.totals.totalRechargeAmount),
    helper: `${formatNumber(dashboard.value.totals.totalRechargeCount)} 笔订单`,
  },
  {
    label: '累计手续费',
    value: formatNumber(dashboard.value.totals.totalPlatformFeeAmount),
    helper: `担保 ${formatNumber(dashboard.value.totals.totalGuaranteeFeeAmount)} / 转出 ${formatNumber(dashboard.value.totals.totalWithdrawFeeAmount)}`,
  },
  {
    label: '已完成担保',
    value: formatNumber(dashboard.value.totals.completedGuaranteeCount),
    helper: `总用户 ${formatNumber(dashboard.value.totals.userCount)}`,
  },
  {
    label: '锁定宝石',
    value: formatNumber(dashboard.value.totals.lockedGems),
    helper: `钱包总量 ${formatNumber(dashboard.value.totals.walletBalance)}`,
  },
  {
    label: '待办总量',
    value: formatNumber(dashboard.value.totals.pendingActionCount),
    helper: `反馈 ${formatNumber(dashboard.value.totals.pendingFeedbackCount)} / 转出 ${formatNumber(dashboard.value.totals.pendingTransferCount + dashboard.value.totals.pendingWithdrawCount)}`,
  },
  {
    label: '账户宝石余额',
    value: liveGemBalance.value !== null
      ? formatNumber(liveGemBalance.value)
      : formatNumber(dashboard.value.totals.platformAccountBalance),
    helper: liveGemBalance.value !== null ? '游戏接口实时余额' : '估算值（点刷新获取实时）',
    highlight: true,
    isGemCard: true,
  },
  {
    label: '用户钱包总余额',
    value: formatNumber(dashboard.value.totals.allUsersWalletBalance),
    helper: `所有用户累计充值 ${formatNumber(dashboard.value.totals.totalRechargeAmount)}`,
    highlight: true,
  },
  {
    label: '推广总奖励',
    value: formatNumber(dashboard.value.totals.totalPromotionReward),
    helper: '已发放推广佣金宝石数',
    highlight: true,
  },
])
const resolvedSnapshotRange = computed(() => getSnapshotRangeByMode(snapshotFilter.mode, snapshotFilter.customRange))
const dashboardRange = computed(() => {
  const range = dashboard.value.range || {}
  return {
    startDate: range.startDate || resolvedSnapshotRange.value.startDate,
    endDate: range.endDate || resolvedSnapshotRange.value.endDate,
    dayCount: Number(range.dayCount || resolvedSnapshotRange.value.dayCount || 1),
  }
})
const snapshotRangeText = computed(() => formatSnapshotRangeText(dashboardRange.value.startDate, dashboardRange.value.endDate))
const snapshotLabelPrefix = computed(() => getSnapshotLabelPrefix(snapshotFilter.mode))
const snapshotTitle = computed(() => `${snapshotLabelPrefix.value}经营快照`)
const snapshotTagText = computed(() => (dashboardRange.value.dayCount <= 1 ? '当日汇总' : `${dashboardRange.value.dayCount} 天汇总`))
const snapshotData = computed(() => ({
  ...createEmptySnapshot(),
  ...(dashboard.value.snapshot || dashboard.value.today || {}),
}))
const snapshotCards = computed(() => [
  {
    label: `${snapshotLabelPrefix.value}充值`,
    value: formatNumber(snapshotData.value.rechargeAmount),
    helper: `${formatNumber(snapshotData.value.rechargeCount)} 笔到账`,
  },
  {
    label: `${snapshotLabelPrefix.value}手续费`,
    value: formatNumber(snapshotData.value.platformFeeAmount),
    helper: `担保 ${formatNumber(snapshotData.value.guaranteeFeeAmount)} / 转出 ${formatNumber(snapshotData.value.withdrawFeeAmount)}`,
  },
  {
    label: `${snapshotLabelPrefix.value}转出`,
    value: formatNumber(snapshotData.value.transferAmount),
    helper: `${formatNumber(snapshotData.value.transferCount)} 笔处理`,
  },
  {
    label: `${snapshotLabelPrefix.value}反馈`,
    value: formatNumber(snapshotData.value.feedbackCount),
    helper: `待处理 ${formatNumber(dashboard.value.totals.pendingFeedbackCount)} 条`,
  },
  {
    label: '待处理队列',
    value: formatNumber(dashboard.value.totals.pendingActionCount),
    helper: `担保 ${formatNumber(dashboard.value.totals.pendingTransferCount)} / 用户 ${formatNumber(dashboard.value.totals.pendingWithdrawCount)} / 反馈 ${formatNumber(dashboard.value.totals.pendingFeedbackCount)}`,
  },
])
const overviewTrendTitle = computed(() => (dashboardRange.value.dayCount <= 1 ? '当日走势' : `${dashboardRange.value.dayCount} 天走势`))
const overviewTrendEmptyText = computed(() => `暂无${overviewTrendTitle.value}数据`)


const overviewTrendRows = computed(() => dashboard.value.dailyFlow.slice().reverse())

const filteredDailyRows = computed(() =>
  filterRows(overviewTrendRows.value, listFilters.daily, (item = {}) => [
    item.date,
    item.rechargeAmount,
    item.rechargeCount,
    item.transferAmount,
    item.transferCount,
    item.guaranteeCreatedCount,
    item.feedbackCount,
    item.platformFeeAmount,
  ]),
)

function buildRemotePager(listKey, rows = []) {
  const state = pagination[listKey] || createPagerState(10)
  const total = Number(listTotals[listKey] || 0)
  const pageSize = Math.max(1, Number(state.pageSize || 10))
  return {
    rows: Array.isArray(rows) ? rows : [],
    total,
    currentPage: Math.max(1, Number(state.page || 1)),
    pageSize,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
  }
}

const pendingWithdrawPager = computed(() => buildRemotePager('pendingWithdraw', dashboard.value.pendingWithdrawList))
const pendingFeedbackPager = computed(() => buildRemotePager('pendingFeedback', dashboard.value.pendingFeedbackList))
const rechargePager = computed(() => buildRemotePager('recharge', dashboard.value.rechargeList))
const guaranteePager = computed(() => buildRemotePager('guarantee', dashboard.value.guaranteeList))
const feedbackPager = computed(() => buildRemotePager('feedback', dashboard.value.feedbackList))



function getManageListKeyByModule(moduleId = '') {
  return Object.keys(MANAGE_LIST_CONFIG).find((key) => MANAGE_LIST_CONFIG[key].moduleId === moduleId) || ''
}

function getDashboardTotalByListKey(listKey) {
  if (listKey === 'pendingWithdraw') return Number(dashboard.value.totals.pendingWithdrawCount || 0)
  if (listKey === 'pendingFeedback') return Number(dashboard.value.totals.pendingFeedbackCount || 0)
  if (listKey === 'recharge') return Number(dashboard.value.totals.rechargeRecordCount || 0)
  if (listKey === 'guarantee') return Number(dashboard.value.totals.guaranteeRecordCount || 0)
  if (listKey === 'feedback') return Number(dashboard.value.totals.feedbackRecordCount || 0)
  return 0
}

function applyDashboardListTotals() {
  listTotals.pendingWithdraw = getDashboardTotalByListKey('pendingWithdraw') || dashboard.value.pendingWithdrawList.length
  listTotals.pendingFeedback = getDashboardTotalByListKey('pendingFeedback') || dashboard.value.pendingFeedbackList.length
  listTotals.recharge = getDashboardTotalByListKey('recharge') || dashboard.value.rechargeList.length
  listTotals.guarantee = getDashboardTotalByListKey('guarantee') || dashboard.value.guaranteeList.length
  listTotals.feedback = getDashboardTotalByListKey('feedback') || dashboard.value.feedbackList.length
}

function buildManageListUrl(listKey) {
  const config = MANAGE_LIST_CONFIG[listKey]
  const filterState = listFilters[listKey]
  const pageState = pagination[listKey]
  if (!config || !filterState || !pageState) return ''

  const params = new URLSearchParams({
    page: String(pageState.page || 1),
    page_size: String(pageState.pageSize || config.defaultPageSize || 10),
  })

  if (normalizeText(filterState.query)) {
    params.set('query', normalizeText(filterState.query))
  }
  if (filterState.status && filterState.status !== 'all') {
    params.set('status', filterState.status)
  }

  return `${config.api}?${params.toString()}`
}

async function loadManageList(listKey, { silent = false } = {}) {
  const config = MANAGE_LIST_CONFIG[listKey]
  if (!config) return

  const requestUrl = buildManageListUrl(listKey)
  if (!requestUrl) return

  if (!silent) loading.value = true
  try {
    const data = await api.get(requestUrl)
    const nextList = Array.isArray(data.list) ? data.list : []
    const nextPagination = data.pagination || {}

    dashboard.value = {
      ...dashboard.value,
      [config.dataKey]: nextList,
    }
    listTotals[listKey] = Number(nextPagination.total || nextList.length || 0)
    pagination[listKey].page = Math.max(1, Number(nextPagination.page || pagination[listKey].page || 1))
    pagination[listKey].pageSize = Math.max(1, Number(nextPagination.pageSize || pagination[listKey].pageSize || config.defaultPageSize || 10))
  } catch (error) {
    ElMessage.error(error.message || '读取列表数据失败')
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

function handleManageListSearch(listKey) {
  const pageState = pagination[listKey]
  if (pageState) {
    pageState.page = 1
  }
  loadManageList(listKey)
}

function handleManageListReset(listKey) {
  const filterState = listFilters[listKey]
  const pageState = pagination[listKey]
  const config = MANAGE_LIST_CONFIG[listKey]
  if (!filterState || !pageState || !config) return

  filterState.query = ''
  filterState.status = 'all'
  pageState.page = 1
  pageState.pageSize = config.defaultPageSize || 10
  loadManageList(listKey)
}

function handleManageListPageChange(listKey, page) {
  const pageState = pagination[listKey]
  if (!pageState) return
  pageState.page = Math.max(1, Number(page || 1))
  loadManageList(listKey, { silent: true })
}

function handleManageListPageSizeChange(listKey, pageSize) {
  const pageState = pagination[listKey]
  if (!pageState) return
  pageState.pageSize = Math.max(1, Number(pageSize || 10))
  pageState.page = 1
  loadManageList(listKey, { silent: true })
}

function hasActiveFilters(listKey) {
  const state = listFilters[listKey]
  return !!state && (!!normalizeText(state.query) || state.status !== 'all')
}

function resetListFilters(listKey) {
  const state = listFilters[listKey]
  if (!state) return
  state.query = ''
  state.status = 'all'
}


function closeDrawer() {
  drawerVisible.value = false
}

function openDrawer(detail) {
  drawerDetail.value = {
    ...createDrawerDetail(),
    ...detail,
  }
  drawerVisible.value = true
}

async function copyText(action) {
  const value = String(action?.value || '').trim()
  if (!value) {
    ElMessage.warning('没有可复制的内容')
    return
  }

  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success(`${action.label || '内容'}已复制`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

function handleInspect(type, item) {
  if (!item) {
    ElMessage.warning('没有可查看的详情')
    return
  }

  if (type === 'recharge') return openDrawer(buildRechargeDetail(item))
  if (type === 'guarantee') return openDrawer(buildGuaranteeDetail(item))
  if (type === 'pending-withdraw') return openDrawer(buildWithdrawDetail(item))
  if (type === 'feedback') return openDrawer(buildFeedbackDetail(item))
  if (type === 'pending-feedback') return openDrawer(buildFeedbackDetail(item, { fromQueue: true }))
}

function buildDashboardRequestUrl(limit = 0) {
  const range = resolvedSnapshotRange.value
  const params = new URLSearchParams({
    limit: String(Math.max(0, Number(limit || 0))),
    start_date: range.startDate,
    end_date: range.endDate,
    days: String(range.dayCount || 1),
  })
  return `/api/manage/dashboard?${params.toString()}`
}

async function handleSnapshotPresetChange(mode) {
  if (!mode) return
  snapshotFilter.mode = mode
  if (mode === 'custom' && (!Array.isArray(snapshotFilter.customRange) || snapshotFilter.customRange.length !== 2)) {
    snapshotFilter.customRange = getTodayRange()
  }
  await loadDashboard({ silent: true })
}

async function handleSnapshotCustomRangeChange(range) {
  if (!Array.isArray(range) || range.length !== 2 || !range[0] || !range[1]) return
  snapshotFilter.mode = 'custom'
  await loadDashboard({ silent: true })
}

async function loadDashboard({ silent = false } = {}) {
  refreshing.value = true
  if (!silent) loading.value = true

  try {
    const data = await api.get(buildDashboardRequestUrl(0))
    dashboard.value = {
      ...createEmptyDashboard(),
      ...data,
    }
    applyDashboardListTotals()
    lastLoadedAt.value = Date.now()
  } catch (error) {
    ElMessage.error(error.message || '读取管理台数据失败')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}


async function handleMenuSelect(index) {
  activeModule.value = index
  const listKey = getManageListKeyByModule(index)
  if (!listKey) return
  await loadManageList(listKey)
}

function setModuleCount(moduleId, count) {
  if (!(moduleId in moduleCounts)) return
  moduleCounts[moduleId] = Number(count || 0)
}

function handleUserCountChange(count) {
  setModuleCount('user-manage', count)
}

function handlePromotionCountChange(count) {
  setModuleCount('promotion-manage', count)
}

function handleHomeContentCountChange(count) {
  setModuleCount('home-content', count)
}

function handleTokenCountChange(count) {
  setModuleCount('token-manage', count)
}

function handleCommunityApplyCountChange(count) {
  setModuleCount('community-apply-manage', count)
}

function handleLayoutFeedbackCountChange(count) {
  setModuleCount('layout-feedback-manage', count)
}

async function reloadDashboardWithCurrentModule({ silent = true } = {}) {

  await loadDashboard({ silent })
  const listKey = getManageListKeyByModule(activeModule.value)
  if (!listKey) return
  await loadManageList(listKey, { silent: true })
}

async function handleRefresh() {
  if (activeModule.value === 'user-manage') {
    refreshing.value = true
    try {
      await userPanelRef.value?.reload?.({ silent: true })
    } finally {
      refreshing.value = false
    }
    return
  }

  if (activeModule.value === 'promotion-manage') {
    refreshing.value = true
    try {
      await promotionPanelRef.value?.reload?.({ silent: true })
    } finally {
      refreshing.value = false
    }
    return
  }

  if (activeModule.value === 'home-content') {
    refreshing.value = true
    try {
      await homeContentPanelRef.value?.reload?.({ silent: true })
    } finally {
      refreshing.value = false
    }
    return
  }

  if (activeModule.value === 'token-manage') {
    refreshing.value = true
    try {
      await tokenPanelRef.value?.reload?.()
    } finally {
      refreshing.value = false
    }
    return
  }

  if (activeModule.value === 'layout-feedback-manage') {
    refreshing.value = true
    try {
      await layoutFeedbackPanelRef.value?.reload?.()
    } finally {
      refreshing.value = false
    }
    return
  }

  const listKey = getManageListKeyByModule(activeModule.value)
  if (!listKey) {
    await loadDashboard({ silent: true })
    return
  }

  refreshing.value = true
  try {
    await Promise.all([
      loadDashboard({ silent: true }),
      loadManageList(listKey, { silent: true }),
    ])
  } finally {
    refreshing.value = false
  }
}




async function handleLogout() {
  await auth.logout()
  await router.replace({ name: 'login' })
}

async function handleWithdrawSubmit(requestId) {
  if (!requestId) return

  try {
    await ElMessageBox.confirm('请确认你已经按用户绑定的方块兽 ID 完成人工转出，确认后会登记为完成。', '登记用户转出完成', {
      type: 'warning',
      confirmButtonText: '确认登记',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  actionBusy.withdraw = requestId
  try {
    await api.post('/api/manage/transfer-request/complete', {
      request_id: requestId,
      admin_note: '猎宝保后台已记录用户转出完成',
    })
    closeDrawer()
    ElMessage.success('已记录用户转出完成')
    await reloadDashboardWithCurrentModule({ silent: true })

  } catch (error) {
    ElMessage.error(error.message || '记录用户转出失败')
  } finally {
    actionBusy.withdraw = ''
  }
}

async function handleWithdrawReject(item) {
  if (!item?.id) return

  let promptResult
  try {
    promptResult = await ElMessageBox.prompt('请填写拒绝原因，系统会把锁定宝石退回用户账户。', '拒绝转出申请', {
      confirmButtonText: '确认拒绝',
      cancelButtonText: '取消',
      inputValue: item.adminNote || '资料有误，请核对方块兽 ID 或备注后重新提交',
      inputPlaceholder: '请输入拒绝原因',
    })
  } catch {
    return
  }

  actionBusy.withdraw = item.id
  try {
    await api.post('/api/manage/transfer-request/reject', {
      request_id: item.id,
      admin_note: String(promptResult.value || '').trim() || '资料有误，请核对后重新提交',
    })
    closeDrawer()
    ElMessage.success('已拒绝该转出申请，宝石已退回用户')
    await loadDashboard({ silent: true })
  } catch (error) {
    ElMessage.error(error.message || '拒绝用户转出失败')
  } finally {
    actionBusy.withdraw = ''
  }
}


async function handleFeedbackSubmit({ item, status }) {
  if (!item?.id || !status) return

  const actionTextMap = {
    adopted: '已采纳',
    completed: '已完成',
    rejected: '暂不处理',
  }
  const defaultReplyMap = {
    adopted: '该反馈已采纳，我们会尽快安排处理。',
    completed: '该反馈已处理完成，感谢你的建议。',
    rejected: '该反馈已收到，但当前版本暂不处理。',
  }

  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(`把这条反馈标记为“${actionTextMap[status]}”，可补充处理说明：`, '更新反馈状态', {
      confirmButtonText: '提交',
      cancelButtonText: '取消',
      inputValue: item.adminReply || defaultReplyMap[status] || '',
      inputPlaceholder: '请输入处理说明',
    })
  } catch {
    return
  }

  actionBusy.feedback = String(item.id)
  try {
    await api.post('/api/manage/feedback/update-status', {
      feedback_id: item.id,
      status,
      admin_reply: String(promptResult.value || '').trim() || defaultReplyMap[status],
    })
    closeDrawer()
    ElMessage.success(`反馈已标记为${actionTextMap[status]}`)
    await reloadDashboardWithCurrentModule({ silent: true })
  } catch (error) {
    ElMessage.error(error.message || '更新反馈状态失败')
  } finally {
    actionBusy.feedback = ''
  }
}


async function handleSettleMonth() {
  let promptResult
  const defaultMonth = new Date().toISOString().slice(0, 7)
  try {
    promptResult = await ElMessageBox.prompt(
      '输入要结算的月份（格式 YYYY-MM）。每月只能结算一次，有幂等保护。',
      '月度推广结算',
      {
        confirmButtonText: '确认结算',
        cancelButtonText: '取消',
        inputValue: defaultMonth,
        inputPlaceholder: 'YYYY-MM',
      }
    )
  } catch {
    return
  }
  const yearMonth = String(promptResult.value || '').trim()
  if (!/^\d{4}-\d{2}$/.test(yearMonth)) {
    ElMessage.error('格式不正确，应为 YYYY-MM')
    return
  }
  settlingMonth.value = true
  try {
    const res = await api.post('/api/manage/promotion/settle-monthly', { year_month: yearMonth })
    ElMessage.success(res.message || `${yearMonth} 月结算完成，共 ${res.count ?? 0} 条`)
    await loadDashboard({ silent: true })
  } catch (e) {
    ElMessage.error(e.message || '月度结算失败')
  } finally {
    settlingMonth.value = false
  }
}

onMounted(async () => {
  const ok = await auth.authCheck()
  if (!ok) {
    await router.replace({ name: 'login' })
    return
  }
  await loadDashboard()
  await fetchLiveGemBalance()
  startLiveGemAutoRefresh()
})

watch(activeModule, () => {
  if (activeModule.value === 'overview') {
    fetchLiveGemBalance()
  }
  startLiveGemAutoRefresh()
})

onBeforeUnmount(() => {
  stopLiveGemAutoRefresh()
})
</script>

<template>
  <el-container class="admin-layout">
    <el-aside width="208px" class="admin-aside">
      <div class="brand-panel">
        <div class="brand-mark">猎</div>
        <div class="brand-copy">
          <div class="brand-title">猎宝保后台</div>
        </div>
      </div>

      <el-menu class="side-menu" :default-active="activeModule" @select="handleMenuSelect">
        <el-menu-item v-for="section in DASHBOARD_SECTIONS" :key="section.id" :index="section.id">
          <div class="menu-main">
            <el-icon class="menu-icon">
              <component :is="sectionIconMap[section.id] || Connection" />
            </el-icon>
            <span>{{ section.title }}</span>
          </div>
          <span
            v-if="pendingBadgeSections.has(section.id) && Number(countMap[section.id] || 0) > 0"
            class="menu-count"
          >
            {{ countMap[section.id] }}
          </span>
        </el-menu-item>
      </el-menu>

      <div class="aside-footer">
        <el-button type="danger" plain class="logout-btn" size="default" @click="handleLogout">退出登录</el-button>
      </div>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="page-toolbar">
          <div class="page-main">
            <div class="page-breadcrumb">首页 / {{ currentSection.title }}</div>
            <div class="page-title-row">
              <h1 class="page-title">{{ currentSection.title }}</h1>
              <el-tag effect="plain" type="info">{{ currentSectionCount }} 条</el-tag>
            </div>
            <div class="page-desc">{{ currentSection.desc }}</div>
          </div>
          <div class="page-stats">
            <div class="page-stat">
              <div class="page-stat-label">待办总量</div>
              <div class="page-stat-value">{{ formatNumber(dashboard.totals.pendingActionCount) }}</div>
            </div>
            <div class="page-stat">
              <div class="page-stat-label">当前模块</div>
              <div class="page-stat-value">{{ currentSectionCount }}</div>
            </div>
            <div class="header-actions">
              <el-button :loading="refreshing" @click="handleRefresh">刷新</el-button>
              <el-button type="primary" plain @click="activeModule = 'overview'">总览</el-button>
            </div>
          </div>
        </div>
      </el-header>

      <el-main class="admin-main">
        <template v-if="activeModule === 'overview'">
          <el-row :gutter="16" class="block-space">
            <el-col v-for="item in summaryCards" :key="item.label" :xs="24" :sm="12" :lg="6">
              <el-card shadow="hover" :class="['metric-card', item.highlight ? 'metric-card--highlight' : '']">
                <div class="metric-label">
                  {{ item.label }}
                  <el-button
                    v-if="item.isGemCard"
                    link
                    size="small"
                    :loading="liveGemLoading"
                    @click.stop="fetchLiveGemBalance"
                    style="margin-left:4px;font-size:12px;"
                    :title="liveGemError || '点击查询游戏账户实时余额'"
                  >{{ liveGemBalance !== null ? '🔄' : '查实时' }}</el-button>
                </div>
                <div class="metric-value" :style="item.isGemCard && liveGemError ? 'color:#f56c6c' : ''">
                  {{ item.isGemCard && liveGemLoading ? '查询中…' : item.value }}
                </div>
                <div class="metric-helper">
                  {{ item.isGemCard && liveGemError ? liveGemError : item.helper }}
                </div>
              </el-card>
            </el-col>
          </el-row>

          <div class="block-space settle-row">
            <el-button
              type="warning"
              plain
              :loading="settlingMonth"
              @click="handleSettleMonth"
            >月度推广结算</el-button>
            <span class="settle-hint">每月末手动触发一次，发放阶梯分红和Top5奖励</span>
          </div>

          <el-row :gutter="16" class="block-space">
            <el-col :xs="24" :lg="10">
              <el-card class="panel-card snapshot-panel" shadow="never">
                <template #header>
                  <div class="panel-head panel-head--stack">
                    <div class="panel-head-copy">
                      <span>{{ snapshotTitle }}</span>
                      <div class="panel-subhead">{{ snapshotRangeText }}</div>
                    </div>
                    <div class="snapshot-toolbar">
                      <div class="snapshot-segment" role="tablist" aria-label="经营快照筛选">
                        <button
                          v-for="option in SNAPSHOT_PRESET_OPTIONS"
                          :key="option.value"
                          type="button"
                          :class="['snapshot-chip', snapshotFilter.mode === option.value ? 'is-active' : '']"
                          @click="handleSnapshotPresetChange(option.value)"
                        >
                          {{ option.label }}
                        </button>
                      </div>
                      <el-date-picker
                        v-if="snapshotFilter.mode === 'custom'"
                        v-model="snapshotFilter.customRange"
                        type="daterange"
                        unlink-panels
                        range-separator="至"
                        start-placeholder="开始日期"
                        end-placeholder="结束日期"
                        value-format="YYYY-MM-DD"
                        class="snapshot-date-picker"
                        @change="handleSnapshotCustomRangeChange"
                      />
                      <el-tag type="primary" effect="plain">{{ snapshotTagText }}</el-tag>
                    </div>
                  </div>
                </template>
                <div class="today-grid">
                  <div v-for="item in snapshotCards" :key="item.label" class="today-item">
                    <div class="today-label">{{ item.label }}</div>
                    <div class="today-value">{{ item.value }}</div>
                    <div class="today-helper">{{ item.helper }}</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="14">
              <el-card class="panel-card" shadow="never">
                <template #header>
                  <div class="panel-head">
                    <span>{{ overviewTrendTitle }}</span>
                    <el-tag effect="plain">{{ snapshotRangeText }}</el-tag>
                  </div>
                </template>
                <el-table :data="overviewTrendRows" border stripe size="small" :empty-text="overviewTrendEmptyText">

                  <el-table-column prop="date" label="日期" min-width="120" />
                  <el-table-column label="充值" min-width="160">
                    <template #default="{ row }">{{ formatNumber(row.rechargeAmount || 0) }} / {{ formatNumber(row.rechargeCount || 0) }} 笔</template>
                  </el-table-column>
                  <el-table-column label="转出" min-width="160">
                    <template #default="{ row }">{{ formatNumber(row.transferAmount || 0) }} / {{ formatNumber(row.transferCount || 0) }} 笔</template>
                  </el-table-column>
                  <el-table-column label="新担保" min-width="120">
                    <template #default="{ row }">{{ formatNumber(row.guaranteeCreatedCount || 0) }}</template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </template>

        <template v-else-if="activeModule === 'user-manage'">
          <UserManagePanel ref="userPanelRef" @count-change="handleUserCountChange" />
        </template>

        <template v-else-if="activeModule === 'promotion-manage'">
          <PromotionManagePanel ref="promotionPanelRef" @count-change="handlePromotionCountChange" />
        </template>

        <template v-else-if="activeModule === 'home-content'">
          <HomeContentManagePanel ref="homeContentPanelRef" @count-change="handleHomeContentCountChange" />
        </template>

        <template v-else-if="activeModule === 'layout-feedback-manage'">
          <LayoutFeedbackManagePanel ref="layoutFeedbackPanelRef" @count-change="handleLayoutFeedbackCountChange" />
        </template>

        <template v-else-if="activeModule === 'pending-withdraw'">
          <el-card class="panel-card" shadow="never">
            <template #header>
              <div class="panel-head panel-head--between">
                <span>用户转出申请列表</span>
                <el-tag type="warning">共 {{ pendingWithdrawPager.total }} 条</el-tag>


              </div>
            </template>
            <div class="toolbar-row">
              <el-input
                v-model="listFilters.pendingWithdraw.query"
                :placeholder="FILTER_PLACEHOLDERS.pendingWithdraw"
                clearable
                class="toolbar-input"
                @keyup.enter="handleManageListSearch('pendingWithdraw')"
              />
              <el-select v-model="listFilters.pendingWithdraw.status" placeholder="全部状态" clearable class="toolbar-select">
                <el-option label="全部状态" value="all" />
                <el-option v-for="option in LIST_STATUS_OPTIONS.pendingWithdraw" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
              <el-button type="primary" plain @click="handleManageListSearch('pendingWithdraw')">查询</el-button>
              <el-button @click="handleManageListReset('pendingWithdraw')">重置</el-button>
            </div>
            <el-table v-loading="loading" :data="pendingWithdrawPager.rows" border stripe empty-text="当前没有符合条件的用户转出申请">


              <el-table-column prop="id" label="申请编号" min-width="160" />
              <el-table-column label="用户" min-width="220">
                <template #default="{ row }">
                  <div>{{ row.userNickName || '方块兽玩家' }}</div>
                  <div class="minor-text">账号：{{ row.account || '未设置账号' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="方块兽" min-width="200">
                <template #default="{ row }">
                  <div>{{ row.beastId || '未绑定' }}</div>
                  <div class="minor-text">昵称：{{ row.beastNick || '—' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="状态" min-width="120">
                <template #default="{ row }">
                  <el-tag :type="toTagType(row.statusClass || row.status)" effect="plain">{{ row.statusText || '待处理' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="申请数量" min-width="150">
                <template #default="{ row }">
                  <div>{{ formatNumber(row.requestAmount ?? row.request_amount ?? 0) }}</div>
                  <div class="minor-text">手续费 {{ formatNumber(row.feeAmount ?? row.fee_amount ?? 0) }}</div>
                </template>
              </el-table-column>
              <el-table-column label="预计实转" min-width="120">
                <template #default="{ row }">{{ formatNumber(row.actualAmount ?? row.actual_amount ?? 0) }}</template>
              </el-table-column>
              <el-table-column prop="createTime" label="提交时间" min-width="160" />
              <el-table-column label="操作" fixed="right" min-width="250">
                <template #default="{ row }">
                  <el-space wrap>
                    <el-button link type="primary" @click="handleInspect('pending-withdraw', row)">详情</el-button>
                    <template v-if="row.status === 'pending'">
                      <el-button size="small" type="success" :loading="actionBusy.withdraw === row.id" @click="handleWithdrawSubmit(row.id)">
                        登记完成
                      </el-button>
                      <el-button size="small" type="danger" plain :loading="actionBusy.withdraw === row.id" @click="handleWithdrawReject(row)">
                        拒绝转出
                      </el-button>
                    </template>
                    <span v-else class="minor-text">已处理</span>
                  </el-space>
                </template>
              </el-table-column>

            </el-table>
            <div class="pagination-row">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next, jumper"
                :total="pendingWithdrawPager.total"
                :current-page="pendingWithdrawPager.currentPage"
                :page-size="pendingWithdrawPager.pageSize"
                :page-sizes="LIST_PAGE_SIZES"
                @current-change="handleManageListPageChange('pendingWithdraw', $event)"
                @size-change="handleManageListPageSizeChange('pendingWithdraw', $event)"
              />
            </div>
          </el-card>
        </template>


        <template v-else-if="activeModule === 'pending-feedback'">

          <el-card class="panel-card" shadow="never">
            <template #header>
              <div class="panel-head panel-head--between">
                <span>待处理反馈列表</span>
                <el-tag type="warning">共 {{ pendingFeedbackPager.total }} 条</el-tag>
              </div>

            </template>
            <div class="toolbar-row">
              <el-input
                v-model="listFilters.pendingFeedback.query"
                :placeholder="FILTER_PLACEHOLDERS.pendingFeedback"
                clearable
                class="toolbar-input"
                @keyup.enter="handleManageListSearch('pendingFeedback')"
              />
              <el-select v-model="listFilters.pendingFeedback.status" placeholder="全部状态" clearable class="toolbar-select">
                <el-option label="全部状态" value="all" />
                <el-option v-for="option in LIST_STATUS_OPTIONS.pendingFeedback" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
              <el-button type="primary" plain @click="handleManageListSearch('pendingFeedback')">查询</el-button>
              <el-button @click="handleManageListReset('pendingFeedback')">重置</el-button>
            </div>
            <el-table v-loading="loading" :data="pendingFeedbackPager.rows" border stripe empty-text="当前没有待处理的反馈">

              <el-table-column label="反馈内容" min-width="320">
                <template #default="{ row }">
                  <div class="primary-text">{{ row.title || '未命名反馈' }}</div>
                  <div class="minor-text">{{ row.content || '暂无描述' }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="type" label="类型" min-width="120" />
              <el-table-column label="用户" min-width="220">
                <template #default="{ row }">
                  <div>{{ row.userNickName || '方块兽玩家' }}</div>
                  <div class="minor-text">{{ row.account || '未设置账号' }} / {{ row.beastId || '未绑定' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="状态" min-width="120">
                <template #default="{ row }">
                  <el-tag :type="toTagType(row.statusClass || row.status)" effect="plain">{{ row.statusText || '待处理' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="time" label="提交时间" min-width="160" />
              <el-table-column label="操作" fixed="right" min-width="280">
                <template #default="{ row }">
                  <el-space wrap>
                    <el-button link type="primary" @click="handleInspect('pending-feedback', row)">详情</el-button>
                    <el-button size="small" type="success" plain :loading="actionBusy.feedback === String(row.id)" @click="handleFeedbackSubmit({ item: row, status: 'adopted' })">采纳</el-button>
                    <el-button size="small" type="primary" plain :loading="actionBusy.feedback === String(row.id)" @click="handleFeedbackSubmit({ item: row, status: 'completed' })">完成</el-button>
                    <el-button size="small" type="danger" plain :loading="actionBusy.feedback === String(row.id)" @click="handleFeedbackSubmit({ item: row, status: 'rejected' })">暂不处理</el-button>
                  </el-space>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-row">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next, jumper"
                :total="pendingFeedbackPager.total"
                :current-page="pendingFeedbackPager.currentPage"
                :page-size="pendingFeedbackPager.pageSize"
                :page-sizes="LIST_PAGE_SIZES"
                @current-change="handleManageListPageChange('pendingFeedback', $event)"
                @size-change="handleManageListPageSizeChange('pendingFeedback', $event)"
              />
            </div>
          </el-card>

        </template>


        <template v-else-if="activeModule === 'recharge'">
          <el-card class="panel-card" shadow="never">
            <template #header>
              <div class="panel-head panel-head--between">
                <span>充值记录</span>
                <el-tag effect="plain">共 {{ rechargePager.total }} 条</el-tag>
              </div>
            </template>
            <div class="toolbar-row">
              <el-input
                v-model="listFilters.recharge.query"
                :placeholder="FILTER_PLACEHOLDERS.recharge"
                clearable
                class="toolbar-input"
                @keyup.enter="handleManageListSearch('recharge')"
              />
              <el-select v-model="listFilters.recharge.status" placeholder="全部状态" clearable class="toolbar-select">
                <el-option label="全部状态" value="all" />
                <el-option v-for="option in LIST_STATUS_OPTIONS.recharge" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
              <el-button type="primary" plain @click="handleManageListSearch('recharge')">查询</el-button>
              <el-button @click="handleManageListReset('recharge')">重置</el-button>
            </div>
            <el-table v-loading="loading" :data="rechargePager.rows" border stripe empty-text="暂无充值记录">

              <el-table-column prop="id" label="订单号" min-width="180" />
              <el-table-column label="用户" min-width="220">
                <template #default="{ row }">
                  <div>{{ row.userNickName || '方块兽玩家' }}</div>
                  <div class="minor-text">{{ row.account || '未设置账号' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="方块兽 / 校验码" min-width="220">
                <template #default="{ row }">
                  <div>{{ row.beastId || '未绑定' }}</div>
                  <div class="minor-text">{{ row.verifyCode || '无校验码' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="充值数量" min-width="120">
                <template #default="{ row }">+{{ formatNumber(row.amount || 0) }}</template>
              </el-table-column>
              <el-table-column label="状态" min-width="120">
                <template #default="{ row }">
                  <el-tag :type="toTagType(row.statusClass || row.status)" effect="plain">{{ row.statusText || '未知状态' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="时间" min-width="180">
                <template #default="{ row }">
                  <div>{{ row.time || '—' }}</div>
                  <div class="minor-text">到账：{{ row.verifiedTime || row.matchedTime || '—' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="操作" fixed="right" min-width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="handleInspect('recharge', row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-row">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next, jumper"
                :total="rechargePager.total"
                :current-page="rechargePager.currentPage"
                :page-size="rechargePager.pageSize"
                :page-sizes="LIST_PAGE_SIZES"
                @current-change="handleManageListPageChange('recharge', $event)"
                @size-change="handleManageListPageSizeChange('recharge', $event)"

              />
            </div>
          </el-card>
        </template>

        <template v-else-if="activeModule === 'guarantee'">
          <el-card class="panel-card" shadow="never">
            <template #header>
              <div class="panel-head panel-head--between">
                <span>担保管理</span>
                <el-tag effect="plain">共 {{ guaranteePager.total }} 条</el-tag>
              </div>
            </template>
            <div class="toolbar-row">
              <el-input
                v-model="listFilters.guarantee.query"
                :placeholder="FILTER_PLACEHOLDERS.guarantee"
                clearable
                class="toolbar-input"
                @keyup.enter="handleManageListSearch('guarantee')"
              />
              <el-select v-model="listFilters.guarantee.status" placeholder="全部状态" clearable class="toolbar-select">
                <el-option label="全部状态" value="all" />
                <el-option v-for="option in LIST_STATUS_OPTIONS.guarantee" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
              <el-button type="primary" plain @click="handleManageListSearch('guarantee')">查询</el-button>
              <el-button @click="handleManageListReset('guarantee')">重置</el-button>
            </div>

            <el-table v-loading="loading" :data="guaranteePager.rows" border stripe empty-text="暂无担保档案">
              <el-table-column label="保单信息" min-width="220">
                <template #default="{ row }">
                  <div class="primary-text">{{ row.id || row.orderNo }}</div>
                  <div class="minor-text">{{ row.petName || row.pet_name || '未填写兽王' }} · {{ formatNumber(row.tradeQuantity ?? row.trade_quantity ?? 1) }} 只</div>
                </template>
              </el-table-column>
              <el-table-column label="卖家 / 买家" min-width="260">
                <template #default="{ row }">
                  <div>卖家：{{ row.sellerNickName || '未设置' }}</div>
                  <div class="minor-text">买家：{{ row.buyerBeastNick || row.buyer_beast_nick || '未填写' }} / {{ row.buyerBeastId || row.buyer_beast_id || '未填写' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="金额" min-width="180">
                <template #default="{ row }">
                  <div>标价 {{ formatNumber(row.gemAmount ?? row.gem_amount ?? 0) }} 宝石</div>
                  <div class="minor-text">卖家实扣 {{ formatNumber(row.sellerTotalCost ?? row.seller_total_cost ?? ((row.gemAmount ?? row.gem_amount ?? 0) + (row.feeAmount ?? row.fee_amount ?? 0))) }} / 买家实收 {{ formatNumber(row.actualReceive ?? row.actual_receive ?? 0) }}</div>
                </template>

              </el-table-column>

              <el-table-column label="截图" min-width="120">
                <template #default="{ row }">
                  <el-tag :type="(row.buyerProofImage || row.buyer_proof_image) ? 'success' : 'info'" effect="plain">
                    {{ (row.buyerProofImage || row.buyer_proof_image) ? '已上传' : '未上传' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" min-width="120">
                <template #default="{ row }">
                  <el-tag :type="toTagType(row.statusClass || row.status)" effect="plain">{{ row.statusText || '未知状态' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="完成时间" min-width="180">
                <template #default="{ row }">{{ row.finishedTime || row.finished_time || '—' }}</template>
              </el-table-column>
              <el-table-column label="操作" fixed="right" min-width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="handleInspect('guarantee', row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-row">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next, jumper"
                :total="guaranteePager.total"
                :current-page="guaranteePager.currentPage"
                :page-size="guaranteePager.pageSize"
                :page-sizes="LIST_PAGE_SIZES"
                @current-change="handleManageListPageChange('guarantee', $event)"
                @size-change="handleManageListPageSizeChange('guarantee', $event)"

              />
            </div>
          </el-card>
        </template>

        <template v-else-if="activeModule === 'feedback'">
          <el-card class="panel-card" shadow="never">
            <template #header>
              <div class="panel-head panel-head--between">
                <span>反馈档案</span>
                <el-tag effect="plain">共 {{ feedbackPager.total }} 条</el-tag>
              </div>
            </template>
            <div class="toolbar-row">
              <el-input
                v-model="listFilters.feedback.query"
                :placeholder="FILTER_PLACEHOLDERS.feedback"
                clearable
                class="toolbar-input"
                @keyup.enter="handleManageListSearch('feedback')"
              />
              <el-select v-model="listFilters.feedback.status" placeholder="全部状态" clearable class="toolbar-select">
                <el-option label="全部状态" value="all" />
                <el-option v-for="option in LIST_STATUS_OPTIONS.feedback" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
              <el-button type="primary" plain @click="handleManageListSearch('feedback')">查询</el-button>
              <el-button @click="handleManageListReset('feedback')">重置</el-button>
            </div>

            <el-table v-loading="loading" :data="feedbackPager.rows" border stripe empty-text="暂无反馈档案">
              <el-table-column label="反馈内容" min-width="320">
                <template #default="{ row }">
                  <div class="primary-text">{{ row.title || '未命名反馈' }}</div>
                  <div class="minor-text">{{ row.content || '暂无描述' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="用户" min-width="220">
                <template #default="{ row }">
                  <div>{{ row.userNickName || '方块兽玩家' }}</div>
                  <div class="minor-text">{{ row.account || '未设置账号' }} / {{ row.beastId || '未绑定' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="状态" min-width="120">
                <template #default="{ row }">
                  <el-tag :type="toTagType(row.statusClass || row.status)" effect="plain">{{ row.statusText || '待处理' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="处理说明" min-width="220">
                <template #default="{ row }">{{ row.adminReply || '暂无处理说明' }}</template>
              </el-table-column>
              <el-table-column label="时间" min-width="180">
                <template #default="{ row }">
                  <div>提交：{{ row.time || '—' }}</div>
                  <div class="minor-text">处理：{{ row.handledTime || '未处理' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="操作" fixed="right" min-width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="handleInspect('feedback', row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-row">
              <el-pagination
                background
                layout="total, sizes, prev, pager, next, jumper"
                :total="feedbackPager.total"
                :current-page="feedbackPager.currentPage"
                :page-size="feedbackPager.pageSize"
                :page-sizes="LIST_PAGE_SIZES"
                @current-change="handleManageListPageChange('feedback', $event)"
                @size-change="handleManageListPageSizeChange('feedback', $event)"

              />
            </div>
          </el-card>
        </template>

        <template v-else-if="activeModule === 'token-manage'">
          <TokenManagePanel ref="tokenPanelRef" @count-change="handleTokenCountChange" />
        </template>

        <template v-else-if="activeModule === 'community-apply-manage'">
          <CommunityApplyManagePanel ref="communityApplyPanelRef" @count-change="handleCommunityApplyCountChange" />
        </template>


        <template v-else-if="activeModule === 'community-manage'">
          <CommunityManagePanel />
        </template>


        <template v-else-if="activeModule === 'daily'">
          <el-card class="panel-card" shadow="never">
            <template #header>
              <div class="panel-head panel-head--between">
                <span>{{ overviewTrendTitle }}</span>
                <el-tag effect="plain">共 {{ filteredDailyRows.length }} / {{ dashboard.dailyFlow.length }} 天数据</el-tag>
              </div>
            </template>
            <div class="toolbar-row">
              <el-input
                v-model="listFilters.daily.query"
                :placeholder="FILTER_PLACEHOLDERS.daily"
                clearable
                class="toolbar-input"
              />

              <el-button v-if="hasActiveFilters('daily')" @click="resetListFilters('daily')">清空筛选</el-button>
            </div>
            <el-table v-loading="loading" :data="filteredDailyRows" border stripe :empty-text="overviewTrendEmptyText">

              <el-table-column prop="date" label="日期" min-width="120" />
              <el-table-column label="充值金额" min-width="140">
                <template #default="{ row }">{{ formatNumber(row.rechargeAmount || 0) }}</template>
              </el-table-column>
              <el-table-column label="充值笔数" min-width="120">
                <template #default="{ row }">{{ formatNumber(row.rechargeCount || 0) }}</template>
              </el-table-column>
              <el-table-column label="转出金额" min-width="140">
                <template #default="{ row }">{{ formatNumber(row.transferAmount || 0) }}</template>
              </el-table-column>
              <el-table-column label="转出笔数" min-width="120">
                <template #default="{ row }">{{ formatNumber(row.transferCount || 0) }}</template>
              </el-table-column>
              <el-table-column label="新担保" min-width="120">
                <template #default="{ row }">{{ formatNumber(row.guaranteeCreatedCount || 0) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </template>

      </el-main>
    </el-container>

    <el-drawer v-model="drawerVisible" size="560px" :title="drawerDetail.title || '查看详情'" destroy-on-close>
      <div class="drawer-kicker">{{ drawerDetail.eyebrow || 'DETAIL' }}</div>
      <div v-if="drawerDetail.subtitle" class="drawer-subtitle">{{ drawerDetail.subtitle }}</div>
      <div class="drawer-status-row">
        <el-tag v-if="drawerDetail.statusLabel" :type="toTagType(drawerDetail.statusTone)" effect="plain">{{ drawerDetail.statusLabel }}</el-tag>
      </div>
      <el-alert v-if="drawerDetail.description" :title="drawerDetail.description" type="info" show-icon :closable="false" class="drawer-alert" />

      <div v-if="drawerDetail.highlights?.length" class="drawer-highlight-grid">
        <el-card v-for="item in drawerDetail.highlights" :key="item.label" shadow="never">
          <div class="mini-card-label">{{ item.label }}</div>
          <div class="mini-card-value">{{ item.value }}</div>
        </el-card>
      </div>

      <el-descriptions v-if="drawerDetail.rows?.length" :column="1" border class="drawer-descriptions">
        <el-descriptions-item v-for="row in drawerDetail.rows" :key="row.label">
          <template #label>{{ row.label }}</template>
          <div class="desc-value-row">
            <span>{{ row.value }}</span>
            <el-button v-if="row.copyValue" link type="primary" @click="copyText({ label: row.label, value: row.copyValue })">复制</el-button>
          </div>
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="drawerDetail.imageUrl" class="drawer-image-box">
        <div class="drawer-image-head">
          <span>{{ drawerDetail.imageLabel || '截图凭证' }}</span>
          <el-button link type="primary" @click="copyText({ label: '截图链接', value: drawerDetail.imageUrl })">复制链接</el-button>
        </div>
        <el-image :src="drawerDetail.imageUrl" :preview-src-list="[drawerDetail.imageUrl]" fit="cover" class="proof-image" />
      </div>

      <el-card v-if="drawerDetail.notes?.length" shadow="never" class="drawer-note-card">
        <template #header>运营备注</template>
        <ul class="note-list">
          <li v-for="note in drawerDetail.notes" :key="note">{{ note }}</li>
        </ul>
      </el-card>
    </el-drawer>
  </el-container>
</template>

<style scoped>
.admin-layout {
  min-height: 100vh;
  background: #f0f2f5;
}

.admin-aside {
  display: flex;
  flex-direction: column;
  padding: 12px 10px;
  background: #304156;
  color: #bfcbd9;
}

.brand-panel {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 14px;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
}

.brand-copy {
  min-width: 0;
}

.brand-title {
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
}

.brand-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #8fa1b7;
}

.nav-section-title {
  padding: 0 10px 8px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #8fa1b7;
}

.side-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}

.side-menu :deep(.el-menu-item) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 42px;
  margin-bottom: 4px;
  padding: 0 10px !important;
  border-radius: 8px;
  color: #bfcbd9;
  font-size: 14px;
}

.side-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: #263445;
  color: #409eff;
}

.menu-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.menu-icon {
  font-size: 14px;
  flex: 0 0 auto;
}

.menu-count {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 8px;
  width: 22px;
  height: 18px;
  padding: 0;
  font-size: 11px;
  line-height: 1;
  border-radius: 999px;
  background: #f56c6c;
  color: #ffffff;
  font-weight: 600;
}

.aside-footer {
  margin-top: 6px;
  padding: 12px 8px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.logout-btn {
  width: 100%;
  margin-top: 8px;
}

.admin-header {
  height: auto;
  padding: 16px 20px 0;
}

.page-toolbar {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #ffffff;
}

.page-main {
  min-width: 0;
}

.page-breadcrumb {
  font-size: 13px;
  color: #909399;
}

.page-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.page-desc {
  margin-top: 8px;
  color: #606266;
  line-height: 1.6;
}

.page-stats {
  display: flex;
  align-items: stretch;
  gap: 12px;
}

.page-stat {
  min-width: 150px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  background: #f8fafc;
}

.page-stat-label {
  font-size: 12px;
  color: #909399;
}

.page-stat-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.page-stat-text {
  margin-top: 8px;
  color: #303133;
  line-height: 1.6;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-main {
  padding: 16px 20px 24px;
}

.block-space {
  margin-bottom: 16px;
}

.metric-card--highlight {
  border-color: #409eff;
  background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%);
}

.settle-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.settle-hint {
  font-size: 13px;
  color: #909399;
}

.metric-card,
.panel-card {
  border-radius: 12px;
}

.metric-label,
.today-label,
.mini-card-label {
  font-size: 13px;
  color: #909399;
}

.metric-value,
.today-value,
.mini-card-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.metric-helper,
.today-helper,
.minor-text,
.drawer-subtitle {
  margin-top: 6px;
  color: #909399;
  line-height: 1.6;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #303133;
  font-weight: 600;
}

.panel-head--between {
  justify-content: space-between;
}

.panel-head--stack {
  align-items: flex-start;
  gap: 16px;
}

.panel-head-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel-subhead {
  font-size: 12px;
  font-weight: 400;
  color: #8c97ab;
}

.snapshot-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.snapshot-segment {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: linear-gradient(135deg, #f4f7ff 0%, #eef3fb 100%);
  border: 1px solid #dbe5f2;
}

.snapshot-chip {
  border: none;
  background: transparent;
  color: #5f6b7c;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  padding: 9px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.snapshot-chip:hover {
  color: #1f2a37;
  background: rgba(64, 158, 255, 0.08);
}

.snapshot-chip.is-active {
  color: #ffffff;
  background: linear-gradient(135deg, #409eff 0%, #5b8cff 100%);
  box-shadow: 0 10px 24px rgba(64, 158, 255, 0.24);
}

.snapshot-date-picker {
  width: 270px;
}

.today-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.today-item {
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(180deg, #fbfdff 0%, #f3f7fc 100%);
  border: 1px solid #e6edf7;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}


.toolbar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafafa;
}

.toolbar-input {
  width: 320px;
}

.toolbar-select {
  width: 180px;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.primary-text {
  font-weight: 600;
  color: #303133;
}

.drawer-kicker {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #909399;
}

.drawer-status-row {
  margin-top: 12px;
}

.drawer-alert {
  margin-top: 16px;
}

.drawer-highlight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.drawer-descriptions {
  margin-top: 16px;
}

.desc-value-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.drawer-image-box {
  margin-top: 16px;
}

.drawer-image-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  color: #303133;
}

.proof-image {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #ebeef5;
}

.drawer-note-card {
  margin-top: 16px;
}

.note-list {
  margin: 0;
  padding-left: 18px;
  color: #606266;
  line-height: 1.8;
}

@media (max-width: 1400px) {
  .page-toolbar {
    flex-direction: column;
  }

  .page-stats {
    flex-wrap: wrap;
  }
}

@media (max-width: 1200px) {
  .admin-layout {
    flex-direction: column;
  }

  .admin-aside {
    width: 100% !important;
  }
}

@media (max-width: 768px) {
  .admin-header,
  .admin-main {
    padding-left: 12px;
    padding-right: 12px;
  }

  .page-stats,
  .today-grid,
  .drawer-highlight-grid {
    grid-template-columns: 1fr;
  }

  .panel-head--stack,
  .snapshot-toolbar {
    width: 100%;
  }

  .snapshot-toolbar {
    justify-content: flex-start;
  }

  .snapshot-segment {
    flex-wrap: wrap;
  }

  .snapshot-date-picker,
  .toolbar-input,
  .toolbar-select {
    width: 100%;
  }
}

</style>
