<script setup>
import { ref, nextTick } from 'vue'
import { RotateCcw, Database, Image, Calendar, ChevronLeft, ChevronRight, Key, BookOpen, Loader2, Brain, Send, Bot, User } from 'lucide-vue-next'
import UserManager from './UserManager.vue'

const props = defineProps({
  health: Object,
  settings: Object,
  api: Function,
  showToast: Function,
  currentUser: Object,
})

const emit = defineEmits(['update-offset', 'reset-today', 'refresh'])

// Pexels key
const pexelsKey = ref('')
const savingKey = ref(false)

// AI settings
const aiUrl = ref('')
const aiKey = ref('')
const aiModel = ref('Pro/moonshotai/Kimi-K2.6')
const aiFormat = ref('openai')
const savingAi = ref(false)

// AI Assistant GIF size
const gifSize = ref(200)
function loadGifSize() {
  const s = localStorage.getItem('ai_gif_size')
  if (s) gifSize.value = Number(s) || 200
}
function saveGifSize() {
  localStorage.setItem('ai_gif_size', String(gifSize.value))
  window.dispatchEvent(new CustomEvent('ai-size-changed', { detail: gifSize.value }))
}

async function loadAiSettings() {
  try {
    const data = await props.api('/api/ai/settings')
    aiUrl.value = data.ai_api_url || ''
    aiKey.value = data.ai_api_key || ''
    aiModel.value = data.ai_model || 'Pro/moonshotai/Kimi-K2.6'
    aiFormat.value = data.ai_api_format || 'openai'
  } catch {}
}

async function saveAiSettings() {
  savingAi.value = true
  try {
    await props.api('/api/ai/settings', {
      method: 'POST',
      body: JSON.stringify({
        ai_api_url: aiUrl.value,
        ai_api_key: aiKey.value,
        ai_model: aiModel.value,
        ai_api_format: aiFormat.value,
      }),
    })
    props.showToast('AI 配置已保存')
  } catch (e) {
    props.showToast(e.message)
  } finally {
    savingAi.value = false
  }
}

// Load AI settings on mount
import { onMounted } from 'vue'
onMounted(() => {
  loadAiSettings()
  loadGifSize()
})

// AI Chat
const chatMessages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatBodyRef = ref(null)
const chatModel = ref('Pro/moonshotai/Kimi-K2.6')

async function sendChat() {
  const msg = chatInput.value.trim()
  if (!msg || chatLoading.value) return
  chatMessages.value.push({ role: 'user', content: msg })
  chatInput.value = ''
  chatLoading.value = true
  await nextTick()
  if (chatBodyRef.value) chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
  try {
    const data = await props.api('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message: msg, model: chatModel.value }),
      timeout: 120000,
    })
    chatMessages.value.push({ role: 'assistant', content: data.reply, model: data.model })
  } catch (e) {
    chatMessages.value.push({ role: 'error', content: e.message })
  } finally {
    chatLoading.value = false
    await nextTick()
    if (chatBodyRef.value) chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
  }
}

function clearChat() {
  chatMessages.value = []
}

// Reset book progress
const resetBookId = ref('')
const resetting = ref(false)

function adjustDate(delta) {
  emit('update-offset', (props.settings.date_offset || 0) + delta)
}

function resetDate() {
  emit('update-offset', 0)
}

async function savePexelsKey() {
  savingKey.value = true
  try {
    await props.api('/api/pexels-key', {
      method: 'POST',
      body: JSON.stringify({ api_key: pexelsKey.value }),
    })
    props.showToast('Pexels API Key 已保存')
    emit('refresh')
  } catch (e) {
    props.showToast(e.message)
  } finally {
    savingKey.value = false
  }
}

async function resetBookProgress() {
  if (!resetBookId.value) return
  resetting.value = true
  try {
    await props.api('/api/books/reset', {
      method: 'POST',
      body: JSON.stringify({ book_id: Number(resetBookId.value) }),
    })
    props.showToast('词书学习进度已重置')
    resetBookId.value = ''
    emit('refresh')
  } catch (e) {
    props.showToast(e.message)
  } finally {
    resetting.value = false
  }
}
</script>

