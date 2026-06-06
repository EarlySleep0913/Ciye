<script setup>
import { ref } from 'vue'
import { LogIn, UserPlus, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  api: Function,
  showToast: Function,
})

const emit = defineEmits(['login'])

const mode = ref('login') // 'login' or 'register'
const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value.trim() || !password.value.trim()) {
    props.showToast('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const endpoint = mode.value === 'login' ? '/api/auth/login' : '/api/auth/register'
    const data = await props.api(endpoint, {
      method: 'POST',
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value.trim(),
      }),
    })
    localStorage.setItem('ciye_token', data.token)
    emit('login', data.user)
  } catch (e) {
    props.showToast(e.message)
  } finally {
    loading.value = false
  }
}

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="card-corner" />
      <div class="card-inner">
        <div class="brand">
          <div class="brand-icon">📖</div>
          <h1 class="brand-title">Ciye 词页</h1>
          <p class="brand-sub">把单词背成一页会留下痕迹的书。</p>
        </div>

        <form class="login-form" @submit.prevent="submit">
          <div class="form-group">
            <label>用户名</label>
            <input
              v-model="username"
              type="text"
              placeholder="输入用户名"
              autocomplete="username"
              autofocus
            />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input
              v-model="password"
              type="password"
              placeholder="输入密码"
              autocomplete="current-password"
            />
          </div>
          <button class="submit-btn" type="submit" :disabled="loading">
            <Loader2 v-if="loading" class="spin" :size="18" />
            <template v-else>
              <LogIn v-if="mode === 'login'" :size="18" />
              <UserPlus v-else :size="18" />
              {{ mode === 'login' ? '登 录' : '注 册' }}
            </template>
          </button>
        </form>

        <div class="toggle-mode">
          <template v-if="mode === 'login'">
            还没有账号？<button @click="toggleMode">立即注册</button>
          </template>
          <template v-else>
            已有账号？<button @click="toggleMode">返回登录</button>
          </template>
        </div>
      </div>
    </div>
    <div class="login-footer">
      <span>词页 CiYe — A private vocabulary room</span>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 20% 8%, rgba(175, 135, 68, 0.18), transparent 30%),
    linear-gradient(135deg, #efe7d8 0%, #f4efe4 42%, #e7ddce 100%);
  padding: 20px;
}

.login-card {
  position: relative;
  width: min(420px, 100%);
  background: rgba(255, 249, 236, 0.92);
  border: 1px solid #d8cbb8;
  box-shadow: 0 24px 70px rgba(42, 30, 18, 0.14);
  overflow: hidden;
}

.card-corner {
  position: absolute;
  top: 0;
  right: 0;
  width: 76px;
  height: 76px;
  background: linear-gradient(135deg, transparent 50%, rgba(175, 135, 68, 0.2) 51%);
  pointer-events: none;
}

.card-inner {
  position: relative;
  padding: 48px 40px 36px;
}

.brand {
  text-align: center;
  margin-bottom: 36px;
}

.brand-icon {
  font-size: 48px;
  margin-bottom: 12px;
  filter: drop-shadow(0 4px 8px rgba(42, 30, 18, 0.15));
}

.brand-title {
  font-family: "ZCOOL XiaoWei", "STKaiti", serif;
  font-size: 36px;
  font-weight: 400;
  color: #223b32;
  margin: 0 0 8px;
  letter-spacing: 0.08em;
}

.brand-sub {
  font-family: "Noto Serif SC", serif;
  font-size: 14px;
  color: #756b5d;
  margin: 0;
  line-height: 1.6;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  color: #756b5d;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: "Noto Serif SC", serif;
}

.form-group input {
  height: 48px;
  padding: 0 16px;
  border: 1px solid #d8cbb8;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.6);
  color: #223b32;
  font-family: "Noto Serif SC", serif;
  font-size: 15px;
  outline: none;
  transition: border-color 200ms ease;
}

.form-group input:focus {
  border-color: #af8744;
  background: rgba(255, 255, 255, 0.85);
}

.form-group input::placeholder {
  color: #b5a997;
}

.submit-btn {
  height: 50px;
  border: 1px solid #223b32;
  border-radius: 6px;
  background: #223b32;
  color: #fff8e8;
  font-family: "Noto Serif SC", serif;
  font-size: 16px;
  letter-spacing: 0.15em;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 200ms ease;
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  background: #1a2f28;
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(34, 59, 50, 0.2);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-mode {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #756b5d;
  font-family: "Noto Serif SC", serif;
}

.toggle-mode button {
  border: none;
  background: none;
  color: #8b3a3a;
  font-family: inherit;
  font-size: inherit;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.toggle-mode button:hover {
  color: #6b2a2a;
}

.login-footer {
  margin-top: 32px;
  font-size: 12px;
  color: rgba(117, 107, 93, 0.6);
  font-family: "Cormorant Garamond", serif;
  letter-spacing: 0.1em;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spin {
  animation: spin 900ms linear infinite;
}
</style>
