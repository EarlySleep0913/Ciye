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

    // 带重试的请求
    let lastError
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 15000) // 15s 超时

        const response = await fetch(path, {
          ...options,
          headers,
          signal: controller.signal,
        })
        clearTimeout(timeout)

        const payload = await response.json()
        if (response.status === 401) {
          localStorage.removeItem('ciye_token')
          window.location.reload()
          throw new Error('登录已过期')
        }
        if (!response.ok) throw new Error(payload.error || '请求失败')
        return payload
      } catch (e) {
        lastError = e
        // AbortError 或 TypeError (网络断开) 时重试
        if (e.name === 'AbortError' || e.message === 'Failed to fetch' || e.message.includes('NetworkError')) {
          if (attempt < 2) {
            await new Promise(r => setTimeout(r, 500 * (attempt + 1))) // 递增延迟
            continue
          }
        }
        // 其他错误直接抛出
        throw e
      }
    }
    throw lastError
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
