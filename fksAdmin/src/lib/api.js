import axios from 'axios'

export const ADMIN_TOKEN_KEY = 'liebaobao_admin_token'
export const ADMIN_USERNAME_KEY = 'liebaobao_admin_username'
export const ADMIN_EXPIRES_KEY = 'liebaobao_admin_expires'

export function getAdminSessionStorage() {
  return {
    token: localStorage.getItem(ADMIN_TOKEN_KEY) || '',
    username: localStorage.getItem(ADMIN_USERNAME_KEY) || '',
    expiresAt: Number(localStorage.getItem(ADMIN_EXPIRES_KEY) || 0),
  }
}

export function persistAdminSession({ token = '', username = '', expiresAt = 0 } = {}) {
  if (token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(ADMIN_TOKEN_KEY)
  }

  if (username) {
    localStorage.setItem(ADMIN_USERNAME_KEY, username)
  } else {
    localStorage.removeItem(ADMIN_USERNAME_KEY)
  }

  if (expiresAt) {
    localStorage.setItem(ADMIN_EXPIRES_KEY, String(expiresAt))
  } else {
    localStorage.removeItem(ADMIN_EXPIRES_KEY)
  }
}

export function clearAdminSessionStorage() {
  localStorage.removeItem(ADMIN_TOKEN_KEY)
  localStorage.removeItem(ADMIN_USERNAME_KEY)
  localStorage.removeItem(ADMIN_EXPIRES_KEY)
}

export const api = axios.create({
  baseURL: '',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const { token } = getAdminSessionStorage()
  if (token) {
    config.headers['x-admin-token'] = token
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    const payload = response.data || {}
    if (payload.ok === false) {
      const error = new Error(payload.message || '请求失败')
      error.status = response.status
      error.payload = payload
      return Promise.reject(error)
    }
    return payload.data || {}
  },
  (error) => {
    const status = error?.response?.status || 0
    const message = error?.response?.data?.message || error?.message || '网络异常，请稍后重试'

    if (status === 401 && typeof window !== 'undefined') {
      clearAdminSessionStorage()
      window.dispatchEvent(
        new CustomEvent('admin-auth-expired', {
          detail: { message },
        }),
      )
    }

    const wrapped = new Error(message)
    wrapped.status = status
    wrapped.payload = error?.response?.data || null
    return Promise.reject(wrapped)
  },
)
