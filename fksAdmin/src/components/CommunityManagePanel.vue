<template>
  <div class="community-panel">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="filterCat" placeholder="全部分类" clearable style="width:150px" @change="onFilterChange">
          <el-option v-for="c in CATEGORIES" :key="c.id" :label="c.label" :value="c.id" />
        </el-select>
        <el-select v-model="filterSub" placeholder="全部子类" clearable style="width:150px" :disabled="!filterCat" @change="loadList">
          <el-option v-for="s in currentSubTabs" :key="s" :label="s" :value="s" />
        </el-select>
        <el-checkbox v-model="showInactive" @change="loadList">显示已下架</el-checkbox>
      </div>
      <el-button type="primary" :icon="Plus" @click="openAdd">添加名流</el-button>
    </div>

    <!-- 列表 -->
    <el-table :data="list" v-loading="loading" border stripe style="width:100%;margin-top:16px">
      <el-table-column label="分类" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ getCatLabel(row.category) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sub_tab" label="子类" width="120" />
      <el-table-column label="头像" width="70">
        <template #default="{ row }">
          <el-avatar :size="40" :src="row.avatar_url || ''" :icon="UserFilled" />
        </template>
      </el-table-column>
      <el-table-column prop="nickname" label="昵称" width="130" />
      <el-table-column label="徽章" width="120">
        <template #default="{ row }">
          <el-tag :type="badgeTagType(row.badge_type)" size="small">{{ row.badge_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="bio" label="简介" show-overflow-tooltip />
      <el-table-column prop="wechat" label="微信" width="130" />
      <el-table-column prop="qq" label="QQ" width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '上架' : '下架' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="70" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="confirmDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑名流' : '添加名流'" width="600px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="主分类" prop="category">
          <el-select v-model="form.category" placeholder="选择分类" @change="onFormCatChange" style="width:100%">
            <el-option v-for="c in CATEGORIES" :key="c.id" :label="c.label" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="子分类" prop="sub_tab">
          <el-select v-model="form.sub_tab" placeholder="选择子类" style="width:100%" :disabled="!form.category">
            <el-option v-for="s in formSubTabs" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="简介" prop="bio">
          <el-input v-model="form.bio" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="头像">
          <div class="avatar-upload-wrap">
            <el-avatar
              v-if="form.avatar_url"
              :size="64"
              :src="form.avatar_url"
              class="avatar-preview"
            />
            <el-avatar v-else :size="64" :icon="UserFilled" class="avatar-preview" />
            <div class="avatar-upload-actions">
              <el-upload
                action=""
                :show-file-list="false"
                accept="image/png,image/jpeg,image/webp,image/gif"
                :before-upload="handleAvatarUpload"
              >
                <el-button size="small" :loading="avatarUploading">
                  {{ form.avatar_url ? '更换图片' : '上传图片' }}
                </el-button>
              </el-upload>
              <el-button
                v-if="form.avatar_url"
                size="small"
                type="danger"
                plain
                @click="form.avatar_url = ''"
              >移除</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="微信号">
          <el-input v-model="form.wechat" maxlength="64" />
        </el-form-item>
        <el-form-item label="QQ号">
          <el-input v-model="form.qq" maxlength="32" />
        </el-form-item>
        <el-form-item label="游戏标签">
          <el-input v-model="form.game_tag" maxlength="64" placeholder="如：地球猎人" />
        </el-form-item>
        <el-form-item label="徽章类型">
          <el-select v-model="form.badge_type" style="width:160px">
            <el-option v-for="b in BADGE_TYPES" :key="b.value" :label="b.label" :value="b.value" />
          </el-select>
          <el-input v-model="form.badge_label" placeholder="徽章文字" maxlength="16" style="width:160px;margin-left:8px" />
        </el-form-item>
        <el-form-item label="排序权重">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
          <span style="margin-left:8px;color:#999;font-size:12px">数字越小越靠前</span>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="上架" inactive-text="下架" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, UserFilled } from '@element-plus/icons-vue'
import { api } from '../lib/api'

const CATEGORIES = [
  { id: 'captain',  label: '大咖团队长', subTabs: ['地球猎人', '旅行世界', '人猿大陆', '乌龟海战', '保卫方块'] },
  { id: 'broker',   label: '顶商中介',   subTabs: ['兽王/珍兽', '金币/超级币', '矿石/护甲', '宝石', '魔方'] },
  { id: 'streamer', label: '主播抖/快',  subTabs: ['抖音', '快手'] },
  { id: 'blogger',  label: '攻略博主',   subTabs: ['公众号'] },
  { id: 'guild',    label: '猎人公会',   subTabs: [] },
]

const BADGE_TYPES = [
  { value: 'gold',     label: '🥇 金牌' },
  { value: 'silver',   label: '🥈 银牌' },
  { value: 'verified', label: '✅ 认证' },
  { value: 'streamer', label: '🎬 主播' },
  { value: 'guild',    label: '🏰 公会' },
]

const BADGE_TAG_MAP = { gold: 'warning', silver: 'info', verified: 'primary', streamer: 'danger', guild: 'success' }

const list = ref([])
const loading = ref(false)
const saving = ref(false)
const avatarUploading = ref(false)
const filterCat = ref('')
const filterSub = ref('')
const showInactive = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref()

const defaultForm = () => ({
  category: '', sub_tab: '', nickname: '', bio: '',
  avatar_url: '', wechat: '', qq: '', game_tag: '',
  badge_type: 'verified', badge_label: '认证',
  sort_order: 0, is_active: true,
})
const form = ref(defaultForm())

const rules = {
  category: [{ required: true, message: '请选择主分类' }],
  nickname: [{ required: true, message: '请填写昵称' }],
}

const currentSubTabs = computed(() => {
  const cat = CATEGORIES.find(c => c.id === filterCat.value)
  return cat ? cat.subTabs : []
})

const formSubTabs = computed(() => {
  const cat = CATEGORIES.find(c => c.id === form.value.category)
  return cat ? cat.subTabs : []
})

function getCatLabel(id) {
  return CATEGORIES.find(c => c.id === id)?.label || id
}

function badgeTagType(type) {
  return BADGE_TAG_MAP[type] || 'info'
}

function onFilterChange() {
  filterSub.value = ''
  loadList()
}

function onFormCatChange() {
  form.value.sub_tab = ''
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
      reader.onload = e => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
    const res = await api.post('/api/upload/image', {
      image_base64: base64,
      image_name: file.name,
      folder: 'community-avatar',
    })
    form.value.avatar_url = res.path || res.url || ''
    ElMessage.success('上传成功')
  } catch (e) {
    ElMessage.error('上传失败: ' + e.message)
  } finally {
    avatarUploading.value = false
  }
  return false
}

