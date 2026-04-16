<script setup>
import StatusPill from './StatusPill.vue'

defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['inspect'])

function resolveTone(statusClass = '') {
  if (statusClass === 'completed') return 'info'
  if (statusClass === 'adopted') return 'success'
  if (statusClass === 'pending') return 'warning'
  if (statusClass === 'rejected') return 'danger'
  return 'neutral'
}
</script>

<template>
  <div class="table-shell">
    <div v-if="!rows.length" class="table-empty">当前没有反馈档案。</div>
    <div v-else class="table-scroll">
      <table class="ops-table">
        <thead>
          <tr>
            <th>反馈</th>
            <th>用户</th>
            <th>状态</th>
            <th>时间</th>
            <th>处理说明</th>
            <th class="align-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in rows" :key="item.id">
            <td>
              <div class="title-cell">
                <div class="type-tag">{{ item.type || '其他' }}</div>
                <div class="title-text">{{ item.title || '未命名反馈' }}</div>
                <div class="content-text">{{ item.content || '暂无描述' }}</div>
              </div>
            </td>
            <td>
              <div class="user-text">{{ item.userNickName || '方块兽玩家' }}</div>
              <div class="sub-text">{{ item.account || '未设置账号' }}</div>
              <div class="sub-text">{{ item.beastId || '未绑定方块兽 ID' }}</div>
            </td>
            <td>
              <StatusPill :label="item.statusText || '待处理'" :tone="resolveTone(item.statusClass || '')" />
            </td>
            <td>
              <div class="time-text">提交：{{ item.time || '—' }}</div>
              <div class="sub-text">处理：{{ item.handledTime || '未处理' }}</div>
            </td>
            <td>
              <div class="reply-text">{{ item.adminReply || '暂无处理说明' }}</div>
            </td>
            <td class="align-right">
              <button class="table-btn" type="button" @click="emit('inspect', item)">详情</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.table-shell {
  border-radius: 24px;
  border: 1px solid rgba(191, 205, 230, 0.1);
  background: rgba(255, 255, 255, 0.03);
}

.table-scroll {
  overflow-x: auto;
}

.ops-table {
  width: 100%;
  min-width: 1160px;
  border-collapse: collapse;
}

.ops-table th,
.ops-table td {
  padding: 16px 18px;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid rgba(191, 205, 230, 0.08);
}

.ops-table th {
  position: sticky;
  top: 0;
  background: rgba(11, 18, 30, 0.94);
  color: rgba(222, 230, 243, 0.52);
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.ops-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.035);
}

.ops-table tbody tr:last-child td {
  border-bottom: none;
}

.title-cell {
  min-width: 300px;
}

.type-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(103, 128, 255, 0.16);
  border: 1px solid rgba(138, 163, 255, 0.18);
  color: #d4dcff;
  font-size: 12px;
  font-weight: 700;
}

.title-text {
  margin-top: 10px;
  color: #fff7e8;
  font-size: 16px;
  font-weight: 700;
}

.content-text,
.sub-text,
.reply-text,
.user-text,
.time-text {
  margin-top: 6px;
}

.content-text,
.sub-text,
.reply-text,
.time-text {
  color: rgba(223, 231, 255, 0.7);
  line-height: 1.72;
}

.user-text {
  color: #eef2ff;
  font-weight: 600;
}

.align-right {
  text-align: right;
}

.table-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
  font-weight: 700;
  cursor: pointer;
}

.table-empty {
  padding: 24px;
  text-align: center;
  color: rgba(223, 231, 255, 0.7);
}
</style>
