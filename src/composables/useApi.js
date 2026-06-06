import { ref } from 'vue'

export function useApi() {
  const loading = ref(false)
  const toast = ref('')

  async function api(path, options = {}) {
    const token = localStorage.getItem('ciye_token')
    const headers = { 'Content-Type': 'application/json', ...options.headers }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    const response = await fetch(path, { ...options, headers })
    const payload = await response.json()
    if (response.status === 401) {
      localStorage.removeItem('ciye_token')
      window.location.reload()
      throw new Error('登录已过期')
    }
    if (!response.ok) throw new Error(payload.error || '请求失败')
    return payload
  }

  function showToast(msg, duration = 3000) {
    toast.value = msg
    if (duration > 0) setTimeout(() => { toast.value = '' }, duration)
  }

  async function wrap(promise) {
    loading.value = true
    try {
      return await promise
    } catch (e) {
      showToast(e.message)
      throw e
    } finally {
      loading.value = false
    }
  }

  return { api, loading, toast, showToast, wrap }
}
