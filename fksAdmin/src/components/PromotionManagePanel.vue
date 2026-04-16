<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'
import { formatNumber } from '../utils/format'

const emit = defineEmits(['count-change'])

function createEmptyPayload() {
  return {
    summary: {
      totalInviters: 0,
      totalInvitees: 0,
      effectiveInvitees: 0,
      pendingInvitees: 0,
      rewardCount: 0,
      totalRewardAmount: 0,
      recentEffectiveCount: 0,
      conversionRate: 0,
    },
    rules: [],
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 1,
    },
    list: [],
    rewardList: [],
    inviteeList: [],
  }
}

const loading = ref(false)
const payload = ref(createEmptyPayload())
const filters = reactive({
  query: '',
  status: 'all',
  page: 1,
  pageSize: 20,
})

const summaryCards = computed(() => [
  {
    label: '推广员',
    value: formatNumber(payload.value.summary.totalInviters),
    helper: `有邀请记录的账户`,
    tone: 'primary',
  },
  {
    label: '总邀请人数',
    value: formatNumber(payload.value.summary.totalInvitees),
    helper: `待转化 ${formatNumber(payload.value.summary.pendingInvitees)}`,
    tone: 'indigo',
  },
  {
    label: '有效推广',
    value: formatNumber(payload.value.summary.effectiveInvitees),
    helper: `近 7 天新增 ${formatNumber(payload.value.summary.recentEffectiveCount)}`,
    tone: 'success',
  },
  {
    label: '奖励发放',
    value: formatNumber(payload.value.summary.totalRewardAmount),
    helper: `${formatNumber(payload.value.summary.rewardCount)} 条奖励日志`,
    tone: 'violet',
  },
  {
    label: '转化率',
    value: `${Number(payload.value.summary.conversionRate || 0).toFixed(1)}%`,
    helper: '按已绑定邀请用户计算',
    tone: 'amber',
  },
])

watch(
  () => payload.value.pagination.total,
  (total) => emit('count-change', Number(total || 0)),
  { immediate: true },
)

function tagType(statusClass = '') {
  if (statusClass === 'success') return 'success'
  if (statusClass === 'danger') return 'danger'
  if (statusClass === 'warning') return 'warning'
  if (statusClass === 'info') return 'primary'
  return 'info'
}

function buildPromotionUrl() {
  const params = new URLSearchParams({
    page: String(filters.page || 1),
    page_size: String(filters.pageSize || 20),
    reward_limit: '20',
    invitee_limit: '24',
  })
  if (filters.query.trim()) {
    params.set('query', filters.query.trim())
  }
  if (filters.status && filters.status !== 'all') {
    params.set('status', filters.status)
  }
  return `/api/manage/promotions?${params.toString()}`
}

