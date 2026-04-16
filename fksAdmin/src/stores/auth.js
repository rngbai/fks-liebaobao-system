import { computed, reactive } from 'vue'
import {
  api,
  clearAdminSessionStorage,
  getAdminSessionStorage,
  persistAdminSession,
} from '../lib/api'

const session = getAdminSessionStorage()

const state = reactive({
  token: session.token,
  username: session.username || 'admin',
  expiresAt: Number(session.expiresAt || 0),
  checking: false,
  message: '',
})

function saveState() {
  persistAdminSession({
    token: state.token,
    username: state.username,
    expiresAt: state.expiresAt,
  })
}

function applySession(payload = {}, fallbackUsername = 'admin') {
  state.token = payload.token || state.token || ''
  state.username = payload.username || fallbackUsername || 'admin'
  state.expiresAt = Number(payload.expiresAt || 0)
  state.message = ''
  saveState()
}

function clearSession(message = '') {
  state.token = ''
  state.username = 'admin'
  state.expiresAt = 0
  state.message = message
  clearAdminSessionStorage()
}

async function authCheck() {
  if (!state.token) {
    clearSession('请先登录后台')
    return false
  }

  state.checking = true
  try {
    const data = await api.get('/api/manage/auth-check')
    applySession({
      token: state.token,
      username: data.username || state.username,
      expiresAt: data.expiresAt || state.expiresAt,
    })
    return true
  } catch (error) {
    clearSession(error.message || '后台未登录或登录已失效')
    return false
  } finally {
    state.checking = false
  }
}

async function login({ username, password }) {
  state.checking = true
  try {
    const data = await api.post('/api/manage/login', { username, password })
    applySession(data, username)
    return data
  } finally {
    state.checking = false
  }
}

async function logout() {
  try {
    if (state.token) {
      await api.post('/api/manage/logout', {})
    }
  } catch {
    // 忽略退出接口失败，始终清理本地会话
  }
  clearSession('已退出后台')
}

export function getStoredToken() {
  return getAdminSessionStorage().token
}

export function useAuthStore() {
  return {
    state,
    isAuthed: computed(() => !!state.token),
    authCheck,
    login,
    logout,
    clearSession,
  }
}
