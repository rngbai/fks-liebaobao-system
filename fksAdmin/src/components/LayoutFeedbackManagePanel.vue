<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api'

const emit = defineEmits(['count-change'])

const loading = ref(false)
const submitting = ref(false)
const list = ref([])
const total = ref(0)
const pager = reactive({ page: 1, pageSize: 15 })
const statusFilter = ref('all')

const form = reactive({
  title: '',
  pageUrl: '',
  content: '',
  contact: '',
})

const STATUS_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '待处理', value: 'pending' },
  { label: '已采纳', value: 'adopted' },
  { label: '已完成', value: 'completed' },
  { label: '暂不处理', value: 'rejected' },
]

async function loadList() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: String(pager.page),
      page_size: String(pager.pageSize),
      scene: 'admin_layout',
      status: statusFilter.value,
    })
    const data = await api.get(`/api/manage/feedbacks?${params.toString()}`)
    list.value = data.list || []
    total.value = Number(data.pagination?.total || 0)
    emit('count-change', total.value)
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function submitForm() {
  submitting.value = true
  try {
    await api.post('/api/manage/layout-feedback', {
      title: form.title,
      content: form.content,
      contact: form.contact,
      page_url: form.pageUrl,
    })
    ElMessage.success('已提交')
    form.title = ''
    form.pageUrl = ''
    form.content = ''
    form.contact = ''
    pager.page = 1
    await loadList()
  } catch (e) {
    ElMessage.error(e.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function updateRow(row, status) {
  try {
    await api.post('/api/manage/feedback/update-status', {
      feedback_id: row.id,
      status,
    })
    ElMessage.success('状态已更新')
    await loadList()
  } catch (e) {
    ElMessage.error(e.message || '更新失败')
  }
}

defineExpose({
  reload: loadList,
})

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="layout-feedback-root">
    <el-card shadow="never" class="form-card">
      <template #header>
        <span>登记网址 / 后台排版问题</span>
      </template>
      <el-form label-width="100px" @submit.prevent>
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="120" show-word-limit placeholder="例：担保中心四宫格图标错位" />
        </el-form-item>
        <el-form-item label="页面位置">
          <el-input v-model="form.pageUrl" placeholder="例：https://liebaobao.site/admin/ 或 小程序「社区」Tab" />
        </el-form-item>
        <el-form-item label="问题描述" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            maxlength="500"
            show-word-limit
            placeholder="请写清复现步骤、期望效果与当前效果（至少 5 个字）"
          />
        </el-form-item>
        <el-form-item label="备注联系">
          <el-input v-model="form.contact" placeholder="选填：企业微信 / 手机，方便开发回访" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submitForm">提交记录</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="list-card">
      <template #header>
        <div class="list-head">
          <span>已登记列表（{{ total }} 条）</span>
          <div class="list-tools">
            <el-select v-model="statusFilter" style="width: 140px" @change="() => { pager.page = 1; loadList() }">
              <el-option v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
            <el-button :loading="loading" @click="loadList">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" border stripe size="small" empty-text="暂无记录">
        <el-table-column prop="id" label="ID" width="72" />
        <el-table-column prop="title" label="标题" min-width="140" show-overflow-tooltip />
        <el-table-column prop="statusText" label="状态" width="100" />
        <el-table-column prop="time" label="时间" width="168" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="updateRow(row, 'adopted')">采纳</el-button>
            <el-button link type="success" size="small" @click="updateRow(row, 'completed')">完成</el-button>
            <el-button link type="info" size="small" @click="updateRow(row, 'rejected')">暂不处理</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-wrap">
        <el-pagination
          v-model:current-page="pager.page"
          v-model:page-size="pager.pageSize"
          layout="total, prev, pager, next"
          :total="total"
          :page-sizes="[10, 15, 30]"
          @current-change="loadList"
          @size-change="() => { pager.page = 1; loadList() }"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.layout-feedback-root {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.form-card,
.list-card {
  border-radius: 12px;
}
.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.list-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pager-wrap {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