async function loadList() {
  loading.value = true
  try {
    const params = { active_only: showInactive.value ? '0' : '1' }
    if (filterCat.value) params.category = filterCat.value
    if (filterSub.value) params.sub_tab = filterSub.value
    const res = await api.get('/api/manage/community', { params })
    list.value = res.list || []
  } catch (e) {
    ElMessage.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editingId.value = null
  form.value = defaultForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = {
    category: row.category, sub_tab: row.sub_tab, nickname: row.nickname,
    bio: row.bio, avatar_url: row.avatar_url, wechat: row.wechat, qq: row.qq,
    game_tag: row.game_tag, badge_type: row.badge_type, badge_label: row.badge_label,
    sort_order: row.sort_order, is_active: row.is_active,
  }
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    const data = { ...form.value }
    if (editingId.value) {
      await api.post(`/api/manage/community/${editingId.value}`, data)
      ElMessage.success('已更新')
    } else {
      await api.post('/api/manage/community', data)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    loadList()
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

async function confirmDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.nickname}」？`, '确认删除', { type: 'warning' })
  try {
    await api.post(`/api/manage/community/${row.id}`, { _action: 'delete' })
    ElMessage.success('已删除')
    loadList()
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

onMounted(loadList)
</script>

<style scoped>
.community-panel { padding: 4px 0; }
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.avatar-upload-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}
.avatar-preview {
  flex-shrink: 0;
  border: 1px solid #e4e7ed;
}
.avatar-upload-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
