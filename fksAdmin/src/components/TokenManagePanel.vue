<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../lib/api'

const emit = defineEmits(['count-change'])

// ── 当前凭证状态 ──────────────────────────────
const config = reactive({
  userId: '',
  tokenPreview: '',
  expText: '',
  daysLeft: null,
  isExpired: false,
  source: 'env',
  updatedAt: '',
})
const loading = ref(false)
const saving = ref(false)

// ── 编辑表单 ─────────────────────────────────
const formVisible = ref(false)
const form = reactive({ userId: '', token: '' })
const showFullToken = ref(false)

// ── 计算属性 ──────────────────────────────────
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

// ── 打开编辑面板 ──────────────────────────────
function openForm() {
  form.userId = config.userId || ''
  form.token = ''
  showFullToken.value = false
  formVisible.value = true
}

function closeForm() {
  formVisible.value = false
  form.userId = ''
  form.token = ''
}

// ── 保存凭证 ──────────────────────────────────
async function saveConfig() {
  if (!form.userId.trim()) {
    ElMessage.warning('请输入游戏 userId')
    return
  }
  if (!form.token.trim()) {
    ElMessage.warning('请粘贴新的 Token')
    return
  }

  try {
    await ElMessageBox.confirm(
      '确认更新游戏凭证？更新后立即生效，下一次充值校验会使用新 Token，无需重启服务器。',
      '更新游戏凭证',
      {
        type: 'warning',
        confirmButtonText: '确认更新',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return
  }

  saving.value = true
  try {
    const data = await api.post('/api/manage/token-config', {
      userId: form.userId.trim(),
      token: form.token.trim(),
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

    <!-- 主状态卡片 -->
    <el-card shadow="never" class="status-card">
      <template #header>
        <div class="card-head">
          <span class="card-title">游戏凭证状态</span>
          <div class="card-actions">
            <el-tag :type="statusTag.type" effect="dark" size="default">{{ statusTag.text }}</el-tag>
            <el-button type="primary" @click="openForm">更新凭证</el-button>
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

        <el-descriptions-item label="配置来源">
          <el-tag :type="config.source === 'db' ? 'success' : 'info'" effect="plain">
            {{ config.source === 'db' ? '数据库（后台更新）' : '环境变量（初始配置）' }}
          </el-tag>
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
          <span v-else class="text-muted">无法解析</span>
        </el-descriptions-item>

        <el-descriptions-item label="最后更新">
          <span class="text-muted">{{ config.updatedAt || '从未通过后台更新' }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 操作说明 -->
    <el-card shadow="never" class="guide-card">
      <template #header><span class="card-title">使用说明</span></template>
      <ul class="guide-list">
        <li>游戏 Token 有效期约 <strong>30 天</strong>，到期后充值校验（转入宝石）功能将无法使用。</li>
        <li>更新后<strong>立即生效</strong>，无需 SSH 到服务器重启，也不用修改 .env 文件。</li>
        <li>如何获取新 Token：登录游戏 App → 抓包或通过现有工具导出 JWT Token → 粘贴到上面的表单。</li>
        <li>userId 通常不变，只需在首次配置或切换账号时更新。</li>
        <li><strong>安全提醒：</strong>Token 属于敏感凭证，请勿截图分享，后台只显示前缀预览。</li>
      </ul>
    </el-card>

    <!-- 编辑抽屉 -->
    <el-drawer
      v-model="formVisible"
      title="更新游戏凭证"
      size="520px"
      destroy-on-close
    >
      <div class="drawer-body">
        <el-alert
          title="Token 更新后立即对所有新的充值校验请求生效，无需重启服务器。"
          type="info"
          show-icon
          :closable="false"
          class="drawer-tip"
        />

        <el-form label-position="top" class="cred-form">
          <el-form-item label="游戏 userId" required>
            <el-input
              v-model="form.userId"
              placeholder="如 9100503"
              clearable
            />
            <div class="form-help">通常是固定数字，一般不需要修改</div>
          </el-form-item>

          <el-form-item label="新的 JWT Token" required>
            <el-input
              v-model="form.token"
              :type="showFullToken ? 'text' : 'password'"
              placeholder="粘贴完整的 JWT Token（eyJ... 开头）"
              :rows="4"
              :autosize="{ minRows: 3, maxRows: 8 }"
              type="textarea"
              class="token-input"
            />
            <div class="form-actions-row">
              <el-checkbox v-model="showFullToken">显示明文</el-checkbox>
              <span v-if="form.token" class="token-len-hint">{{ form.token.length }} 字符</span>
            </div>
            <div class="form-help">完整 JWT，通常以 eyJ 开头，长度 200+ 字符</div>
          </el-form-item>
        </el-form>

        <div class="drawer-footer">
          <el-button @click="closeForm">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveConfig">确认更新</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.token-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.urgency-banner {
  border-radius: 10px;
}

.status-card,
.guide-card {
  border-radius: 12px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cred-desc {
  margin-top: 4px;
}

.desc-val-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  letter-spacing: 0.03em;
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
.text-muted { color: #909399; }

.guide-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  line-height: 2;
  font-size: 14px;
}

.guide-list li + li {
  margin-top: 4px;
}

.drawer-body {
  padding: 4px 0 80px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.drawer-tip {
  border-radius: 8px;
}

.cred-form {
  margin-top: 4px;
}

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

.token-len-hint {
  font-size: 12px;
  color: #909399;
}

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
</style>
