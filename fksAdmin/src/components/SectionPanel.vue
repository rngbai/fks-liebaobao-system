<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    default: '',
  },
  desc: {
    type: String,
    default: '',
  },
  tag: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <section class="section-panel">
    <header class="section-head">
      <div class="section-main">
        <div class="section-eyebrow">{{ eyebrow }}</div>
        <h2 class="section-title">{{ title }}</h2>
        <p class="section-desc">{{ desc }}</p>
      </div>
      <div class="section-side">
        <slot name="actions" />
        <span v-if="tag" class="section-tag">{{ tag }}</span>
      </div>
    </header>
    <div class="section-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.section-panel {
  padding: 24px;
  border-radius: 30px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background:
    linear-gradient(180deg, rgba(15, 23, 35, 0.95), rgba(9, 14, 24, 0.99));
  box-shadow: 0 24px 44px rgba(2, 8, 16, 0.26);
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.section-main {
  min-width: 0;
}

.section-eyebrow {
  font-size: 12px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(224, 232, 246, 0.5);
}

.section-title {
  margin: 12px 0 0;
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: 30px;
  line-height: 1.1;
  color: #fff8ec;
}

.section-desc {
  margin: 10px 0 0;
  max-width: 780px;
  color: rgba(229, 236, 248, 0.72);
  font-size: 14px;
  line-height: 1.8;
}

.section-side {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.section-tag {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #edf2fb;
  font-size: 12px;
  font-weight: 700;
}

.section-body {
  min-width: 0;
}

@media (max-width: 960px) {
  .section-head {
    flex-direction: column;
  }

  .section-side {
    justify-content: flex-start;
    width: 100%;
  }
}
</style>
