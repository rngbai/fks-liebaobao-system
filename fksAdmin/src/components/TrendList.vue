<script setup>
import { computed } from 'vue'
import { formatNumber } from '../utils/format'

const props = defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
})

const normalizedRows = computed(() => props.rows.slice().reverse())
</script>

<template>
  <div v-if="!rows.length" class="empty-state">暂无近 7 天流水数据。</div>
  <div v-else class="trend-list">
    <article v-for="row in normalizedRows" :key="row.date" class="trend-item">
      <div class="trend-date">{{ row.date }}</div>
      <div class="trend-metrics">
        <span class="metric-chip">充值 {{ formatNumber(row.rechargeAmount || 0) }} / {{ formatNumber(row.rechargeCount || 0) }} 笔</span>
        <span class="metric-chip">转出 {{ formatNumber(row.transferAmount || 0) }} / {{ formatNumber(row.transferCount || 0) }} 笔</span>
        <span class="metric-chip">新担保 {{ formatNumber(row.guaranteeCreatedCount || 0) }}</span>
      </div>
    </article>
  </div>
</template>

<style scoped>
.trend-list {
  display: grid;
  gap: 12px;
}

.trend-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(255, 255, 255, 0.03);
}

.trend-date {
  color: #ffe5b8;
  font-size: 15px;
  font-weight: 700;
}

.trend-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.metric-chip {
  display: inline-flex;
  align-items: center;
  padding: 9px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #eef2ff;
  font-size: 12px;
}

.empty-state {
  padding: 26px 18px;
  border-radius: 22px;
  border: 1px dashed rgba(255, 255, 255, 0.12);
  text-align: center;
  color: rgba(223, 231, 255, 0.68);
}

@media (max-width: 760px) {
  .trend-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .trend-metrics {
    justify-content: flex-start;
  }
}
</style>