<template>
  <section class="settings-page">
    <div class="section-heading">
      <p class="eyebrow">Settings</p>
      <h2>设置</h2>
    </div>

    <div class="settings-grid">
      <!-- 日期调整 -->
      <article v-spotlight class="setting-card">
        <h3><Calendar :size="18" /> 日期调整 <span class="badge">测试用</span></h3>
        <p class="setting-desc">模拟不同日期，方便测试复习调度</p>
        <div class="date-control">
          <div class="date-display">
            <div class="date-row">
              <span class="date-label">真实日期</span>
              <span class="date-value">{{ settings.real_date }}</span>
            </div>
            <div class="date-row virtual">
              <span class="date-label">模拟日期</span>
              <span class="date-value">{{ settings.virtual_date }}</span>
            </div>
          </div>
          <div class="date-buttons">
            <button class="quiet-btn compact" @click="adjustDate(-1)">
              <ChevronLeft :size="16" /> 前一天
            </button>
            <button class="quiet-btn compact" :class="{ disabled: !settings.date_offset }" @click="resetDate">
              回到今天
            </button>
            <button class="quiet-btn compact" @click="adjustDate(1)">
              后一天 <ChevronRight :size="16" />
            </button>
          </div>
          <p v-if="settings.date_offset" class="offset-hint">
            当前偏移：{{ settings.date_offset > 0 ? '+' : '' }}{{ settings.date_offset }} 天
          </p>
        </div>
      </article>

      <!-- 重置今日学习 -->
      <article v-spotlight class="setting-card">
        <h3><RotateCcw :size="18" /> 重置今日学习</h3>
        <p class="setting-desc">将今天学过的所有词重置为未学习状态，方便反复测试</p>
        <button class="primary-btn action-btn" @click="emit('reset-today')">
          <RotateCcw :size="16" />
          重置今日学习
        </button>
      </article>

      <!-- 重置词书进度 -->
      <article v-spotlight class="setting-card">
        <h3><BookOpen :size="18" /> 重置词书学习进度</h3>
        <p class="setting-desc">将某本词书的所有单词重置为未学习状态，已掌握程度归零</p>
        <div class="reset-book-row">
          <select v-model="resetBookId" class="book-select">
            <option value="" disabled>选择词书...</option>
            <option v-for="book in books" :key="book.id" :value="book.id">
              {{ book.name }} ({{ book.total }}词)
            </option>
          </select>
          <button
            class="primary-btn action-btn"
            :disabled="!resetBookId || resetting"
            @click="resetBookProgress"
          >
            <RotateCcw v-if="!resetting" :size="16" />
            <Loader2 v-else class="spin" :size="16" />
            重置进度
          </button>
        </div>
      </article>

      <!-- Pexels API Key -->
      <article v-spotlight class="setting-card">
        <h3><Key :size="18" /> Pexels API Key</h3>
        <p class="setting-desc">填写后可为单词配上辅助记忆图片。去 pexels.com/api 免费申请。</p>
        <div class="pexels-row">
          <input
            v-model="pexelsKey"
            type="password"
            class="pexels-input"
            placeholder="输入 Pexels API Key..."
          />
          <button class="primary-btn action-btn" :disabled="savingKey" @click="savePexelsKey">
            {{ savingKey ? '保存中...' : '保存' }}
          </button>
        </div>
        <p class="pexels-status">
          当前状态：
          <span :class="health?.pexels?.ok ? 'ok' : 'warn'">
            {{ health?.pexels?.ok ? '可用' : health?.pexels?.message || '检测中' }}
          </span>
        </p>
      </article>

      <!-- AI 配置 -->
      <article v-spotlight class="setting-card">
        <h3><Brain :size="18" /> AI 配置</h3>
        <p class="setting-desc">用于 AI 辅助导入词书。支持 OpenAI 兼容 API 和 Anthropic Messages API。</p>
        <div class="ai-form">
          <div class="ai-field">
            <label>API 格式</label>
            <select v-model="aiFormat" class="ai-input">
              <option value="openai">OpenAI 兼容</option>
              <option value="anthropic">Anthropic Messages</option>
            </select>
          </div>
          <div class="ai-field">
            <label>API URL</label>
            <input v-model="aiUrl" class="ai-input" :placeholder="aiFormat === 'anthropic' ? 'https://api.siliconflow.cn' : 'https://api.siliconflow.cn/v1/chat/completions'" />
          </div>
          <div class="ai-field">
            <label>API Key</label>
            <input v-model="aiKey" type="password" class="ai-input" placeholder="sk-xxxxxxxx" />
          </div>
          <div class="ai-field">
            <label>模型</label>
            <input v-model="aiModel" class="ai-input" :placeholder="aiFormat === 'anthropic' ? 'claude-sonnet-4-20250514' : 'Pro/moonshotai/Kimi-K2.6'" />
          </div>
          <button class="primary-btn action-btn" :disabled="savingAi" @click="saveAiSettings">
            {{ savingAi ? '保存中...' : '保存 AI 配置' }}
          </button>
        </div>
      </article>

      <!-- AI 对话测试 -->
      <article v-spotlight class="setting-card chat-card">
        <h3><Bot :size="18" /> AI 对话测试</h3>
        <p class="setting-desc">测试 AI API 连接是否正常。发送消息试试。</p>
        <div class="chat-container">
          <div ref="chatBodyRef" class="chat-body">
            <div v-if="chatMessages.length === 0" class="chat-empty">
              <Bot :size="32" />
              <p>发送一条消息来测试 API 连接</p>
            </div>
            <div v-for="(msg, i) in chatMessages" :key="i" class="chat-msg" :class="msg.role">
              <div class="chat-avatar">
                <User v-if="msg.role === 'user'" :size="14" />
                <Bot v-else :size="14" />
              </div>
              <div class="chat-bubble">
                <pre v-if="msg.role === 'error'" class="chat-error">{{ msg.content }}</pre>
                <pre v-else>{{ msg.content }}</pre>
              </div>
            </div>
            <div v-if="chatLoading" class="chat-msg assistant">
              <div class="chat-avatar"><Bot :size="14" /></div>
              <div class="chat-bubble typing">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </div>
          <div class="chat-model-row">
            <label>模型</label>
            <select v-model="chatModel" class="chat-model-select">
              <option value="Pro/moonshotai/Kimi-K2.6">Pro/moonshotai/Kimi-K2.6</option>
              <option value="deepseek-ai/DeepSeek-V4-Flash">deepseek-ai/DeepSeek-V4-Flash</option>
            </select>
            <span class="chat-model-hint">{{ chatModel === 'Pro/moonshotai/Kimi-K2.6' ? '文档解析专用' : '通用对话' }}</span>
          </div>
          <div class="chat-input-row">
            <input
              v-model="chatInput"
              class="chat-input"
              placeholder="输入消息..."
              @keydown.enter.prevent="sendChat"
              :disabled="chatLoading"
            />
            <button class="chat-send-btn" :disabled="!chatInput.trim() || chatLoading" @click="sendChat">
              <Send :size="16" />
            </button>
            <button v-if="chatMessages.length" class="chat-clear-btn" @click="clearChat" title="清空对话">
              <RotateCcw :size="14" />
            </button>
          </div>
        </div>
      </article>

      <!-- AI 助手大小 -->
      <article v-spotlight class="setting-card">
        <h3><Bot :size="18" /> AI 助手大小</h3>
        <p class="setting-desc">调整悬浮 AI 助手的显示大小</p>
        <div class="date-control">
          <div class="date-row">
            <span class="date-label">图标大小</span>
            <span class="date-value">{{ gifSize }}px</span>
          </div>
          <div class="limit-row">
            <input
              type="range"
              min="60"
              max="200"
              v-model.number="gifSize"
              @input="saveGifSize"
            />
          </div>
        </div>
      </article>

      <!-- 服务状态 -->
      <article class="setting-card status-card">
        <h3>服务状态</h3>
        <div class="status-list">
          <div class="status-item">
            <Database :size="18" />
            <div class="status-info">
              <span class="status-name">ECDICT 本地词典</span>
              <span class="status-value" :class="health?.ecdict ? 'ok' : 'warn'">
                {{ health?.ecdict ? '已就绪' : '未安装' }}
              </span>
            </div>
          </div>
          <div class="status-item">
            <Image :size="18" />
            <div class="status-info">
              <span class="status-name">Pexels 图片服务</span>
              <span class="status-value" :class="health?.pexels?.ok ? 'ok' : 'warn'">
                {{ health?.pexels?.ok ? '可用' : health?.pexels?.message || '检测中' }}
              </span>
            </div>
          </div>
        </div>
      </article>
    </div>

    <!-- User Management -->
    <UserManager
      :api="api"
      :show-toast="showToast"
      :current-user="currentUser"
    />
  </section>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.setting-card {
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 24px;
  transition: all 260ms cubic-bezier(0.16, 1, 0.3, 1);
}

