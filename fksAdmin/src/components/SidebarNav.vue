<script setup>
const props = defineProps({
  sections: {
    type: Array,
    default: () => [],
  },
  activeSection: {
    type: String,
    default: 'overview',
  },
  countMap: {
    type: Object,
    default: () => ({}),
  },
  username: {
    type: String,
    default: 'admin',
  },
  expireText: {
    type: String,
    default: '未同步',
  },
  lastUpdatedText: {
    type: String,
    default: '尚未同步',
  },
  pendingCount: {
    type: String,
    default: '0',
  },
})

const emit = defineEmits(['jump', 'logout'])
</script>

<template>
  <aside class="sidebar-shell">
    <section class="brand-card">
      <div class="brand-topline">
        <span class="brand-kicker">LIEBAOBAO OPS</span>
        <span class="brand-badge">经营驾驶舱</span>
      </div>
      <h1 class="brand-title">猎宝保</h1>
      <p class="brand-desc">
        用列表和节奏来管理订单，而不是靠到处翻卡片。当前工作流按“先处理、再归档、最后看走势”组织。
      </p>
      <div class="brand-signal-grid">
        <div class="signal-box">
          <div class="signal-label">待办压力</div>
          <div class="signal-value">{{ pendingCount }}</div>
        </div>
        <div class="signal-box">
          <div class="signal-label">最近同步</div>
          <div class="signal-desc">{{ lastUpdatedText }}</div>
        </div>
      </div>
    </section>

    <section class="session-card">
      <div class="session-head">
        <div>
          <div class="session-label">当前登录</div>
          <div class="session-user">{{ username }}</div>
        </div>
        <div class="session-status">{{ expireText }}</div>
      </div>
      <div class="session-tip">建议优先处理截图已上传、金额较大的担保和待回复反馈。</div>
      <button class="session-btn" type="button" @click="emit('logout')">退出后台</button>
    </section>

    <nav class="nav-panel">
      <div class="nav-heading">模块导航</div>
      <button
        v-for="section in sections"
        :key="section.id"
        :class="['nav-item', { 'is-active': activeSection === section.id }]"
        type="button"
        @click="emit('jump', section.id)"
      >
        <div class="nav-main">
          <div class="nav-title">{{ section.title }}</div>
          <div class="nav-desc">{{ section.desc }}</div>
        </div>
        <div class="nav-count">{{ countMap[section.id] ?? '--' }}</div>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar-shell {
  position: sticky;
  top: 20px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.brand-card,
.session-card,
.nav-panel {
  border-radius: 30px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  background:
    linear-gradient(180deg, rgba(14, 22, 34, 0.94), rgba(9, 14, 23, 0.98));
  box-shadow: 0 24px 44px rgba(2, 8, 16, 0.28);
}

.brand-card {
  padding: 22px;
  background:
    radial-gradient(circle at top right, rgba(214, 167, 99, 0.2), transparent 26%),
    linear-gradient(180deg, rgba(16, 25, 38, 0.96), rgba(9, 14, 23, 0.98));
}

.brand-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.brand-kicker,
.session-label,
.nav-heading,
.signal-label {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(220, 228, 241, 0.5);
}

.brand-badge,
.session-status {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(214, 167, 99, 0.2);
  background: rgba(214, 167, 99, 0.12);
  color: #ffe0ae;
  font-size: 12px;
  font-weight: 700;
}

.brand-title {
  margin: 16px 0 8px;
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: 42px;
  line-height: 1;
  color: #fff8ec;
}

.brand-desc,
.session-tip,
.nav-desc,
.signal-desc {
  color: rgba(229, 236, 248, 0.7);
  font-size: 14px;
  line-height: 1.8;
}

.brand-signal-grid {
  margin-top: 20px;
  display: grid;
  gap: 12px;
}

.signal-box {
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(191, 205, 230, 0.1);
}

.signal-value {
  margin-top: 10px;
  font-family: 'Bahnschrift', 'Segoe UI Variable Display', 'Microsoft YaHei UI', sans-serif;
  font-size: 34px;
  line-height: 1;
  font-weight: 800;
  color: #fff7e8;
}

.session-card {
  padding: 20px;
}

.session-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.session-user {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 800;
  color: #ffffff;
}

.session-tip {
  margin-top: 14px;
}

.session-btn {
  width: 100%;
  margin-top: 18px;
  min-height: 46px;
  border: 1px solid rgba(191, 205, 230, 0.12);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.05);
  color: #edf2fb;
  font-weight: 700;
  cursor: pointer;
}

.nav-panel {
  padding: 20px;
  display: grid;
  gap: 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
  min-height: 78px;
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid rgba(191, 205, 230, 0.1);
  background: rgba(255, 255, 255, 0.03);
  color: #ffffff;
  text-align: left;
  cursor: pointer;
}

.nav-item.is-active {
  background:
    linear-gradient(135deg, rgba(214, 167, 99, 0.18), rgba(116, 212, 208, 0.08));
  border-color: rgba(214, 167, 99, 0.24);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.nav-title {
  font-size: 15px;
  font-weight: 800;
  color: #fff8ec;
}

.nav-desc {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
}

.nav-count {
  min-width: 44px;
  padding: 9px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #edf2fb;
  font-size: 12px;
  font-weight: 800;
  text-align: center;
}

@media (max-width: 1280px) {
  .sidebar-shell {
    position: static;
  }
}
</style>
