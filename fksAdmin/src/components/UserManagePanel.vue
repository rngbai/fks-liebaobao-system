<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../lib/api'
import { formatNumber } from '../utils/format'

const emit = defineEmits(['count-change'])

function createEmptyPayload() {
  return {
    summary: {
      totalUsers: 0,
      activeUsers: 0,
      boundBeastUsers: 0,
      recentNewUsers: 0,
      totalBalance: 0,
      totalLockedGems: 0,
      totalRecharged: 0,
      totalSpent: 0,
      totalEarned: 0,
    },
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 1,
    },
    list: [],
  }
}

function createEmptyDetail() {
  return {
    id: 0,
    nickName: '',
    account: '',
    beastId: '',
    phone: '',
    email: '',
    userKey: '',
    sourceText: '',
    inviteCode: '',
    invitedByNickName: '',
    invitedByInviteCode: '',
    invitedAt: '',
    promotionEffectiveAt: '',
    createdTime: '',
    updatedTime: '',
    wallet: {},
    stats: {},
    statusText: '',
    statusClass: 'info',
  }
}

const loading = ref(false)
const importSubmitting = ref(false)
const detailVisible = ref(false)
const importVisible = ref(false)
const payload = ref(createEmptyPayload())
const detail = ref(createEmptyDetail())
const filters = reactive({
  query: '',
  status: 'all',
  page: 1,
  pageSize: 20,
})
const importForm = reactive({
  text: '',
})

