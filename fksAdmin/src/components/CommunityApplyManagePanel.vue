<template>
  <div class="apply-panel">
    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-head panel-head--between">
          <span>名流认证申请</span>
          <el-tag type="warning">共 {{ pagination.total }} 条</el-tag>
        </div>
      </template>

      <div class="toolbar-row">
        <el-input
          v-model="filters.query"
          placeholder="搜索标题 / 申请说明 / 用户 / 联系方式 / 板块"
          clearable
          class="toolbar-input"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="filters.status" class="toolbar-select" @change="handleSearch">
          <el-option label="待审核" value="pending" />
          <el-option label="已通过" value="completed" />
          <el-option label="已采纳" value="adopted" />
          <el-option label="暂不处理" value="rejected" />
          <el-option label="全部状态" value="all" />
        </el-select>
        <el-button type="primary" plain @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" border stripe empty-text="暂无名流认证申请">
        <el-table-column label="申请板块" min-width="180">
          <template #default="{ row }">
            <div class="primary-text">{{ row.targetCategoryLabel || row.targetCategory || '社区名流' }}</div>
            <div class="minor-text">{{ row.targetSubTab || '无子分类' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="申请内容" min-width="320">
          <template #default="{ row }">
            <div class="primary-text">{{ row.title || '未命名申请' }}</div>
            <div class="minor-text minor-text--clamp">{{ row.content || '暂无说明' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="申请人" min-width="220">
          <template #default="{ row }">
            <div>{{ row.userNickName || '方块兽玩家' }}</div>
            <div class="minor-text">{{ row.account || '未设置账号' }} / {{ row.beastId || '未绑定' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="联系方式" min-width="160">
          <template #default="{ row }">
            <span>{{ row.contact || '未填写' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="120">
          <template #default="{ row }">
            <el-tag :type="tagType(row.statusClass || row.status)" effect="plain">{{ row.statusText || '待处理' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="180">
          <template #default="{ row }">
            <div>提交：{{ row.time || '—' }}</div>
            <div class="minor-text">处理：{{ row.handledTime || '未处理' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" min-width="280">
          <template #default="{ row }">
            <el-space wrap>
              <el-button
                v-if="row.status === 'pending' && !row.linkedProfileId"
                link
                type="primary"
                @click="openApprove(row)"
              >通过入驻</el-button>
              <el-button
                v-if="row.status === 'pending'"
                size="small"
                type="danger"
                plain
                :loading="actionBusy === String(row.id)"
                @click="handleReject(row)"
              >驳回</el-button>
              <el-button link @click="openDetail(row)">详情</el-button>
              <el-button v-if="row.linkedProfileId" link type="success">已入驻 #{{ row.linkedProfileId }}</el-button>
            </el-space>
          </template>
        </el-table-column>

      </el-table>

      <div class="pagination-row">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="pagination.total"
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="PAGE_SIZES"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="approveVisible" title="通过名流认证并加入社区" width="680px" destroy-on-close>
      <el-alert
        v-if="currentRow"
        :title="`申请人：${currentRow.userNickName || '方块兽玩家'}，申请板块：${currentRow.targetCategoryLabel || currentRow.targetCategory || '社区名流'}${currentRow.targetSubTab ? ` · ${currentRow.targetSubTab}` : ''}`"
        type="info"
        :closable="false"
        class="dialog-alert"
      />
      <el-form ref="approveFormRef" :model="approveForm" :rules="approveRules" label-width="92px">
        <el-form-item label="主分类" prop="category">
          <el-select v-model="approveForm.category" placeholder="选择分类" @change="handleApproveCategoryChange" style="width:100%">
            <el-option v-for="item in CATEGORIES" :key="item.id" :label="item.label" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="子分类">
          <el-select v-model="approveForm.sub_tab" placeholder="选择子类" style="width:100%" :disabled="!approveForm.category || !approveSubTabs.length">
            <el-option v-for="item in approveSubTabs" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="approveForm.nickname" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="简介" prop="bio">
          <el-input v-model="approveForm.bio" type="textarea" :rows="4" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="头像">
          <div class="avatar-upload-wrap">
            <el-avatar v-if="approveForm.avatar_url" :size="64" :src="approveForm.avatar_url" class="avatar-preview" />
            <el-avatar v-else :size="64" :icon="UserFilled" class="avatar-preview" />
            <div class="avatar-upload-actions">
              <el-upload
                action=""
                :show-file-list="false"
                accept="image/png,image/jpeg,image/webp,image/gif"
                :before-upload="handleAvatarUpload"
              >
                <el-button size="small" :loading="avatarUploading">{{ approveForm.avatar_url ? '更换图片' : '上传图片' }}</el-button>
              </el-upload>
              <el-button v-if="approveForm.avatar_url" size="small" type="danger" plain @click="approveForm.avatar_url = ''">移除</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="微信号">
          <el-input v-model="approveForm.wechat" maxlength="64" />
        </el-form-item>
        <el-form-item label="QQ号">
          <el-input v-model="approveForm.qq" maxlength="32" />
        </el-form-item>
        <el-form-item label="游戏标签">
          <el-input v-model="approveForm.game_tag" maxlength="64" placeholder="如：地球猎人" />
        </el-form-item>
        <el-form-item label="徽章">
          <el-select v-model="approveForm.badge_type" style="width:160px">
            <el-option v-for="item in BADGE_TYPES" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-input v-model="approveForm.badge_label" maxlength="16" placeholder="徽章文字" style="width:160px;margin-left:8px" />
        </el-form-item>
        <el-form-item label="排序权重">
          <el-input-number v-model="approveForm.sort_order" :min="0" :max="9999" />
          <span class="form-hint">数字越小越靠前</span>
        </el-form-item>
        <el-form-item label="处理说明">
          <el-input v-model="approveForm.admin_reply" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="立即上架">
          <el-switch v-model="approveForm.is_active" active-text="上架" inactive-text="下架" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitApprove">确认通过并入驻</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="申请详情" width="620px" destroy-on-close>
      <template v-if="detailRow">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="申请板块">{{ detailRow.targetCategoryLabel || detailRow.targetCategory || '社区名流' }}<template v-if="detailRow.targetSubTab"> · {{ detailRow.targetSubTab }}</template></el-descriptions-item>
          <el-descriptions-item label="申请标题">{{ detailRow.title || '未命名申请' }}</el-descriptions-item>
          <el-descriptions-item label="申请说明">{{ detailRow.content || '暂无说明' }}</el-descriptions-item>
          <el-descriptions-item label="联系方式">{{ detailRow.contact || '未填写' }}</el-descriptions-item>
          <el-descriptions-item label="申请人">{{ detailRow.userNickName || '方块兽玩家' }} / {{ detailRow.account || '未设置账号' }} / {{ detailRow.beastId || '未绑定' }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">{{ detailRow.statusText || '待处理' }}</el-descriptions-item>
          <el-descriptions-item label="处理说明">{{ detailRow.adminReply || '暂无处理说明' }}</el-descriptions-item>
          <el-descriptions-item label="关联名流">{{ detailRow.linkedProfileId ? `#${detailRow.linkedProfileId}` : '未生成' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { api } from '../lib/api'

const emit = defineEmits(['count-change'])

const PAGE_SIZES = [10, 20, 50]
const SCENE = 'community_apply'
const FEEDBACK_TYPE = '社区认证申请'
const CATEGORIES = [
  { id: 'captain', label: '大咖团队长', subTabs: ['地球猎人', '旅行世界', '人猿大陆', '乌龟海战', '保卫方块'] },
  { id: 'broker', label: '顶商中介', subTabs: ['兽王/珍兽', '金币/超级币', '矿石/护甲', '宝石', '魔方'] },
  { id: 'streamer', label: '主播抖/快', subTabs: ['抖音', '快手'] },
  { id: 'blogger', label: '攻略博主', subTabs: ['公众号'] },
  { id: 'guild', label: '猎人公会', subTabs: [] },
]
const BADGE_TYPES = [
  { value: 'gold', label: '🥇 金牌' },
  { value: 'silver', label: '🥈 银牌' },
  { value: 'verified', label: '✅ 认证' },
  { value: 'streamer', label: '🎬 主播' },
  { value: 'guild', label: '🏰 公会' },
]

const loading = ref(false)
const submitLoading = ref(false)
const avatarUploading = ref(false)
const rows = ref([])
const actionBusy = ref('')
const approveVisible = ref(false)
const detailVisible = ref(false)
const currentRow = ref(null)
const detailRow = ref(null)
const approveFormRef = ref(null)
const filters = reactive({
  query: '',
  status: 'pending',
})
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})

const defaultApproveForm = () => ({
  category: '',
  sub_tab: '',
  nickname: '',
  bio: '',
  avatar_url: '',
  wechat: '',
  qq: '',
  game_tag: '',
  badge_type: 'verified',
  badge_label: '认证',
  sort_order: 0,
  is_active: true,
  admin_reply: '社区名流认证已通过，已加入对应板块展示。',
})
const approveForm = reactive(defaultApproveForm())
const approveRules = {
  category: [{ required: true, message: '请选择主分类', trigger: 'change' }],
  nickname: [{ required: true, message: '请填写昵称', trigger: 'blur' }],
  bio: [{ required: true, message: '请填写简介', trigger: 'blur' }],
}

const approveSubTabs = computed(() => {
  const category = CATEGORIES.find(item => item.id === approveForm.category)
  return category ? category.subTabs : []
})

watch(() => pagination.total, (total) => emit('count-change', Number(total || 0)), { immediate: true })

function tagType(statusClass = '') {
  if (statusClass === 'completed' || statusClass === 'success') return 'success'
  if (statusClass === 'adopted' || statusClass === 'info') return 'primary'
  if (statusClass === 'rejected' || statusClass === 'danger') return 'danger'
  if (statusClass === 'pending' || statusClass === 'warning') return 'warning'
  return 'info'
}

function resetApproveForm() {
  Object.assign(approveForm, defaultApproveForm())
}

function buildListUrl() {
  const params = new URLSearchParams({
    page: String(pagination.page),
    page_size: String(pagination.pageSize),
    type: FEEDBACK_TYPE,
    scene: SCENE,
  })
  if (filters.status && filters.status !== 'all') {
    params.set('status', filters.status)
  }
  if (String(filters.query || '').trim()) {
    params.set('query', String(filters.query || '').trim())
  }
  return `/api/manage/feedbacks?${params.toString()}`
}

async function loadList() {
  loading.value = true
  try {
    const data = await api.get(buildListUrl())
    rows.value = Array.isArray(data.list) ? data.list : []
    const nextPagination = data.pagination || {}
    pagination.total = Number(nextPagination.total || rows.value.length || 0)
    pagination.page = Math.max(1, Number(nextPagination.page || pagination.page || 1))
    pagination.pageSize = Math.max(1, Number(nextPagination.pageSize || pagination.pageSize || 10))
  } catch (error) {
    ElMessage.error(error.message || '读取名流认证申请失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadList()
}

function handleReset() {
  filters.query = ''
  filters.status = 'pending'
  pagination.page = 1
  pagination.pageSize = 10
  loadList()
}

function handlePageChange(page) {
  pagination.page = Math.max(1, Number(page || 1))
  loadList()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = Math.max(1, Number(pageSize || 10))
  pagination.page = 1
  loadList()
}

function handleApproveCategoryChange() {
  if (!approveSubTabs.value.includes(approveForm.sub_tab)) {
    approveForm.sub_tab = approveSubTabs.value[0] || ''
  }
}

function openApprove(row) {
  currentRow.value = row
  resetApproveForm()
  approveForm.category = row.targetCategory || ''
  approveForm.sub_tab = row.targetSubTab || ''
  approveForm.nickname = row.userNickName || ''
  approveForm.bio = row.content || ''
  approveForm.wechat = row.contact || ''
  approveForm.game_tag = row.targetSubTab || row.targetCategoryLabel || ''
  handleApproveCategoryChange()
  approveVisible.value = true
}

function openDetail(row) {
  detailRow.value = row
  detailVisible.value = true
}

async function handleAvatarUpload(file) {
  const MAX_SIZE = 2 * 1024 * 1024
  if (file.size > MAX_SIZE) {
    ElMessage.error('图片不能超过 2MB')
    return false
  }
  avatarUploading.value = true
  try {
    const base64 = await new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = event => resolve(event.target.result)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
    const res = await api.post('/api/upload/image', {
      image_base64: base64,
      image_name: file.name,
      folder: 'community-avatar',
    })
    approveForm.avatar_url = res.path || res.url || ''
    ElMessage.success('上传成功')
  } catch (error) {
    ElMessage.error(`上传失败: ${error.message || '未知错误'}`)
  } finally {
    avatarUploading.value = false
  }
  return false
}

async function submitApprove() {
  if (!currentRow.value?.id) return
  await approveFormRef.value?.validate()
  submitLoading.value = true
  try {
    const payload = {
      feedback_id: currentRow.value.id,
      approve_to_profile: true,
      admin_reply: String(approveForm.admin_reply || '').trim(),
      profile: {
        category: approveForm.category,
        sub_tab: approveForm.sub_tab,
        nickname: approveForm.nickname,
        bio: approveForm.bio,
        avatar_url: approveForm.avatar_url,
        wechat: approveForm.wechat,
        qq: approveForm.qq,
        game_tag: approveForm.game_tag,
        badge_type: approveForm.badge_type,
        badge_label: approveForm.badge_label,
        sort_order: approveForm.sort_order,
        is_active: approveForm.is_active,
      },
    }
    await api.post('/api/manage/feedback/update-status', payload)
    approveVisible.value = false
    ElMessage.success('认证申请已通过并加入名流列表')
    await loadList()
  } catch (error) {
    ElMessage.error(error.message || '通过名流认证失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleReject(row) {
  let promptResult
  try {
    promptResult = await ElMessageBox.prompt('请填写驳回原因，用户会在申请记录里看到处理说明。', '驳回认证申请', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputValue: row.adminReply || '资料不足，请补充真实信息后重新申请',
      inputPlaceholder: '请输入驳回原因',
    })
  } catch {
    return
  }

  actionBusy.value = String(row.id)
  try {
    await api.post('/api/manage/feedback/update-status', {
      feedback_id: row.id,
      status: 'rejected',
      admin_reply: String(promptResult.value || '').trim() || '资料不足，请补充真实信息后重新申请',
    })
    ElMessage.success('已驳回该认证申请')
    await loadList()
  } catch (error) {
    ElMessage.error(error.message || '驳回认证申请失败')
  } finally {
    actionBusy.value = ''
  }
}

defineExpose({
  reload: loadList,
})

onMounted(loadList)
</script>


<style scoped>
.apply-panel {
  padding: 4px 0;
}

.panel-head--between,
.toolbar-row,
.avatar-upload-wrap,
.avatar-upload-actions {
  display: flex;
}

.panel-head--between,
.toolbar-row {
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-input {
  width: min(420px, 100%);
}

.toolbar-select {
  width: 160px;
}

.primary-text {
  font-weight: 600;
  color: #1f2d3d;
}

.minor-text {
  margin-top: 4px;
  font-size: 12px;
  color: #7a8499;
}

.minor-text--clamp {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.dialog-alert {
  margin-bottom: 16px;
}

.avatar-upload-wrap {
  align-items: center;
  gap: 16px;
}

.avatar-preview {
  flex-shrink: 0;
  border: 1px solid #e4e7ed;
}

.avatar-upload-actions {
  flex-direction: column;
  gap: 8px;
}

.form-hint {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