async function loadPromotions({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const data = await api.get(buildPromotionUrl())
    payload.value = {
      ...createEmptyPayload(),
      ...data,
    }
  } catch (error) {
    ElMessage.error(error.message || '读取推广管理数据失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  filters.page = 1
  loadPromotions()
}

function handleReset() {
  filters.query = ''
  filters.status = 'all'
  filters.page = 1
  filters.pageSize = 20
  loadPromotions()
}

function handlePageChange(page) {
  filters.page = Number(page || 1)
  loadPromotions({ silent: true })
}

function handleSizeChange(size) {
  filters.pageSize = Number(size || 20)
  filters.page = 1
  loadPromotions({ silent: true })
}

defineExpose({
  reload: loadPromotions,
})

onMounted(() => {
  loadPromotions()
})
</script>

<template>
  <div class="promotion-shell">
    <el-row :gutter="16" class="summary-row">
      <el-col v-for="item in summaryCards" :key="item.label" :xs="24" :sm="12" :lg="8" :xl="4.8">
        <el-card shadow="never" class="summary-card" :class="`is-${item.tone}`">
          <div class="summary-label">{{ item.label }}</div>
          <div class="summary-value">{{ item.value }}</div>
          <div class="summary-helper">{{ item.helper }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-head">
          <div>
            <div class="panel-eyebrow">PROMOTION OPS</div>
            <div class="panel-title">推广管理</div>
            <div class="panel-desc">复用 `users.invite_code / invited_by_user_id / promotion_effective_at` 与 `promotion_reward_logs`，集中看邀请转化、奖励发放和推广员表现。</div>
          </div>
          <div class="panel-actions">
            <el-button @click="loadPromotions({ silent: true })">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="rule-strip">
        <div v-for="rule in payload.rules" :key="rule.threshold" class="rule-chip">
          <div class="rule-threshold">{{ rule.threshold }} 人</div>
          <div class="rule-reward">奖励 {{ formatNumber(rule.reward) }} 宝石</div>
          <div class="rule-label">{{ rule.label }}</div>
        </div>
      </div>

      <div class="toolbar-row">
        <el-input
          v-model="filters.query"
          class="toolbar-input"
          clearable
          placeholder="搜索推广员 / 受邀用户 / 方块兽 ID / 推荐码"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="filters.status" class="toolbar-select" placeholder="全部状态">
          <el-option label="全部状态" value="all" />
          <el-option label="有邀请" value="invited" />
          <el-option label="已生效" value="effective" />
          <el-option label="已奖励" value="rewarded" />
          <el-option label="待转化" value="pending" />
        </el-select>
        <el-button type="primary" plain @click="handleSearch">筛选</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="payload.list" border stripe empty-text="暂无推广员数据">
        <el-table-column label="推广员" min-width="220">
          <template #default="{ row }">
            <div class="primary-text">{{ row.nickName || '方块兽玩家' }}</div>
            <div class="minor-text">账号：{{ row.account || '未设置账号' }}</div>
            <div class="minor-text">方块兽：{{ row.beastId || '未绑定' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="推荐码" min-width="150">
          <template #default="{ row }">
            <div class="code-text">{{ row.inviteCode || '未生成' }}</div>
            <div class="minor-text">创建：{{ row.createdTime || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="邀请转化" min-width="220">
          <template #default="{ row }">
            <div>总邀请 {{ formatNumber(row.invitedCount || 0) }}</div>
            <div class="minor-text">有效 {{ formatNumber(row.effectiveInviteCount || 0) }} / 待转化 {{ formatNumber(row.pendingInviteCount || 0) }}</div>
            <div class="minor-text">转化率 {{ Number(row.effectiveRate || 0).toFixed(1) }}%</div>
          </template>
        </el-table-column>
        <el-table-column label="奖励表现" min-width="200">
          <template #default="{ row }">
            <div>奖励 {{ formatNumber(row.totalRewardAmount || 0) }} 宝石</div>
            <div class="minor-text">日志 {{ formatNumber(row.rewardCount || 0) }} 条</div>
            <div class="minor-text">最近奖励：{{ row.latestRewardTime || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="最近动态" min-width="170">
          <template #default="{ row }">
            <div>最近邀请：{{ row.latestInvitedTime || '—' }}</div>
            <div class="minor-text">状态：{{ row.statusText || '未开始' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag :type="tagType(row.statusClass)" effect="plain">{{ row.statusText || '未开始' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="payload.pagination.total || 0"
          :current-page="filters.page"
          :page-size="filters.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :xl="12">
        <el-card class="panel-card sub-card" shadow="never">
          <template #header>
            <div class="sub-head">
              <div>
                <div class="panel-eyebrow">REWARD LOGS</div>
                <div class="sub-title">近期奖励记录</div>
              </div>
              <el-tag effect="plain">{{ payload.rewardList.length }} 条</el-tag>
            </div>
          </template>
          <el-table :data="payload.rewardList" border stripe size="small" empty-text="暂无奖励记录">
            <el-table-column label="推广员" min-width="160">
              <template #default="{ row }">
                <div>{{ row.nickName || '方块兽玩家' }}</div>
                <div class="minor-text">{{ row.inviteCode || '—' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="受邀用户" min-width="150">
              <template #default="{ row }">
                <div>{{ row.inviteeNickName || '—' }}</div>
                <div class="minor-text">{{ row.inviteeBeastId || '未绑定' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="奖励" min-width="160">
              <template #default="{ row }">
                <div>{{ formatNumber(row.rewardAmount || 0) }} 宝石</div>
                <div class="minor-text">阈值 {{ formatNumber(row.triggerThreshold || 0) }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="createdTime" label="时间" min-width="150" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :xl="12">
        <el-card class="panel-card sub-card" shadow="never">
          <template #header>
            <div class="sub-head">
              <div>
                <div class="panel-eyebrow">INVITEE FLOW</div>
                <div class="sub-title">近期受邀用户</div>
              </div>
              <el-tag effect="plain">{{ payload.inviteeList.length }} 条</el-tag>
            </div>
          </template>
          <el-table :data="payload.inviteeList" border stripe size="small" empty-text="暂无受邀用户数据">
            <el-table-column label="受邀用户" min-width="170">
              <template #default="{ row }">
                <div>{{ row.nickName || '方块兽玩家' }}</div>
                <div class="minor-text">{{ row.account || '未设置账号' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="邀请来源" min-width="160">
              <template #default="{ row }">
                <div>{{ row.inviterNickName || '—' }}</div>
                <div class="minor-text">{{ row.inviterInviteCode || '—' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="转化状态" min-width="150">
              <template #default="{ row }">
                <el-tag :type="tagType(row.statusClass)" effect="plain">{{ row.statusText || '待转化' }}</el-tag>
                <div class="minor-text">{{ row.promotionEffectiveAt || row.invitedAt || '—' }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="invitedAt" label="绑定时间" min-width="150" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.promotion-shell {
  display: grid;
  gap: 16px;
}

.summary-card {
  overflow: hidden;
  position: relative;
  min-height: 128px;
  background: linear-gradient(180deg, #ffffff 0%, #faf8ff 100%);
}

.summary-card::after {
  content: '';
  position: absolute;
  inset: auto -28px -48px auto;
  width: 128px;
  height: 128px;
  border-radius: 999px;
  background: rgba(91, 110, 245, 0.08);
}

.summary-card.is-success::after { background: rgba(52, 211, 153, 0.1); }
.summary-card.is-indigo::after { background: rgba(99, 102, 241, 0.1); }
.summary-card.is-violet::after { background: rgba(139, 92, 246, 0.12); }
.summary-card.is-amber::after { background: rgba(251, 191, 36, 0.12); }

.summary-label {
  position: relative;
  z-index: 1;
  font-size: 13px;
  color: #909399;
}

.summary-value {
  position: relative;
  z-index: 1;
  margin-top: 14px;
  font-size: 32px;
  font-weight: 700;
  color: #1f2a37;
}

.summary-helper {
  position: relative;
  z-index: 1;
  margin-top: 8px;
  color: #6b7280;
  line-height: 1.7;
}

.panel-card {
  border-radius: 16px;
}

.panel-head,
.sub-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.panel-eyebrow {
  font-size: 12px;
  letter-spacing: 0.16em;
  color: #94a3b8;
}

.panel-title {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  color: #111827;
}

.sub-title {
  margin-top: 8px;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.panel-desc {
  margin-top: 8px;
  max-width: 760px;
  color: #6b7280;
  line-height: 1.7;
}

.panel-actions {
  display: flex;
  gap: 10px;
}

.rule-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.rule-chip {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid #eceff6;
  background: linear-gradient(135deg, #faf8ff 0%, #ffffff 100%);
}

.rule-threshold {
  font-size: 20px;
  font-weight: 700;
  color: #5b6ef5;
}

.rule-reward {
  margin-top: 8px;
  font-weight: 600;
  color: #8b5cf6;
}

.rule-label {
  margin-top: 6px;
  color: #6b7280;
  line-height: 1.6;
}

.toolbar-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  border: 1px solid #edf2f7;
}

.toolbar-input {
  width: 360px;
}

.toolbar-select {
  width: 170px;
}

.primary-text {
  font-weight: 600;
  color: #1f2937;
}

.minor-text {
  margin-top: 4px;
  color: #6b7280;
  line-height: 1.55;
}

.code-text {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 14px;
  font-weight: 700;
  color: #5b6ef5;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.sub-card {
  height: 100%;
}

@media (max-width: 960px) {
  .panel-head,
  .sub-head {
    flex-direction: column;
  }

  .toolbar-input,
  .toolbar-select {
    width: 100%;
  }
}
</style>
