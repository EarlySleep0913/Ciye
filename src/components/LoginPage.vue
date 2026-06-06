<script setup>
import { ref } from 'vue'
import { LogIn, UserPlus, Loader2 } from 'lucide-vue-next'
import iconUrl from '../assets/icon.png'

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
    <!-- B. 飘落的树叶/书页 -->
    <div class="falling-leaves">
      <div class="leaf" v-for="i in 8" :key="i" :style="{ '--delay': i * 2.5 + 's', '--x': (i * 13 % 100) + '%' }"></div>
    </div>

    <div class="login-card">
      <!-- A. 纸张卷角 -->
      <div class="card-corner">
        <div class="corner-flap"></div>
      </div>
      <div class="card-inner">
        <div class="brand">
          <img class="brand-icon" :src="iconUrl" alt="Ciye" />
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
  position: relative;
  overflow: hidden;
}

/* ── B. 飘落树叶 ── */
.falling-leaves {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.leaf {
  position: absolute;
  top: -40px;
  left: var(--x);
  width: 12px;
  height: 12px;
  background: rgba(175, 135, 68, 0.15);
  border-radius: 0 50% 50% 50%;
  transform: rotate(45deg);
  animation: leafFall 12s var(--delay, 0s) linear infinite;
}

.leaf:nth-child(odd) {
  width: 8px;
  height: 8px;
  background: rgba(111, 134, 111, 0.12);
}

@keyframes leafFall {
  0% { transform: translateY(-20px) rotate(45deg); opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { transform: translateY(100vh) rotate(405deg); opacity: 0; }
}

.login-card {
  position: relative;
  z-index: 1;
  width: min(420px, 100%);
  background:
    linear-gradient(rgba(34, 59, 50, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 59, 50, 0.018) 1px, transparent 1px),
    rgba(255, 249, 236, 0.95);
  background-size: 100% 28px, 28px 100%, 100% 100%;
  border: 1px solid #d8cbb8;
  box-shadow:
    0 24px 70px rgba(42, 30, 18, 0.14),
    0 1px 3px rgba(42, 30, 18, 0.06);
}

/* ── A. 纸张右下角卷角 ── */
.card-corner {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 60px;
  height: 60px;
  overflow: hidden;
  pointer-events: none;
  z-index: 2;
}

.corner-flap {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background:
    linear-gradient(315deg,
      #e8dfd0 0%,
      #f4efe4 30%,
      rgba(216, 203, 184, 0.9) 48%,
      transparent 50%
    );
  transform-origin: bottom right;
  transition: transform 500ms cubic-bezier(0.4, 0, 0.2, 1);
  clip-path: polygon(100% 0, 100% 100%, 0 100%);
}

.corner-flap::after {
  content: "";
  position: absolute;
  bottom: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, transparent 45%, rgba(175, 135, 68, 0.12) 50%, rgba(216, 203, 184, 0.6) 55%);
  clip-path: polygon(100% 0, 100% 100%, 0 100%);
}

.login-card:hover .corner-flap {
  transform: rotate(20deg) translateX(-6px) translateY(6px);
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
  width: 72px;
  height: 72px;
  margin-bottom: 12px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 4px 16px rgba(42, 30, 18, 0.15);
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
  box-shadow: 0 0 0 3px rgba(175, 135, 68, 0.12);
}

.form-group input::placeholder {
  color: #b5a997;
}

/* ── D. 按钮按压效果 ── */
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
  position: relative;
  overflow: hidden;
  margin-top: 8px;
}

.submit-btn::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, transparent 50%, rgba(0,0,0,0.1) 100%);
  pointer-events: none;
}

.submit-btn:active:not(:disabled) {
  transform: translateY(2px);
  box-shadow: inset 0 3px 6px rgba(0, 0, 0, 0.25);
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
