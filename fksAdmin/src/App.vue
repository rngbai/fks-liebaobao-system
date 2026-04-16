<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const booting = ref(true)

const handleAuthExpired = (event) => {
  const message = event?.detail?.message || '后台登录已失效，请重新登录'
  auth.clearSession(message)
  if (route.name !== 'login') {
    router.replace({ name: 'login' })
  }
}

onMounted(async () => {
  window.addEventListener('admin-auth-expired', handleAuthExpired)

  if (auth.state.token) {
    const ok = await auth.authCheck()
    if (ok && route.name === 'login') {
      await router.replace({ name: 'dashboard' })
    }
    if (!ok && route.meta.requiresAuth) {
      await router.replace({ name: 'login' })
    }
  } else if (route.meta.requiresAuth) {
    await router.replace({ name: 'login' })
  }

  booting.value = false
})

onBeforeUnmount(() => {
  window.removeEventListener('admin-auth-expired', handleAuthExpired)
})
</script>

<template>
  <div v-if="booting" class="boot-screen">
    <div class="boot-card">
      <div class="boot-kicker">LIEBAOBAO CONTROL GRID</div>
      <h1>猎宝保后台启动中</h1>
      <p>正在校验登录态，并加载经营驾驶舱、工作队列与运营档案面板。</p>
    </div>
  </div>
  <RouterView v-else />
</template>