.setting-card:hover {
  box-shadow: 0 32px 80px rgba(42, 30, 18, 0.18);
}

.setting-card h3 {
  font-size: 18px;
  font-family: var(--body-font);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.setting-desc {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 16px;
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--gold);
  color: white;
  border-radius: 10px;
  font-weight: 400;
}

.date-control {
  display: grid;
  gap: 14px;
}

.date-display {
  display: grid;
  gap: 8px;
}

.date-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.date-row.virtual {
  background: rgba(175, 135, 68, 0.1);
  border-color: var(--gold);
}

.date-label {
  font-size: 13px;
  color: var(--muted);
}

.date-value {
  font-family: var(--english-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
}

.date-buttons {
  display: flex;
  gap: 8px;
}

.date-buttons .quiet-btn {
  flex: 1;
  justify-content: center;
  font-size: 13px;
}

.date-buttons .quiet-btn.disabled {
  opacity: 0.4;
  pointer-events: none;
}

.offset-hint {
  text-align: center;
  font-size: 13px;
  color: var(--gold);
  margin: 0;
}

.limit-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.limit-row input[type="range"] {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(216, 203, 184, 0.5);
  border-radius: 3px;
  outline: none;
}

.limit-row input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--gold);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.action-btn {
  width: 100%;
  justify-content: center;
}

