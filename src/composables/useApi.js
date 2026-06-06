import { ref } from 'vue'

export function useApi() {
  const loading = ref(false)
  const toast = ref('')

  async function api(path, options = {}) {
    const response = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
    const payload = await response.json()
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
