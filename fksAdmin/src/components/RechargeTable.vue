<script setup>
import { formatNumber } from '../utils/format'
import StatusPill from './StatusPill.vue'

const props = defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['inspect'])

function resolveTone(statusClass = '') {
  if (statusClass === 'success' || statusClass === 'done') return 'success'
  if (statusClass === 'pending') return 'warning'
  if (statusClass === 'cancelled' || statusClass === 'expired') return 'danger'
  return 'neutral'
}
</script>

<template>
  <div class="table-shell">
    <div v-if="!rows.length" class="table-empty">暂无充值记录。</div>
    <div v-else class="table-scroll">
      <table class="ops-table">
        <thead>
          <tr>
            <th>用户</th>
            <th>充值数量</th>
            <th>校验信息</th>
            <th>状态</th>
            <th>时间</th>
            <th class="align-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>
              <div class="strong-text">{{ row.userNickName || '方块兽玩家' }}</div>
              <div class="muted-text">账号：{{ row.account || '未设置账号' }}</div>
              <div class="muted-text">方块兽：{{ row.beastId || '未绑定' }}</div>
            </td>
            <td>
              <div class="number-text">+{{ formatNumber(row.amount || 0) }}</div>
              <div class="muted-text">订单号：{{ row.id || '—' }}</div>
            </td>
            <td>
              <div class="strong-text">{{ row.verifyCode || '无校验码' }}</div>
              <div class="muted-text">到账来源：{{ row.createSource || 'miniapp' }}</div>
            </td>
            <td>
              <StatusPill :label="row.statusText || '未知状态'" :tone="resolveTone(row.statusClass || '')" />
            </td>
            <td>
              <div class="muted-text">创建：{{ row.time || '—' }}</div>
              <div class="muted-text">到账：{{ row.verifiedTime || row.matchedTime || '—' }}</div>
            </td>
            <td class="align-right">
              <button class="table-btn" type="button" @click="emit('inspect', row)">详情</button>
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
  min-width: 980px;
  border-collapse: collapse;
}

.ops-table th,
.ops-table td {
  padding: 16px 18px;
  border-bottom: 1px solid rgba(191, 205, 230, 0.08);
  text-align: left;
  vertical-align: top;
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

.strong-text,
.number-text {
  color: #fff8ec;
  font-weight: 700;
}

.number-text {
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: 22px;
}

.muted-text {
  margin-top: 6px;
  color: rgba(229, 236, 248, 0.68);
  line-height: 1.7;
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
  padding: 26px 18px;
  text-align: center;
  color: rgba(229, 236, 248, 0.72);
}
</style>