/* Reset book progress */
.reset-book-row {
  display: flex;
  gap: 10px;
}

.book-select {
  flex: 1;
  height: 42px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.54);
  color: var(--ink);
  font-family: var(--body-font);
  font-size: 14px;
  outline: none;
}

.book-select:focus {
  border-color: var(--gold);
}

.reset-book-row .action-btn {
  width: auto;
  min-width: 100px;
}

/* Pexels key */
.pexels-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.pexels-input {
  flex: 1;
  height: 42px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.54);
  color: var(--ink);
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  outline: none;
}

.pexels-input:focus {
  border-color: var(--gold);
}

.pexels-row .action-btn {
  width: auto;
  min-width: 80px;
}

.pexels-status {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
}

.pexels-status .ok { color: var(--sage); font-weight: 500; }
.pexels-status .warn { color: var(--gold); }

/* AI form */
.ai-form {
  display: grid;
  gap: 12px;
}

.ai-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ai-field label {
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ai-input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.54);
  color: var(--ink);
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  outline: none;
}

select.ai-input {
  font-family: var(--body-font);
  cursor: pointer;
}

.ai-input:focus {
  border-color: var(--gold);
  box-shadow: 0 0 0 3px rgba(175, 135, 68, 0.12);
}

/* Status card */
.status-card {
  grid-column: 1 / -1;
}

.status-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-name {
  font-size: 14px;
  font-weight: 500;
}

.status-value {
  font-size: 13px;
}

.status-value.ok { color: var(--sage); }
.status-value.warn { color: var(--gold); }

/* AI Chat */
.chat-card {
  grid-column: 1 / -1;
}

.chat-container {
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.4);
}

.chat-body {
  height: 360px;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--muted);
}

.chat-empty p {
  margin: 0;
  font-size: 13px;
}

.chat-msg {
  display: flex;
  gap: 10px;
  max-width: 85%;
  animation: chatMsgIn 300ms var(--ease-out);
}

@keyframes chatMsgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.chat-msg.error {
  align-self: stretch;
  max-width: 100%;
}

.chat-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border: 1px solid var(--line);
  background: var(--paper-2);
  color: var(--muted);
}

.chat-msg.user .chat-avatar {
  background: rgba(34, 59, 50, 0.1);
  color: var(--ink);
}

.chat-msg.error .chat-avatar {
  background: rgba(139, 58, 58, 0.1);
  color: var(--red);
}

.chat-bubble {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid var(--line);
  background: var(--paper-2);
  overflow-x: auto;
}

.chat-bubble pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--body-font);
  font-size: 14px;
  line-height: 1.6;
}

.chat-msg.user .chat-bubble {
  background: rgba(34, 59, 50, 0.08);
  border-color: rgba(34, 59, 50, 0.15);
}

.chat-msg.error .chat-bubble {
  background: rgba(139, 58, 58, 0.06);
  border-color: rgba(139, 58, 58, 0.2);
  color: var(--red);
  width: 100%;
}

.chat-error {
  margin: 0;
  font-size: 13px;
  font-family: Consolas, "Courier New", monospace;
}

/* Typing indicator */
.typing {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 12px 16px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--muted);
  animation: dotPulse 1.2s ease-in-out infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

.chat-model-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-top: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.4);
}

.chat-model-row label {
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.chat-model-select {
  flex: 1;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.6);
  color: var(--ink);
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  outline: none;
  cursor: pointer;
}

.chat-model-select:focus {
  border-color: var(--gold);
}

.chat-model-hint {
  font-size: 11px;
  color: var(--gold);
  flex-shrink: 0;
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.6);
}

.chat-input {
  flex: 1;
  height: 40px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--ink);
  font-family: var(--body-font);
  font-size: 14px;
  outline: none;
}

.chat-input:focus {
  border-color: var(--gold);
}

.chat-input:disabled {
  opacity: 0.6;
}

.chat-send-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--ink);
  border-radius: 6px;
  background: var(--ink);
  color: #fff8e8;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 160ms ease;
}

.chat-send-btn:hover:not(:disabled) {
  background: #1a2f28;
  transform: translateY(-1px);
}

.chat-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.chat-clear-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--muted);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 160ms ease;
}

.chat-clear-btn:hover {
  color: var(--red);
  border-color: var(--red);
}

@media (max-width: 720px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  .status-list {
    grid-template-columns: 1fr;
  }
}
</style>
