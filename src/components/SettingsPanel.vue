<script setup>
import { ref } from 'vue'
import { RotateCcw, Database, Image, Calendar, ChevronLeft, ChevronRight, Key, BookOpen, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  health: Object,
  settings: Object,
  books: Array,
  api: Function,
  showToast: Function,
})

const emit = defineEmits(['update-offset', 'reset-today', 'refresh'])

// Pexels key
const pexelsKey = ref('')
const savingKey = ref(false)

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
      <article class="setting-card">
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
      <article class="setting-card">
        <h3><RotateCcw :size="18" /> 重置今日学习</h3>
        <p class="setting-desc">将今天学过的所有词重置为未学习状态，方便反复测试</p>
        <button class="primary-btn action-btn" @click="emit('reset-today')">
          <RotateCcw :size="16" />
          重置今日学习
        </button>
      </article>

      <!-- 重置词书进度 -->
      <article class="setting-card">
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
      <article class="setting-card">
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

@media (max-width: 720px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  .status-list {
    grid-template-columns: 1fr;
  }
}
</style>
