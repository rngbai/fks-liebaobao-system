<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: '状态',
  },
  tone: {
    type: String,
    default: 'neutral',
  },
})

const toneClass = computed(() => `is-${props.tone || 'neutral'}`)
</script>

<template>
  <span :class="['status-pill', toneClass]">{{ label }}</span>
</template>

<style scoped>
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  min-width: 86px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(186, 199, 221, 0.14);
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.is-neutral {
  border-color: rgba(186, 199, 221, 0.14);
  color: rgba(237, 242, 251, 0.84);
}

.is-warning {
  border-color: rgba(240, 195, 109, 0.26);
  background: rgba(240, 195, 109, 0.14);
  color: #ffdea3;
}

.is-success {
  border-color: rgba(105, 215, 174, 0.28);
  background: rgba(105, 215, 174, 0.15);
  color: #acf2d5;
}

.is-danger {
  border-color: rgba(255, 143, 143, 0.24);
  background: rgba(255, 143, 143, 0.12);
  color: #ffc0c0;
}

.is-info {
  border-color: rgba(138, 163, 255, 0.26);
  background: rgba(138, 163, 255, 0.14);
  color: #d6e0ff;
}
</style>
