<script setup>
import { onMounted, reactive, ref, computed, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { api } from '../lib/api'

const emit = defineEmits(['count-change'])

// ── 当前凭证状态 ──────────────────────────────
const config = reactive({
  userId: '',
  userName: '',
  tokenPreview: '',
  tokenType: 'fks',
  expText: '',
  daysLeft: null,
  isExpired: false,
  source: 'env',
  updatedAt: '',
})
const loading = ref(false)
const saving = ref(false)

// ── 手动编辑表单 ──────────────────────────────
const formVisible = ref(false)
const form = reactive({ userId: '', userName: '', token: '', tokenType: 'fks' })
const showFullToken = ref(false)

// ── 扫码登录 ──────────────────────────────────
const qrVisible = ref(false)
const qrImage = ref('')
const qrSessionId = ref('')
const qrStatus = ref('idle') // idle | loading | waiting | success | error | timeout
const qrError = ref('')
const qrCountdown = ref(0)
let qrPollTimer = null
let qrCountdownTimer = null

// ── 计算属性 ──────────────────────────────────
const tokenTypeLabel = computed(() =>
  config.tokenType === 'cw' ? '潮玩宇宙' : '方块兽'
)
const tokenTypeTagType = computed(() =>
  config.tokenType === 'cw' ? 'warning' : 'primary'
)
const statusTag = computed(() => {
  if (config.isExpired) return { type: 'danger', text: '已过期' }
  if (config.daysLeft !== null && config.daysLeft <= 3) return { type: 'warning', text: `${config.daysLeft} 天后过期` }
  if (config.daysLeft !== null && config.daysLeft <= 7) return { type: 'warning', text: `剩余 ${config.daysLeft} 天` }
  if (config.daysLeft !== null) return { type: 'success', text: `剩余 ${config.daysLeft} 天` }
  return { type: 'info', text: '有效期未知' }
})
const urgencyAlert = computed(() => {
  if (config.isExpired) return { type: 'error', text: 'Token 已过期！充值校验功能将失效，请立即更新。' }
  if (config.daysLeft !== null && config.daysLeft <= 3) return { type: 'warning', text: `Token 即将在 ${config.daysLeft} 天后过期，请提前更新以避免充值校验中断。` }
  return null
})
const userNameAlert = computed(() => {
  if (config.userName) return null
  return {
    type: 'warning',
    text: '未设置用户名称 / 方块昵称。小程序“转入宝石”页会读取这里的名称，若与实际收款账号不一致，用户可能无法按正确昵称完成转入。',
  }
})

// ── 数据加载 ──────────────────────────────────
async function loadConfig() {
  loading.value = true
  try {
    const data = await api.get('/api/manage/token-config')
    Object.assign(config, data)
    emit('count-change', config.isExpired ? 1 : 0)
  } catch (err) {
    ElMessage.error(err.message || '读取游戏凭证失败')
  } finally {
    loading.value = false
  }
}

// ── 手动编辑 ──────────────────────────────────
function openForm() {
  form.userId = config.userId || ''
  form.userName = config.userName || ''
  form.token = ''
  form.tokenType = config.tokenType || 'fks'
  showFullToken.value = false
  formVisible.value = true
}

function closeForm() {
  formVisible.value = false
  form.userId = ''
  form.userName = ''
  form.token = ''
}

async function saveConfig() {
  if (!form.userId.trim()) { ElMessage.warning('请输入游戏 userId'); return }
  if (!form.userName.trim()) { ElMessage.warning('请输入用户名称 / 方块昵称'); return }
  if (!form.token.trim()) { ElMessage.warning('请粘贴新的 Token'); return }
  try {
    await ElMessageBox.confirm(
      `确认更新游戏凭证？账号类型：${form.tokenType === 'cw' ? '潮玩宇宙' : '方块兽'}。更新后立即生效，无需重启服务器。`,
      '更新游戏凭证',
      { type: 'warning', confirmButtonText: '确认更新', cancelButtonText: '取消' }
    )
  } catch { return }

  saving.value = true
  try {
    const data = await api.post('/api/manage/token-config', {
      userId: form.userId.trim(),
      userName: form.userName.trim(),
      token: form.token.trim(),
      tokenType: form.tokenType,
    })
    Object.assign(config, data)
    emit('count-change', config.isExpired ? 1 : 0)
    closeForm()
    ElMessage.success('游戏凭证已更新，立即生效')
  } catch (err) {
    ElMessage.error(err.message || '保存凭证失败')
  } finally {
    saving.value = false
  }
}

// ── 扫码登录 ──────────────────────────────────
function stopQrPolling() {
  if (qrPollTimer) { clearInterval(qrPollTimer); qrPollTimer = null }
  if (qrCountdownTimer) { clearInterval(qrCountdownTimer); qrCountdownTimer = null }
}

function closeQr() {
  stopQrPolling()
  qrVisible.value = false
  qrImage.value = ''
  qrSessionId.value = ''
  qrStatus.value = 'idle'
  qrError.value = ''
  qrCountdown.value = 0
}

async function startQrLogin() {
  closeQr()
  qrVisible.value = true
  qrStatus.value = 'loading'
  try {
    const data = await api.post('/api/manage/token-config/qr-start', {})
    qrImage.value = data.qrImage
    qrSessionId.value = data.sessionId
    qrStatus.value = 'waiting'
    qrCountdown.value = data.expiresIn || 180

    // 倒计时
    qrCountdownTimer = setInterval(() => {
      qrCountdown.value = Math.max(0, qrCountdown.value - 1)
    }, 1000)

    // 轮询状态
    qrPollTimer = setInterval(pollQrStatus, 2500)
  } catch (err) {
    qrStatus.value = 'error'
    qrError.value = err.message || '生成二维码失败'
  }
}

async function pollQrStatus() {
  if (!qrSessionId.value) return
  try {
    const data = await api.get(`/api/manage/token-config/qr-status?session=${qrSessionId.value}`)
    if (data.status === 'waiting') return
    stopQrPolling()
    if (data.ok && data.autoSaved) {
      qrStatus.value = 'success'
      Object.assign(config, data)
      emit('count-change', config.isExpired ? 1 : 0)
      if (data.userName) {
        ElMessage.success('潮玩宇宙扫码登录成功，凭证已自动保存！')
      } else {
        ElMessage.warning('潮玩宇宙扫码登录成功，但请手动补充用户名称，确保小程序收款昵称一致。')
      }
      setTimeout(closeQr, 2000)
    } else if (data.status === 'timeout') {
      qrStatus.value = 'timeout'
    } else {
      qrStatus.value = 'error'
      qrError.value = data.message || '登录失败'
    }
  } catch {
    // 忽略轮询错误，继续等待
  }
}

// ── 复制 ──────────────────────────────────────
async function copyUserId() {
  try {
    await navigator.clipboard.writeText(config.userId)
    ElMessage.success('userId 已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

defineExpose({ reload: loadConfig })
onMounted(loadConfig)
onUnmounted(stopQrPolling)
</script>

<template>
  <div v-loading="loading" class="token-panel">

    <!-- 紧急提示横幅 -->
    <el-alert
      v-if="urgencyAlert"
      :title="urgencyAlert.text"
      :type="urgencyAlert.type"
      show-icon
      :closable="false"
      class="urgency-banner"
    />
    <el-alert
      v-if="userNameAlert"
      :title="userNameAlert.text"
      :type="userNameAlert.type"
      show-icon
      :closable="false"
      class="urgency-banner"
    />

    <!-- 主状态卡片 -->
    <el-card shadow="never" class="status-card">
      <template #header>
        <div class="card-head">
          <div class="card-head-left">
            <span class="card-title">游戏凭证状态</span>
            <el-tag :type="tokenTypeTagType" effect="plain" size="small" class="type-tag">
              {{ tokenTypeLabel }}
            </el-tag>
            <el-tag :type="statusTag.type" effect="dark" size="default">{{ statusTag.text }}</el-tag>
          </div>
          <div class="card-actions">
            <el-button type="success" @click="startQrLogin">
              <span>📱 扫码登录（潮玩宇宙）</span>
            </el-button>
            <el-button type="primary" @click="openForm">手动更新</el-button>
            <el-button @click="loadConfig" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border class="cred-desc">
        <el-descriptions-item label="游戏 userId">
          <div class="desc-val-row">
            <span class="mono">{{ config.userId || '未设置' }}</span>
            <el-button v-if="config.userId" link type="primary" size="small" @click="copyUserId">复制</el-button>
          </div>
        </el-descriptions-item>

        <el-descriptions-item label="用户名称 / 方块昵称">
          <span>{{ config.userName || '未设置' }}</span>
          <span class="type-hint">（小程序转入页展示的收款昵称以这里为准）</span>
        </el-descriptions-item>

        <el-descriptions-item label="账号类型">
          <el-tag :type="tokenTypeTagType" effect="plain">
            {{ tokenTypeLabel }}
          </el-tag>
          <span class="type-hint">{{ config.tokenType === 'cw' ? '（验证时使用潮玩宇宙 UA）' : '（验证时使用方块兽 UA）' }}</span>
        </el-descriptions-item>

        <el-descriptions-item label="Token 预览">
          <span class="mono token-preview">{{ config.tokenPreview || '未设置' }}</span>
        </el-descriptions-item>

        <el-descriptions-item label="过期时间">
          <span :class="config.isExpired ? 'text-danger' : ''">{{ config.expText || '—' }}</span>
        </el-descriptions-item>

        <el-descriptions-item label="剩余有效期">
          <el-tag v-if="config.daysLeft !== null" :type="statusTag.type" effect="plain">
            {{ config.isExpired ? '已过期' : `${config.daysLeft} 天` }}
          </el-tag>
          <span v-else class="text-muted">无法解析（非 JWT 格式）</span>
        </el-descriptions-item>

        <el-descriptions-item label="配置来源 / 最后更新">
          <el-tag :type="config.source === 'db' ? 'success' : 'info'" effect="plain" size="small">
            {{ config.source === 'db' ? '数据库' : '环境变量' }}
          </el-tag>
          <span class="text-muted ml-8">{{ config.updatedAt || '从未通过后台更新' }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 使用说明 -->
    <el-card shadow="never" class="guide-card">
      <template #header><span class="card-title">使用说明</span></template>
      <div class="guide-grid">
        <div class="guide-section">
          <div class="guide-section-title">🐾 方块兽账号（FKS）</div>
          <ul class="guide-list">
            <li>Token 有效期约 <strong>30 天</strong>，到期充值校验失效。</li>
            <li>获取方式：登录方块兽 App → 抓包导出 JWT Token。</li>
            <li>点「手动更新」粘贴 Token，选择「方块兽」类型。</li>
          </ul>
        </div>
        <div class="guide-section">
          <div class="guide-section-title">🌟 潮玩宇宙账号（CW）</div>
          <ul class="guide-list">
            <li>点「扫码登录」用微信扫码，自动获取并保存 Token。</li>
            <li>CW Token 通常有效期更长，验证时自动切换 UA。</li>
            <li>也可「手动更新」选择「潮玩宇宙」类型粘贴 Token。</li>
          </ul>
        </div>
      </div>
    </el-card>

    <!-- 手动编辑抽屉 -->
    <el-drawer v-model="formVisible" title="手动更新游戏凭证" size="520px" destroy-on-close>
      <div class="drawer-body">
        <el-alert
          title="Token 更新后立即对所有新的充值校验请求生效，无需重启服务器。"
          type="info" show-icon :closable="false" class="drawer-tip"
        />
        <el-form label-position="top" class="cred-form">
          <el-form-item label="账号类型" required>
            <el-radio-group v-model="form.tokenType">
              <el-radio-button value="fks">🐾 方块兽（FKS）</el-radio-button>
              <el-radio-button value="cw">🌟 潮玩宇宙（CW）</el-radio-button>
            </el-radio-group>
            <div class="form-help">
              {{ form.tokenType === 'cw' ? '验证时使用潮玩宇宙 User-Agent' : '验证时使用方块兽 User-Agent' }}
            </div>
          </el-form-item>
          <el-form-item label="游戏 userId" required>
            <el-input v-model="form.userId" placeholder="如 9100503" clearable />
            <div class="form-help">通常是固定数字，一般不需要修改</div>
          </el-form-item>
          <el-form-item label="用户名称 / 方块昵称" required>
            <el-input v-model="form.userName" placeholder="如 面板小助手" clearable />
            <div class="form-help">小程序“转入宝石”页会直接展示这里的名称，必须和实际收款账号保持一致</div>
          </el-form-item>
          <el-form-item label="新的 Token" required>
            <el-input
              v-model="form.token"
              :type="showFullToken ? 'text' : 'textarea'"
              placeholder="粘贴完整 Token"
              :autosize="{ minRows: 3, maxRows: 8 }"
              class="token-input"
            />
            <div class="form-actions-row">
              <el-checkbox v-model="showFullToken">显示明文</el-checkbox>
              <span v-if="form.token" class="token-len-hint">{{ form.token.length }} 字符</span>
            </div>
            <div class="form-help">
              {{ form.tokenType === 'cw' ? '潮玩宇宙 Token，推荐用扫码方式获取' : '方块兽 JWT，通常以 eyJ 开头，200+ 字符' }}
            </div>
          </el-form-item>
        </el-form>
        <div class="drawer-footer">
          <el-button @click="closeForm">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveConfig">确认更新</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 微信扫码登录对话框 -->
    <el-dialog
      v-model="qrVisible"
      title="微信扫码登录 — 潮玩宇宙"
      width="360px"
      :close-on-click-modal="false"
      @close="closeQr"
    >
      <div class="qr-body">
        <!-- 加载中 -->
        <div v-if="qrStatus === 'loading'" class="qr-placeholder">
          <el-icon class="qr-spin"><Loading /></el-icon>
          <p>正在生成二维码...</p>
        </div>

        <!-- 等待扫码 -->
        <template v-else-if="qrStatus === 'waiting'">
          <img :src="qrImage" class="qr-img" alt="微信二维码" />
          <p class="qr-tip">使用微信扫描上方二维码</p>
          <p class="qr-tip qr-tip--sub">登录潮玩宇宙账号，Token 将自动保存</p>
          <div class="qr-countdown">
            <el-progress
              :percentage="Math.round(qrCountdown / 180 * 100)"
              :stroke-width="6"
              :show-text="false"
              :color="qrCountdown > 60 ? '#67c23a' : qrCountdown > 30 ? '#e6a23c' : '#f56c6c'"
            />
            <span class="qr-countdown-text">{{ qrCountdown }}秒后过期</span>
          </div>
        </template>

        <!-- 成功 -->
        <div v-else-if="qrStatus === 'success'" class="qr-result qr-result--success">
          <div class="qr-result-icon">✅</div>
          <p>登录成功！凭证已自动保存</p>
        </div>

        <!-- 超时 -->
        <div v-else-if="qrStatus === 'timeout'" class="qr-result">
          <div class="qr-result-icon">⏰</div>
          <p>二维码已过期</p>
          <el-button type="primary" @click="startQrLogin">重新生成</el-button>
        </div>

        <!-- 错误 -->
        <div v-else-if="qrStatus === 'error'" class="qr-result qr-result--error">
          <div class="qr-result-icon">❌</div>
          <p>{{ qrError || '生成失败，请重试' }}</p>
          <el-button type="primary" @click="startQrLogin">重试</el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="closeQr">关闭</el-button>
        <el-button v-if="qrStatus === 'waiting'" type="primary" plain @click="startQrLogin">
          刷新二维码
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.token-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.urgency-banner { border-radius: 10px; }

.status-card, .guide-card { border-radius: 12px; }

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.card-head-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.type-tag { font-size: 12px; }

.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.cred-desc { margin-top: 4px; }

.desc-val-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 6px;
}

.ml-8 { margin-left: 8px; }

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  background: #f4f6f8;
  padding: 2px 8px;
  border-radius: 6px;
}

.token-preview {
  color: #606266;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  vertical-align: middle;
}

.text-danger { color: #f56c6c; font-weight: 600; }
.text-muted { color: #909399; font-size: 13px; }

/* 说明区域 */
.guide-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 680px) {
  .guide-grid { grid-template-columns: 1fr; }
}

.guide-section-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
}

.guide-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  line-height: 2;
  font-size: 13px;
}

/* 抽屉 */
.drawer-body {
  padding: 4px 0 80px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.drawer-tip { border-radius: 8px; }
.cred-form { margin-top: 4px; }

.form-help {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.form-actions-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.token-len-hint { font-size: 12px; color: #909399; }

.token-input :deep(textarea) {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

/* 扫码对话框 */
.qr-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  min-height: 260px;
  justify-content: center;
  padding: 8px 0;
}

.qr-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #909399;
}

.qr-spin {
  font-size: 36px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.qr-img {
  width: 220px;
  height: 220px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.qr-tip {
  margin: 0;
  font-size: 14px;
  color: #303133;
  text-align: center;
}

.qr-tip--sub {
  font-size: 12px;
  color: #909399;
}

.qr-countdown {
  width: 220px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qr-countdown-text {
  font-size: 12px;
  color: #909399;
  text-align: center;
}

.qr-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #606266;
}

.qr-result--success { color: #67c23a; }
.qr-result--error { color: #f56c6c; }

.qr-result-icon { font-size: 48px; }
</style>
