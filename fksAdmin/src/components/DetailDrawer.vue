<script setup>
import StatusPill from './StatusPill.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  detail: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['close', 'copy'])
</script>

<template>
  <div v-if="visible" class="drawer-mask" @click.self="emit('close')">
    <aside class="drawer-panel">
      <header class="drawer-head">
        <div>
          <div class="drawer-kicker">{{ detail.eyebrow || 'DETAIL' }}</div>
          <h3 class="drawer-title">{{ detail.title || '查看详情' }}</h3>
          <p v-if="detail.subtitle" class="drawer-subtitle">{{ detail.subtitle }}</p>
        </div>
        <div class="drawer-head-actions">
          <StatusPill v-if="detail.statusLabel" :label="detail.statusLabel" :tone="detail.statusTone || 'neutral'" />
          <button class="close-btn" type="button" @click="emit('close')">关闭</button>
        </div>
      </header>

      <p v-if="detail.description" class="drawer-description">{{ detail.description }}</p>

      <div v-if="detail.highlights?.length" class="highlight-grid">
        <article v-for="item in detail.highlights" :key="item.label" class="highlight-card">
          <div class="highlight-label">{{ item.label }}</div>
          <div class="highlight-value">{{ item.value }}</div>
        </article>
      </div>

      <div v-if="detail.rows?.length" class="detail-list">
        <div v-for="row in detail.rows" :key="row.label" class="detail-row">
          <div class="detail-label">{{ row.label }}</div>
          <div class="detail-value-box">
            <div class="detail-value">{{ row.value }}</div>
            <button
              v-if="row.copyValue"
              class="copy-btn"
              type="button"
              @click="emit('copy', { label: row.label, value: row.copyValue })"
            >
              复制
            </button>
          </div>
        </div>
      </div>

      <div v-if="detail.imageUrl" class="proof-box">
        <div class="proof-head">
          <div>
            <div class="drawer-kicker">{{ detail.imageLabel || 'PROOF IMAGE' }}</div>
            <div class="proof-title">截图凭证</div>
          </div>
          <div class="proof-actions">
            <button class="copy-btn" type="button" @click="emit('copy', { label: '截图链接', value: detail.imageUrl })">复制链接</button>
            <a class="proof-link" :href="detail.imageUrl" target="_blank" rel="noreferrer">打开大图</a>
          </div>
        </div>
        <img class="proof-image" :src="detail.imageUrl" :alt="detail.imageLabel || '截图凭证'" />
      </div>

      <div v-if="detail.notes?.length" class="note-box">
        <div class="drawer-kicker">OPS NOTES</div>
        <ul>
          <li v-for="note in detail.notes" :key="note">{{ note }}</li>
        </ul>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  justify-content: flex-end;
  background: rgba(3, 9, 17, 0.62);
  backdrop-filter: blur(10px);
}

.drawer-panel {
  width: min(560px, 100%);
  height: 100vh;
  overflow-y: auto;
  padding: 24px;
  border-left: 1px solid rgba(191, 205, 230, 0.12);
  background:
    linear-gradient(180deg, rgba(11, 17, 28, 0.98), rgba(8, 13, 22, 1));
  box-shadow: -30px 0 60px rgba(2, 8, 16, 0.36);
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.drawer-head-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.drawer-kicker,
.highlight-label,
.detail-label {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(220, 228, 241, 0.5);
}

.drawer-title {
  margin: 12px 0 0;
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: 34px;
  line-height: 1.08;
  color: #fff8ec;
}

.drawer-subtitle,
.drawer-description {
  margin: 10px 0 0;
  color: rgba(229, 236, 248, 0.72);
  line-height: 1.8;
}

.drawer-description {
  margin-top: 16px;
}

.close-btn,
.copy-btn,
.proof-link {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
  font-size: 13px;
  font-weight: 700;
}

.close-btn,
.copy-btn {
  cursor: pointer;
}

.proof-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.highlight-grid {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.highlight-card,
.note-box {
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(191, 205, 230, 0.1);
  background: rgba(255, 255, 255, 0.04);
}

.highlight-value {
  margin-top: 10px;
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: 22px;
  font-weight: 800;
  color: #fff8ec;
}

.detail-list {
  margin-top: 20px;
  display: grid;
  gap: 10px;
}

.detail-row {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(191, 205, 230, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.detail-value-box {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-top: 8px;
}

.detail-value {
  flex: 1;
  color: #edf2fb;
  line-height: 1.75;
  word-break: break-word;
}

.proof-box {
  margin-top: 22px;
  padding: 16px;
  border-radius: 22px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background: rgba(255, 255, 255, 0.03);
}

.proof-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.proof-title {
  margin-top: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #fff8ec;
}

.proof-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.proof-image {
  width: 100%;
  margin-top: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
}

.note-box {
  margin-top: 20px;
}

.note-box ul {
  margin: 12px 0 0;
  padding-left: 18px;
  color: rgba(229, 236, 248, 0.78);
  line-height: 1.8;
}

@media (max-width: 760px) {
  .drawer-panel {
    padding: 18px;
  }

  .drawer-head,
  .proof-head,
  .detail-value-box {
    flex-direction: column;
  }

  .highlight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
