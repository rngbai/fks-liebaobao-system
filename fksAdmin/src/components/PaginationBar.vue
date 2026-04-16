<script setup>
const props = defineProps({
  total: {
    type: Number,
    default: 0,
  },
  currentPage: {
    type: Number,
    default: 1,
  },
  totalPages: {
    type: Number,
    default: 1,
  },
  pageSize: {
    type: Number,
    default: 10,
  },
  start: {
    type: Number,
    default: 0,
  },
  end: {
    type: Number,
    default: 0,
  },
  pageSizes: {
    type: Array,
    default: () => [6, 10, 20],
  },
})

const emit = defineEmits(['update:page', 'update:pageSize'])

function setPage(page) {
  emit('update:page', Number(page || 1))
}

function setPageSize(event) {
  emit('update:pageSize', Number(event.target.value || props.pageSize || 10))
}
</script>

<template>
  <footer v-if="total > 0" class="pager-bar">
    <div class="pager-summary">
      当前显示 <strong>{{ start }}</strong> - <strong>{{ end }}</strong> / <strong>{{ total }}</strong>
    </div>

    <div class="pager-actions">
      <label class="size-box">
        <span>每页</span>
        <select :value="pageSize" @change="setPageSize">
          <option v-for="size in pageSizes" :key="size" :value="size">{{ size }}</option>
        </select>
      </label>

      <div class="pager-switcher">
        <button type="button" :disabled="currentPage <= 1" @click="setPage(1)">首页</button>
        <button type="button" :disabled="currentPage <= 1" @click="setPage(currentPage - 1)">上一页</button>
        <div class="page-indicator">{{ currentPage }} / {{ totalPages }}</div>
        <button type="button" :disabled="currentPage >= totalPages" @click="setPage(currentPage + 1)">下一页</button>
        <button type="button" :disabled="currentPage >= totalPages" @click="setPage(totalPages)">尾页</button>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.pager-bar {
  margin-top: 18px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
  padding-top: 18px;
  border-top: 1px solid rgba(191, 205, 230, 0.1);
}

.pager-summary {
  color: rgba(229, 236, 248, 0.72);
  font-size: 13px;
}

.pager-summary strong {
  color: #fff8ec;
}

.pager-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.size-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: rgba(229, 236, 248, 0.72);
  font-size: 13px;
}

.size-box select {
  width: 82px;
  min-height: 38px;
  padding: 0 12px;
}

.pager-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pager-switcher button,
.page-indicator {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #edf2fb;
  font-size: 13px;
  font-weight: 700;
}

.pager-switcher button {
  cursor: pointer;
}

.pager-switcher button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-indicator {
  display: inline-flex;
  align-items: center;
}
</style>
