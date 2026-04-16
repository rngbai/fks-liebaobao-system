<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: '',
  },
  value: {
    type: String,
    default: '0',
  },
  hint: {
    type: String,
    default: '',
  },
  tone: {
    type: String,
    default: 'default',
  },
})

const toneClass = computed(() => `is-${props.tone || 'default'}`)
</script>

<template>
  <article :class="['stat-card', toneClass]">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
    <div class="stat-hint">{{ hint }}</div>
  </article>
</template>

<style scoped>
.stat-card {
  position: relative;
  overflow: hidden;
  padding: 22px;
  border-radius: 26px;
  border: 1px solid rgba(188, 201, 224, 0.12);
  background:
    linear-gradient(180deg, rgba(18, 29, 46, 0.95), rgba(9, 15, 26, 0.98));
  box-shadow: 0 20px 36px rgba(2, 9, 18, 0.24);
}

.stat-card::after {
  content: '';
  position: absolute;
  inset: auto -10% -48% auto;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  filter: blur(14px);
}

.stat-label {
  position: relative;
  z-index: 1;
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(228, 235, 247, 0.52);
}

.stat-value {
  position: relative;
  z-index: 1;
  margin-top: 20px;
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: clamp(32px, 3.4vw, 44px);
  line-height: 1;
  font-weight: 800;
  color: #fff9ef;
}

.stat-hint {
  position: relative;
  z-index: 1;
  margin-top: 14px;
  color: rgba(226, 233, 246, 0.72);
  font-size: 13px;
  line-height: 1.75;
}

.is-gold {
  background:
    radial-gradient(circle at top right, rgba(214, 167, 99, 0.24), transparent 26%),
    linear-gradient(180deg, rgba(24, 30, 41, 0.98), rgba(12, 16, 25, 0.98));
  border-color: rgba(214, 167, 99, 0.22);
}

.is-green {
  background:
    radial-gradient(circle at top right, rgba(105, 215, 174, 0.18), transparent 24%),
    linear-gradient(180deg, rgba(16, 28, 31, 0.98), rgba(8, 17, 20, 0.98));
  border-color: rgba(105, 215, 174, 0.22);
}

.is-blue {
  background:
    radial-gradient(circle at top right, rgba(138, 163, 255, 0.2), transparent 24%),
    linear-gradient(180deg, rgba(17, 26, 42, 0.98), rgba(8, 14, 25, 0.98));
  border-color: rgba(138, 163, 255, 0.24);
}

.is-red {
  background:
    radial-gradient(circle at top right, rgba(255, 143, 143, 0.16), transparent 24%),
    linear-gradient(180deg, rgba(34, 20, 25, 0.98), rgba(18, 11, 15, 0.98));
  border-color: rgba(255, 143, 143, 0.2);
}
</style>
