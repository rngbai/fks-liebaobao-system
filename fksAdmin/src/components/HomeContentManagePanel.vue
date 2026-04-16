<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../lib/api'

const emit = defineEmits(['count-change'])

const ACTION_OPTIONS = [
  { label: 'QQ群', value: 'group' },
  { label: '页面跳转', value: 'navigate' },
  { label: '切换 Tab', value: 'switchTab' },
  { label: '无动作', value: 'none' },
]

function createUniqueId(prefix = 'slot') {
  return `${prefix}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
}

function cloneData(data) {
  return JSON.parse(JSON.stringify(data || {}))
}

function createEmptyTopBanner() {
  return {
    id: createUniqueId('top'),
    label: '广告',
    title: '',
    desc: '',
    brand: '',
    cta: '立即查看',
    visualTitle: '',
    visualTag: '',
    type: 'group',
    url: '',
    qq: '',
    gradient: 'linear-gradient(135deg,#f7f8fc 0%,#ffffff 52%,#eef3ff 100%)',
  }
}

function createEmptyPromoCard() {
  return {
    id: createUniqueId('promo'),
    title: '',
    subtitle: '',
    badge: '',
    accent: '立即查看',
    type: 'group',
    url: '',
    qq: '',
    gradient: 'linear-gradient(135deg,#171a3b 0%,#3247c5 55%,#60d7ff 100%)',
  }
}

function createEmptyContent() {
  return {
    hotNotice: '',
    officialGroup: {
      name: '方块兽交易交流群',
      qq: '769851293',
    },
    topBanners: [createEmptyTopBanner()],
    bannerCards: [createEmptyPromoCard()],
  }
}

function createEmptyPayload() {
  return {
    summary: {
      topBannerCount: 0,
      bannerCardCount: 0,
      slotCount: 0,
      noticeLength: 0,
      officialGroupQq: '',
      updatedAt: '',
    },
    content: createEmptyContent(),
    updatedAt: '',
    configKey: 'home_content',
  }
}

function normalizeTopBanner(item = {}) {
  return {
    ...createEmptyTopBanner(),
    ...cloneData(item),
    id: String(item.id || createUniqueId('top')),
  }
}

function normalizePromoCard(item = {}) {
  return {
    ...createEmptyPromoCard(),
    ...cloneData(item),
    id: String(item.id || createUniqueId('promo')),
  }
}

function createContentModel(source = {}) {
  const raw = cloneData(source)
  return {
    hotNotice: String(raw.hotNotice || '').trim(),
    officialGroup: {
      name: String(raw.officialGroup?.name || '方块兽交易交流群').trim(),
      qq: String(raw.officialGroup?.qq || '769851293').trim(),
    },
    topBanners: Array.isArray(raw.topBanners) && raw.topBanners.length
      ? raw.topBanners.map((item) => normalizeTopBanner(item))
      : [createEmptyTopBanner()],
    bannerCards: Array.isArray(raw.bannerCards) && raw.bannerCards.length
      ? raw.bannerCards.map((item) => normalizePromoCard(item))
      : [createEmptyPromoCard()],
  }
}

function applyContent(content = {}) {
  const next = createContentModel(content)
  draft.hotNotice = next.hotNotice
  draft.officialGroup.name = next.officialGroup.name
  draft.officialGroup.qq = next.officialGroup.qq
  draft.topBanners.splice(0, draft.topBanners.length, ...next.topBanners)
  draft.bannerCards.splice(0, draft.bannerCards.length, ...next.bannerCards)
}

function tagType(actionType = '') {
  if (actionType === 'group') return 'success'
  if (actionType === 'navigate') return 'primary'
  if (actionType === 'switchTab') return 'warning'
  return 'info'
}

function actionLabel(actionType = '') {
  const match = ACTION_OPTIONS.find((item) => item.value === actionType)
  return match?.label || '无动作'
}

function resolveActionTarget(item = {}) {
  if (item.type === 'group') {
    return item.qq || draft.officialGroup.qq || '未设置群号'
  }
  if (item.type === 'navigate' || item.type === 'switchTab') {
    return item.url || '未设置页面路径'
  }
  return '无跳转动作'
}

const loading = ref(false)
const saving = ref(false)
const payload = ref(createEmptyPayload())
const draft = reactive(createEmptyContent())
const dialogVisible = ref(false)
const dialogMode = ref('add')
const dialogKind = ref('top')
const dialogIndex = ref(-1)
const dialogForm = reactive(createEmptyTopBanner())
const savedSnapshot = ref('')

const slotCount = computed(() => draft.topBanners.length + draft.bannerCards.length)
const hasUnsavedChanges = computed(() => JSON.stringify(createContentModel(draft)) !== savedSnapshot.value)
const dialogTitle = computed(() => {
  const prefix = dialogMode.value === 'edit' ? '编辑' : '新增'
  return `${prefix}${dialogKind.value === 'top' ? '顶部轮播' : '中部推荐位'}`
})
const summaryCards = computed(() => [
  {
    label: '顶部轮播',
    value: String(draft.topBanners.length),
    helper: '首页顶部广告位',
    tone: 'primary',
  },
  {
    label: '中部推荐位',
    value: String(draft.bannerCards.length),
    helper: '首页活动轮播卡片',
    tone: 'violet',
  },
  {
    label: '官方群号',
    value: draft.officialGroup.qq || '未设置',
    helper: draft.officialGroup.name || '官方群信息',
    tone: 'success',
  },
  {
    label: '平台快报',
    value: `${String(draft.hotNotice || '').length}`,
    helper: '当前公告字数',
    tone: 'amber',
  },
])

watch(slotCount, (count) => emit('count-change', Number(count || 0)), { immediate: true })

async function loadContent({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const data = await api.get('/api/manage/home-content')
    const nextContent = createContentModel(data.content)
    payload.value = {
      ...createEmptyPayload(),
      ...data,
      content: nextContent,
    }
    applyContent(nextContent)
    savedSnapshot.value = JSON.stringify(createContentModel(nextContent))
  } catch (error) {
    ElMessage.error(error.message || '读取首页内容失败')
  } finally {
    loading.value = false
  }
}

function resetDialogForm(kind = 'top', source = null) {
  const next = kind === 'top' ? normalizeTopBanner(source || createEmptyTopBanner()) : normalizePromoCard(source || createEmptyPromoCard())
  Object.keys(dialogForm).forEach((key) => delete dialogForm[key])
  Object.assign(dialogForm, next)
}

function handleAddItem(kind) {
  dialogKind.value = kind
  dialogMode.value = 'add'
  dialogIndex.value = -1
  resetDialogForm(kind)
  dialogVisible.value = true
}

function handleEditItem(kind, item, index) {
  dialogKind.value = kind
  dialogMode.value = 'edit'
  dialogIndex.value = index
  resetDialogForm(kind, item)
  dialogVisible.value = true
}

async function handleRemoveItem(kind, index) {
  const list = kind === 'top' ? draft.topBanners : draft.bannerCards
  if (list.length <= 1) {
    ElMessage.warning('至少保留 1 个广告位，避免首页区域空白')
    return
  }
  try {
    await ElMessageBox.confirm('删除后仍需点击“保存改动”才会正式生效，确认先从当前草稿里移除吗？', '移除广告位', {
      type: 'warning',
      confirmButtonText: '确认移除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  list.splice(index, 1)
  ElMessage.success('已从当前草稿移除')
}

function validateDialogForm() {
  if (!String(dialogForm.title || '').trim()) {
    ElMessage.warning('请填写标题')
    return false
  }
  if ((dialogForm.type === 'navigate' || dialogForm.type === 'switchTab') && !String(dialogForm.url || '').trim()) {
    ElMessage.warning('当前动作类型需要填写页面路径')
    return false
  }
  return true
}

function handleDialogSubmit() {
  if (!validateDialogForm()) return
  const list = dialogKind.value === 'top' ? draft.topBanners : draft.bannerCards
  const item = dialogKind.value === 'top' ? normalizeTopBanner(dialogForm) : normalizePromoCard(dialogForm)
  if (item.type !== 'group') item.qq = ''
  if (item.type === 'none') item.url = ''
  if (dialogMode.value === 'edit' && dialogIndex.value >= 0) {
    list.splice(dialogIndex.value, 1, item)
  } else {
    list.push(item)
  }
  dialogVisible.value = false
  ElMessage.success(dialogMode.value === 'edit' ? '广告位已更新到草稿' : '广告位已加入草稿')
}

async function handleRestoreSaved() {
  if (!hasUnsavedChanges.value) {
    ElMessage.info('当前草稿和已保存内容一致')
    return
  }
  try {
    await ElMessageBox.confirm('这会撤销当前未保存的编辑内容，恢复到最近一次保存的版本。', '恢复已保存内容', {
      type: 'warning',
      confirmButtonText: '恢复',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  applyContent(payload.value.content)
  ElMessage.success('已恢复到最近一次保存内容')
}

async function handleSave() {
  saving.value = true
  try {
    const data = await api.post('/api/manage/home-content', {
      content: createContentModel(draft),
    })
    const nextContent = createContentModel(data.content)
    payload.value = {
      ...createEmptyPayload(),
      ...data,
      content: nextContent,
    }
    applyContent(nextContent)
    savedSnapshot.value = JSON.stringify(createContentModel(nextContent))
    ElMessage.success('首页内容已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存首页内容失败')
  } finally {
    saving.value = false
  }
}

defineExpose({
  reload: loadContent,
})

onMounted(() => {
  loadContent()
})
</script>

<template>
  <div class="home-content-shell">
    <el-row :gutter="16" class="summary-row">
      <el-col v-for="item in summaryCards" :key="item.label" :xs="24" :sm="12" :xl="6">
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
            <div class="panel-eyebrow">HOME CONTENT OPS</div>
            <div class="panel-title">首页广告位 / 内容位管理</div>
            <div class="panel-desc">把首页顶部轮播、中部活动轮播、平台快报和官方群信息收进后台，不再依赖手改小程序前端常量。</div>
          </div>
          <div class="panel-actions">
            <el-button @click="loadContent({ silent: true })">刷新</el-button>
            <el-button @click="handleRestoreSaved">恢复已保存</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">保存改动</el-button>
          </div>
        </div>
      </template>

      <el-alert
        :title="hasUnsavedChanges ? '当前有未保存改动，保存后小程序首页与后台内容位会一起生效。' : '当前草稿已和数据库同步。'"
        :type="hasUnsavedChanges ? 'warning' : 'success'"
        :closable="false"
        show-icon
        class="status-alert"
      />

      <div class="meta-row">
        <span>配置键：{{ payload.configKey }}</span>
        <span>已保存广告位：{{ slotCount }} 个</span>
        <span>最近保存：{{ payload.updatedAt || '首次初始化后会显示' }}</span>
      </div>

      <el-row :gutter="16" class="block-row">
        <el-col :xs="24" :xl="12">
          <el-card class="sub-card" shadow="never">
            <template #header>
              <div class="sub-head">
                <div>
                  <div class="sub-title">平台快报</div>
                  <div class="sub-desc">首页公告文案会直接展示在“平台快报”区域。</div>
                </div>
                <el-tag effect="plain">{{ String(draft.hotNotice || '').length }} 字</el-tag>
              </div>
            </template>
            <el-input
              v-model="draft.hotNotice"
              type="textarea"
              :rows="5"
              maxlength="200"
              show-word-limit
              placeholder="请输入首页平台快报内容"
            />
          </el-card>
        </el-col>
        <el-col :xs="24" :xl="12">
          <el-card class="sub-card" shadow="never">
            <template #header>
              <div class="sub-head">
                <div>
                  <div class="sub-title">官方群信息</div>
                  <div class="sub-desc">群号会给首页“加群说明”、群详情入口和群号复制动作复用。</div>
                </div>
                <el-tag type="success" effect="plain">QQ群</el-tag>
              </div>
            </template>
            <el-form label-width="86px" class="group-form">
              <el-form-item label="群名称">
                <el-input v-model="draft.officialGroup.name" maxlength="64" placeholder="例如：方块兽交易交流群" />
              </el-form-item>
              <el-form-item label="群号">
                <el-input v-model="draft.officialGroup.qq" maxlength="32" placeholder="例如：769851293" />
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="block-row">
        <el-col :xs="24" :xl="12">
          <el-card class="sub-card" shadow="never">
            <template #header>
              <div class="sub-head">
                <div>
                  <div class="sub-title">顶部轮播广告位</div>
                  <div class="sub-desc">控制首页最上方的轮播卡片，适合做主广告位或核心活动入口。</div>
                </div>
                <div class="sub-actions">
                  <el-tag effect="plain">{{ draft.topBanners.length }} 条</el-tag>
                  <el-button type="primary" plain @click="handleAddItem('top')">新增</el-button>
                </div>
              </div>
            </template>

            <el-table v-loading="loading" :data="draft.topBanners" border stripe empty-text="暂无顶部轮播配置">
              <el-table-column label="主内容" min-width="220">
                <template #default="{ row }">
                  <div class="primary-text">{{ row.title || '未填写标题' }}</div>
                  <div class="minor-text">{{ row.desc || '未填写描述' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="文案" min-width="160">
                <template #default="{ row }">
                  <div>{{ row.brand || '未填写品牌文案' }}</div>
                  <div class="minor-text">{{ row.cta || '未填写按钮文案' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="动作" min-width="160">
                <template #default="{ row }">
                  <el-tag :type="tagType(row.type)" effect="plain">{{ actionLabel(row.type) }}</el-tag>
                  <div class="minor-text">{{ resolveActionTarget(row) }}</div>
                </template>
              </el-table-column>
              <el-table-column label="视觉区" min-width="150">
                <template #default="{ row }">
                  <div>{{ row.visualTitle || '未填写视觉标题' }}</div>
                  <div class="minor-text">{{ row.visualTag || '未填写视觉标签' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="操作" fixed="right" min-width="130">
                <template #default="{ row }">
                  <el-space>
                    <el-button link type="primary" @click="handleEditItem('top', row, draft.topBanners.indexOf(row))">编辑</el-button>
                    <el-button link type="danger" @click="handleRemoveItem('top', draft.topBanners.indexOf(row))">移除</el-button>
                  </el-space>
                </template>

              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :xl="12">
          <el-card class="sub-card" shadow="never">
            <template #header>
              <div class="sub-head">
                <div>
                  <div class="sub-title">中部活动轮播</div>
                  <div class="sub-desc">控制首页中部推荐位，适合承接加群、担保、榜单等活动卡片。</div>
                </div>
                <div class="sub-actions">
                  <el-tag effect="plain">{{ draft.bannerCards.length }} 条</el-tag>
                  <el-button type="primary" plain @click="handleAddItem('promo')">新增</el-button>
                </div>
              </div>
            </template>

            <el-table v-loading="loading" :data="draft.bannerCards" border stripe empty-text="暂无中部推荐位配置">
              <el-table-column label="卡片标题" min-width="220">
                <template #default="{ row }">
                  <div class="primary-text">{{ row.title || '未填写标题' }}</div>
                  <div class="minor-text">{{ row.subtitle || '未填写副标题' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="徽标 / 按钮" min-width="160">
                <template #default="{ row }">
                  <div>{{ row.badge || '未填写徽标' }}</div>
                  <div class="minor-text">{{ row.accent || '未填写按钮文案' }}</div>
                </template>
              </el-table-column>
              <el-table-column label="动作" min-width="160">
                <template #default="{ row }">
                  <el-tag :type="tagType(row.type)" effect="plain">{{ actionLabel(row.type) }}</el-tag>
                  <div class="minor-text">{{ resolveActionTarget(row) }}</div>
                </template>
              </el-table-column>
              <el-table-column label="渐变" min-width="140">
                <template #default="{ row }">
                  <div class="gradient-preview" :style="{ background: row.gradient || '#f5f7fa' }"></div>
                </template>
              </el-table-column>
              <el-table-column label="操作" fixed="right" min-width="130">
                <template #default="{ row, $index }">
                  <el-space>
                    <el-button link type="primary" @click="handleEditItem('promo', row, $index)">编辑</el-button>
                    <el-button link type="danger" @click="handleRemoveItem('promo', $index)">移除</el-button>
                  </el-space>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="720px" destroy-on-close>
      <el-form label-width="96px" class="dialog-form">
        <el-form-item label="唯一标识">
          <el-input v-model="dialogForm.id" placeholder="建议用英文或短横线，便于后续维护" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="dialogForm.title" maxlength="64" placeholder="请输入展示标题" />
        </el-form-item>

        <template v-if="dialogKind === 'top'">
          <el-form-item label="标签">
            <el-input v-model="dialogForm.label" maxlength="16" placeholder="例如：广告 / 官方 / 热门" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="dialogForm.desc" type="textarea" :rows="3" maxlength="160" show-word-limit placeholder="请输入轮播描述" />
          </el-form-item>
          <el-form-item label="品牌文案">
            <el-input v-model="dialogForm.brand" maxlength="32" placeholder="例如：官方社群推荐" />
          </el-form-item>
          <el-form-item label="按钮文案">
            <el-input v-model="dialogForm.cta" maxlength="20" placeholder="例如：立即查看" />
          </el-form-item>
          <el-form-item label="视觉标题">
            <el-input v-model="dialogForm.visualTitle" maxlength="32" placeholder="右侧视觉区域标题" />
          </el-form-item>
          <el-form-item label="视觉标签">
            <el-input v-model="dialogForm.visualTag" maxlength="32" placeholder="右侧视觉区域标签" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="副标题">
            <el-input v-model="dialogForm.subtitle" type="textarea" :rows="3" maxlength="180" show-word-limit placeholder="请输入推荐位副标题" />
          </el-form-item>
          <el-form-item label="徽标">
            <el-input v-model="dialogForm.badge" maxlength="20" placeholder="例如：QQ 群 / 平台功能" />
          </el-form-item>
          <el-form-item label="按钮文案">
            <el-input v-model="dialogForm.accent" maxlength="20" placeholder="例如：立即加群" />
          </el-form-item>
        </template>

        <el-form-item label="动作类型">
          <el-select v-model="dialogForm.type" class="dialog-full-width">
            <el-option v-for="item in ACTION_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="dialogForm.type === 'group'" label="QQ群号">
          <el-input v-model="dialogForm.qq" maxlength="32" placeholder="留空时默认复用首页官方群号" />
        </el-form-item>
        <el-form-item v-if="dialogForm.type === 'navigate' || dialogForm.type === 'switchTab'" label="页面路径">
          <el-input v-model="dialogForm.url" maxlength="255" placeholder="例如：/pages/rank/rank" />
        </el-form-item>

        <el-form-item label="渐变背景">
          <el-input v-model="dialogForm.gradient" maxlength="255" placeholder="支持 linear-gradient(...) 这类 CSS 渐变值" />
        </el-form-item>
        <el-form-item label="预览色块">
          <div class="gradient-preview gradient-preview--large" :style="{ background: dialogForm.gradient || '#f5f7fa' }"></div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleDialogSubmit">确认</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.home-content-shell {
  display: grid;
  gap: 16px;
}

.summary-card {
  min-height: 126px;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #faf8ff 100%);
}

.summary-card.is-primary { background: linear-gradient(180deg, #ffffff 0%, #f4f7ff 100%); }
.summary-card.is-violet { background: linear-gradient(180deg, #ffffff 0%, #faf5ff 100%); }
.summary-card.is-success { background: linear-gradient(180deg, #ffffff 0%, #f2fbf7 100%); }
.summary-card.is-amber { background: linear-gradient(180deg, #ffffff 0%, #fff8ed 100%); }

.summary-label {
  font-size: 13px;
  color: #909399;
}

.summary-value {
  margin-top: 12px;
  font-size: 30px;
  font-weight: 700;
  color: #111827;
}

.summary-helper {
  margin-top: 8px;
  color: #6b7280;
  line-height: 1.7;
}

.panel-card,
.sub-card {
  border-radius: 16px;
}

.panel-head,
.sub-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
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

.panel-desc,
.sub-desc,
.meta-row,
.minor-text {
  color: #6b7280;
  line-height: 1.7;
}

.panel-desc,
.sub-desc {
  margin-top: 8px;
}

.panel-actions,
.sub-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.status-alert {
  margin-bottom: 14px;
}

.meta-row {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  font-size: 13px;
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
  width: 360px;
}

.block-row {

  row-gap: 16px;
}

.sub-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.group-form {
  padding-top: 4px;
}

.primary-text {
  font-weight: 600;
  color: #1f2937;
}

.gradient-preview {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.gradient-preview--large {
  height: 86px;
}

.dialog-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.dialog-full-width {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 960px) {
  .panel-head,
  .sub-head {
    flex-direction: column;
  }
}
</style>
