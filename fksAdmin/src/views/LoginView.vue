<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const submitting = ref(false)
const errorMessage = ref('')
const form = reactive({
  username: auth.state.username || 'admin',
  password: '',
})

async function handleLogin() {
  const username = form.username.trim() || 'admin'
  const password = form.password

  if (!username || !password) {
    errorMessage.value = '请输入后台账号和密码'
    ElMessage.warning(errorMessage.value)
    return
  }

  submitting.value = true
  errorMessage.value = ''

  try {
    await auth.login({ username, password })
    form.password = ''
    ElMessage.success('登录成功')
    await router.replace({ name: 'dashboard' })
  } catch (error) {
    errorMessage.value = error.message || '后台账号或密码错误'
    ElMessage.error(errorMessage.value)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-shell">
    <el-card shadow="hover" class="login-card">
      <div class="panel-kicker">LIEBAOBAO ADMIN</div>
      <h1 class="panel-title">猎宝保后台管理系统</h1>
      <p class="panel-desc">请输入后台账号和密码</p>

      <form @submit.prevent="handleLogin">
        <el-form label-position="top" class="login-form">
          <el-form-item label="后台账号">
            <el-input
              v-model="form.username"
              placeholder="请输入后台账号"
              autocomplete="username"
              size="large"
              clearable
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item label="后台密码">
            <el-input
              v-model="form.password"
              placeholder="请输入后台密码"
              autocomplete="current-password"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon class="login-error" />
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            native-type="button"
            :loading="submitting || auth.state.checking"
            @click="handleLogin"
          >
            {{ submitting || auth.state.checking ? '登录中...' : '进入后台' }}
          </el-button>
        </el-form>
      </form>
    </el-card>
  </div>
</template>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: #f5f7fa;
}

.login-card {
  width: min(460px, calc(100vw - 32px));
  padding: 8px;
}

.panel-kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #909399;
}

.panel-title {
  margin: 12px 0 0;
  font-size: 36px;
  line-height: 1.15;
  font-weight: 700;
  color: #303133;
}

.panel-desc {
  margin: 12px 0 0;
  color: #606266;
  line-height: 1.8;
}

.login-form {
  margin-top: 24px;
}

.login-error {
  margin: 4px 0 18px;
}

.login-btn {
  width: 100%;
  margin-top: 10px;
  min-height: 50px;
}

@media (max-width: 768px) {
  .login-shell {
    padding: 18px;
  }

  .panel-title {
    font-size: 32px;
  }
}
</style>
