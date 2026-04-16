<script setup>
import { computed } from 'vue'
import StatusPill from './StatusPill.vue'

const props = defineProps({
  item: {
    type: Object,
    default: () => ({}),
  },
  busy: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit', 'inspect'])

function resolveTone(statusClass = '') {
  if (statusClass === 'completed') return 'info'
  if (statusClass === 'adopted') return 'success'
  if (statusClass === 'pending') return 'warning'
  if (statusClass === 'rejected') return 'danger'
  return 'neutral'
}

const tone = computed(() => resolveTone(props.item.statusClass || ''))
const quickActions = [
  { key: 'adopted', label: '采纳', style: 'is-adopted' },
  { key: 'completed', label: '完成', style: 'is-completed' },
  { key: 'rejected', label: '暂不处理', style: 'is-rejected' },
]
</script>

<template>
  <article class="feedback-row">
    <div class="feedback-main">
      <div class="feedback-headline">
        <div>
          <div class="feedback-topline">
            <span class="type-badge">{{ item.type || '其他' }}</span>
            <StatusPill :label="item.statusText || '待处理'" :tone="tone" />
          </div>
          <div class="feedback-title">{{ item.title || '未命名反馈' }}</div>
          <div class="feedback-content">{{ item.content || '暂无描述' }}</div>
        </div>
        <div class="feedback-id">#{{ item.id }}</div>
      </div>

      <div class="feedback-meta-grid">
        <div class="meta-item">
          <div class="meta-label">提交用户</div>
          <div class="meta-value">{{ item.userNickName || '方块兽玩家' }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">账号 / 方块兽</div>
          <div class="meta-value">{{ item.account || '未设置账号' }} / {{ item.beastId || '未绑定' }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">联系方式</div>
          <div class="meta-value">{{ item.contact || '未填写' }}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">提交时间</div>
          <div class="meta-value">{{ item.time || '—' }}</div>
        </div>
      </div>
    </div>

    <div class="feedback-actions">
      <button class="ghost-btn" type="button" @click="emit('inspect', item)">查看详情</button>
      <button
        v-for="action in quickActions"
        :key="action.key"
        :class="['quick-btn', action.style]"
        type="button"
        :disabled="busy"
        @click="emit('submit', { item, status: action.key })"
      >
        {{ busy ? '处理中...' : action.label }}
      </button>
    </div>
  </article>
</template>

<style scoped>
.feedback-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 18px;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(191, 205, 230, 0.1);
  background: rgba(255, 255, 255, 0.035);
}

.feedback-headline {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.feedback-topline,
.feedback-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.type-badge,
.meta-label,
.feedback-id {
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(222, 230, 243, 0.48);
}

.type-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(138, 163, 255, 0.12);
  border: 1px solid rgba(138, 163, 255, 0.18);
  color: #dbe4ff;
  font-weight: 700;
}

.feedback-title {
  margin-top: 10px;
  font-size: 20px;
  font-weight: 800;
  color: #fff8ec;
}

.feedback-content,
.meta-value {
  margin-top: 8px;
  color: rgba(229, 236, 248, 0.74);
  line-height: 1.75;
}

.feedback-meta-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.meta-item {
  padding: 14px;
  border-radius: 18px;
  border: 1px solid rgba(191, 205, 230, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.feedback-actions {
  flex-direction: column;
  justify-content: center;
}

.ghost-btn,
.quick-btn {
  min-height: 42px;
  border-radius: 14px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
}

.quick-btn.is-adopted {
  background: rgba(105, 215, 174, 0.14);
  color: #a8f1d4;
}

.quick-btn.is-completed {
  background: rgba(138, 163, 255, 0.16);
  color: #dce5ff;
}

.quick-btn.is-rejected {
  background: rgba(255, 143, 143, 0.12);
  color: #ffc0c0;
}

.quick-btn:disabled {
  cursor: wait;
  opacity: 0.7;
}

@media (max-width: 1280px) {
  .feedback-row {
    grid-template-columns: 1fr;
  }

  .feedback-actions {
    flex-direction: row;
  }
}

@media (max-width: 900px) {
  .feedback-meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .feedback-headline {
    flex-direction: column;
  }

  .feedback-meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