const rows = computed(() => payload.value.list || [])
const summaryCards = computed(() => [
  {
    label: '总用户',
    value: formatNumber(payload.value.summary.totalUsers),
    helper: `近 7 天新增 ${formatNumber(payload.value.summary.recentNewUsers)}`,
    tone: 'primary',
  },
  {
    label: '正常账户',
    value: formatNumber(payload.value.summary.activeUsers),
    helper: `绑定方块兽 ${formatNumber(payload.value.summary.boundBeastUsers)}`,
    tone: 'success',
  },
  {
    label: '钱包总量',
    value: formatNumber(payload.value.summary.totalBalance),
    helper: `锁定 ${formatNumber(payload.value.summary.totalLockedGems)}`,
    tone: 'indigo',
  },
  {
    label: '累计转入',
    value: formatNumber(payload.value.summary.totalRecharged),
    helper: `累计转出 ${formatNumber(payload.value.summary.totalSpent)}`,
    tone: 'amber',
  },
  {
    label: '累计获益',
    value: formatNumber(payload.value.summary.totalEarned),
    helper: '已含担保与推广奖励',
    tone: 'violet',
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
  return 'info'
}

function buildUserUrl() {
  const params = new URLSearchParams({
    page: String(filters.page || 1),
    page_size: String(filters.pageSize || 20),
  })
  if (filters.query.trim()) {
    params.set('query', filters.query.trim())
  }
  if (filters.status && filters.status !== 'all') {
    params.set('status', filters.status)
  }
  return `/api/manage/users?${params.toString()}`
}

async function loadUsers({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const data = await api.get(buildUserUrl())
    payload.value = {
      ...createEmptyPayload(),
      ...data,
    }
  } catch (error) {
    ElMessage.error(error.message || '读取用户管理数据失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  filters.page = 1
  loadUsers()
}

function handleReset() {
  filters.query = ''
  filters.status = 'all'
  filters.page = 1
  filters.pageSize = 20
  loadUsers()
}

function handlePageChange(page) {
  filters.page = Number(page || 1)
  loadUsers({ silent: true })
}

function handleSizeChange(size) {
  filters.pageSize = Number(size || 20)
  filters.page = 1
  loadUsers({ silent: true })
}

function openDetail(row = {}) {
  detail.value = {
    ...createEmptyDetail(),
    ...row,
    wallet: row.wallet || {},
    stats: row.stats || {},
  }
  detailVisible.value = true
}

function openImportDialog() {
  importVisible.value = true
}

async function submitImport() {
  const text = String(importForm.text || '').trim()
  if (!text) {
    ElMessage.warning('请先粘贴要导入的用户内容')
    return
  }
  importSubmitting.value = true
  try {
    const data = await api.post('/api/manage/users/import', { text })
    const result = data.result || {}
    const latest = data.latest || {}
    payload.value = {
      ...createEmptyPayload(),
      ...latest,
    }
    const summaryText = `新增 ${formatNumber(result.createdCount || 0)}，更新 ${formatNumber(result.updatedCount || 0)}，跳过 ${formatNumber(result.skippedCount || 0)}`
    ElMessage.success(`导入完成：${summaryText}`)
    if (Number(result.errorCount || 0) > 0) {
      ElMessage.warning(`另有 ${formatNumber(result.errorCount || 0)} 行失败，请检查导入格式`)
    } else {
      importVisible.value = false
      importForm.text = ''
    }
  } catch (error) {
    ElMessage.error(error.message || '导入用户失败')
  } finally {
    importSubmitting.value = false
  }
}

const actionBusy = ref('')

async function handleBanUser(row) {
  const isBanned = row.status === 0
  const action = isBanned ? '恢复正常' : '拉黑'
  try {
    await ElMessageBox.confirm(
      isBanned
        ? `确认恢复「${row.nickName || '该用户'}」为正常状态？`
        : `确认拉黑「${row.nickName || '该用户'}」？拉黑后该账户将无法正常使用。`,
      `${action}用户`,
      { type: 'warning', confirmButtonText: `确认${action}`, cancelButtonText: '取消' }
    )
  } catch { return }

  actionBusy.value = String(row.id)
  try {
    await api.post('/api/manage/users/ban', { user_id: row.id, status: isBanned ? 1 : 0 })
    ElMessage.success(`用户已${action}`)
    await loadUsers({ silent: true })
  } catch (error) {
    ElMessage.error(error.message || `${action}失败`)
  } finally {
    actionBusy.value = ''
  }
}

async function handleDeleteUser(row) {
  try {
    await ElMessageBox.confirm(
      `确认永久删除「${row.nickName || '该用户'}」？此操作不可恢复，该用户的所有数据（钱包、订单、反馈）将被一并清除。`,
      '删除用户',
      { type: 'error', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch { return }

  try {
    await ElMessageBox.confirm(
      '请再次确认：删除后数据无法恢复！',
      '二次确认',
      { type: 'error', confirmButtonText: '我确定要删除', cancelButtonText: '取消' }
    )
  } catch { return }

  actionBusy.value = String(row.id)
  try {
    await api.post('/api/manage/users/delete', { user_id: row.id })
    ElMessage.success('用户已删除')
    await loadUsers({ silent: true })
  } catch (error) {
    ElMessage.error(error.message || '删除失败')
  } finally {
    actionBusy.value = ''
  }
}

defineExpose({
  reload: loadUsers,
})

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <div class="user-manage-shell">
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
            <div class="panel-eyebrow">USER OPERATIONS</div>
            <div class="panel-title">用户管理</div>
            <div class="panel-desc">按账户、方块兽 ID、推荐码和钱包数据聚合查看用户，支持后台批量导入资料。</div>
          </div>
          <div class="panel-actions">
            <el-button @click="loadUsers({ silent: true })">刷新</el-button>
            <el-button type="primary" @click="openImportDialog">导入用户</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar-row">
        <el-input
          v-model="filters.query"
          class="toolbar-input"
          clearable
          placeholder="搜索昵称 / 账号 / 方块兽 ID / 推荐码 / 手机 / 邮箱"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="filters.status" class="toolbar-select" placeholder="全部状态">
          <el-option label="全部状态" value="all" />
          <el-option label="正常" value="1" />
          <el-option label="停用" value="0" />
        </el-select>
        <el-button type="primary" plain @click="handleSearch">筛选</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe empty-text="暂无用户数据">
        <el-table-column label="用户" min-width="230">
          <template #default="{ row }">
            <div class="primary-text">{{ row.nickName || '方块兽玩家' }}</div>
            <div class="minor-text">账号：{{ row.account || '未设置账号' }}</div>
            <div class="minor-text">推荐码：{{ row.inviteCode || '未生成' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="来源 / 状态" min-width="150">
          <template #default="{ row }">
            <div>{{ row.sourceText || '小程序' }}</div>
            <el-tag class="status-tag" :type="tagType(row.statusClass)" effect="plain">{{ row.statusText || '未知' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="联系与绑定" min-width="220">
          <template #default="{ row }">
            <div>方块兽：{{ row.beastId || '未绑定' }}</div>
            <div class="minor-text">手机：{{ row.phone || '未填写' }}</div>
            <div class="minor-text">邮箱：{{ row.email || '未填写' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="钱包" min-width="220">
          <template #default="{ row }">
            <div>可用 {{ formatNumber(row.wallet?.gemBalance || 0) }}</div>
            <div class="minor-text">锁定 {{ formatNumber(row.wallet?.lockedGems || 0) }}</div>
            <div class="minor-text">转入 {{ formatNumber(row.wallet?.totalRecharged || 0) }} / 获益 {{ formatNumber(row.wallet?.totalEarned || 0) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="业务统计" min-width="220">
          <template #default="{ row }">
            <div>担保 {{ formatNumber(row.stats?.guaranteeDone || 0) }} / {{ formatNumber(row.stats?.guaranteeTotal || 0) }}</div>
            <div class="minor-text">有效推荐 {{ formatNumber(row.stats?.effectiveInvitedCount || 0) }}</div>
            <div class="minor-text">推广奖励 {{ formatNumber(row.stats?.rewardAmount || 0) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="180">
          <template #default="{ row }">
            <div>创建：{{ row.createdTime || '—' }}</div>
            <div class="minor-text">更新：{{ row.updatedTime || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" min-width="220">
          <template #default="{ row }">
            <el-space wrap>
              <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              <el-button
                size="small"
                :type="row.status === 0 ? 'success' : 'warning'"
                plain
                :loading="actionBusy === String(row.id)"
                @click="handleBanUser(row)"
              >{{ row.status === 0 ? '解除拉黑' : '拉黑' }}</el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :loading="actionBusy === String(row.id)"
                @click="handleDeleteUser(row)"
              >删除</el-button>
            </el-space>
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

    <el-drawer v-model="detailVisible" size="560px" :title="detail.nickName || '用户详情'" destroy-on-close>
      <div class="detail-kicker">USER DETAIL</div>
      <div class="detail-meta-row">
        <el-tag :type="tagType(detail.statusClass)" effect="plain">{{ detail.statusText || '未知状态' }}</el-tag>
        <span class="detail-source">{{ detail.sourceText || '小程序' }}</span>
        <el-button
          size="small"
          :type="detail.status === 0 ? 'success' : 'warning'"
          plain
          @click="handleBanUser(detail); detailVisible = false"
        >{{ detail.status === 0 ? '解除拉黑' : '拉黑账户' }}</el-button>
        <el-button
          size="small"
          type="danger"
          plain
          @click="handleDeleteUser(detail); detailVisible = false"
        >删除账号</el-button>
      </div>

      <el-descriptions :column="1" border class="detail-descriptions">
        <el-descriptions-item label="用户标识">{{ detail.userKey || '—' }}</el-descriptions-item>
        <el-descriptions-item label="账号">{{ detail.account || '—' }}</el-descriptions-item>
        <el-descriptions-item label="方块兽 ID">{{ detail.beastId || '—' }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ detail.phone || '—' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ detail.email || '—' }}</el-descriptions-item>
        <el-descriptions-item label="推荐码">{{ detail.inviteCode || '—' }}</el-descriptions-item>
        <el-descriptions-item label="邀请人">{{ detail.invitedByNickName || '—' }}</el-descriptions-item>
        <el-descriptions-item label="邀请人推荐码">{{ detail.invitedByInviteCode || '—' }}</el-descriptions-item>
        <el-descriptions-item label="绑定邀请时间">{{ detail.invitedAt || '—' }}</el-descriptions-item>
        <el-descriptions-item label="推广生效时间">{{ detail.promotionEffectiveAt || '—' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detail.createdTime || '—' }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ detail.updatedTime || '—' }}</el-descriptions-item>
      </el-descriptions>

      <div class="detail-grid">
        <div class="mini-card">
          <div class="mini-label">钱包可用</div>
          <div class="mini-value">{{ formatNumber(detail.wallet?.gemBalance || 0) }}</div>
          <div class="mini-helper">锁定 {{ formatNumber(detail.wallet?.lockedGems || 0) }}</div>
        </div>
        <div class="mini-card">
          <div class="mini-label">累计转入</div>
          <div class="mini-value">{{ formatNumber(detail.wallet?.totalRecharged || 0) }}</div>
          <div class="mini-helper">累计转出 {{ formatNumber(detail.wallet?.totalSpent || 0) }}</div>
        </div>
        <div class="mini-card">
          <div class="mini-label">担保完成</div>
          <div class="mini-value">{{ formatNumber(detail.stats?.guaranteeDone || 0) }}</div>
          <div class="mini-helper">总担保 {{ formatNumber(detail.stats?.guaranteeTotal || 0) }}</div>
        </div>
        <div class="mini-card">
          <div class="mini-label">推广奖励</div>
          <div class="mini-value">{{ formatNumber(detail.stats?.rewardAmount || 0) }}</div>
          <div class="mini-helper">有效推荐 {{ formatNumber(detail.stats?.effectiveInvitedCount || 0) }}</div>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="importVisible" width="760px" title="批量导入用户" destroy-on-close>
      <el-alert
        title="每行一位用户，格式为：账号,昵称,方块兽ID,手机号,邮箱,状态。状态可填 1/0、正常/停用；首行若是表头会自动跳过。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-input
        v-model="importForm.text"
        type="textarea"
        :rows="11"
        maxlength="12000"
        show-word-limit
        class="import-textarea"
        placeholder="player_001,星辰大主宰,9100503,13800000000,star@example.com,1&#10;player_002,龙王传说,9100504,13900000000,dragon@example.com,正常"
      />
      <div class="import-tips">
        <div class="tips-title">导入说明</div>
        <ul>
          <li>优先按 **账号 / 方块兽 ID / 手机 / 邮箱** 匹配已有用户，命中则更新。</li>
          <li>未命中时会自动创建新用户，并复用现有 `users` / `user_wallets` 表结构。</li>
          <li>导入只写现有字段，不会额外生成业务字段。</li>
        </ul>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="importVisible = false">取消</el-button>
          <el-button type="primary" :loading="importSubmitting" @click="submitImport">开始导入</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-manage-shell {
  display: grid;
  gap: 16px;
}

.summary-row {
  margin-bottom: 0;
}

.summary-card {
  overflow: hidden;
  position: relative;
  min-height: 128px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.summary-card::after {
  content: '';
  position: absolute;
  inset: auto -24px -44px auto;
  width: 120px;
  height: 120px;
  border-radius: 999px;
  background: rgba(64, 158, 255, 0.08);
}

.summary-card.is-success::after { background: rgba(64, 194, 124, 0.1); }
.summary-card.is-indigo::after { background: rgba(78, 89, 255, 0.1); }
.summary-card.is-amber::after { background: rgba(250, 173, 20, 0.1); }
.summary-card.is-violet::after { background: rgba(139, 92, 246, 0.1); }

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

.panel-head {
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

.panel-desc {
  margin-top: 8px;
  max-width: 760px;
  color: #6b7280;
  line-height: 1.7;
}

.panel-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
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
  width: 160px;
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

.status-tag {
  margin-top: 8px;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  color: #94a3b8;
}

.detail-meta-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
}

.detail-source {
  color: #6b7280;
}

.detail-descriptions {
  margin-top: 18px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.mini-card {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid #edf2f7;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.mini-label {
  font-size: 13px;
  color: #94a3b8;
}

.mini-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  color: #111827;
}

.mini-helper {
  margin-top: 6px;
  color: #6b7280;
}

.import-textarea {
  margin-top: 16px;
}

.import-tips {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #edf2f7;
}

.tips-title {
  font-weight: 700;
  color: #1f2937;
}

.import-tips ul {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #6b7280;
  line-height: 1.8;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 960px) {
  .panel-head {
    flex-direction: column;
  }

  .toolbar-input,
  .toolbar-select {
    width: 100%;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
