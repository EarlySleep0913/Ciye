<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useApi } from './composables/useApi.js'
import { useAudio } from './composables/useAudio.js'
import NavRail from './components/NavRail.vue'
import StudyCard from './components/StudyCard.vue'
import BookShelf from './components/BookShelf.vue'
import StatsPanel from './components/StatsPanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import LookupPopover from './components/LookupPopover.vue'
import LoginPage from './components/LoginPage.vue'
import WrongWords from './components/WrongWords.vue'
import Favorites from './components/Favorites.vue'
import SpellingTest from './components/SpellingTest.vue'
import EbbinghausPanel from './components/EbbinghausPanel.vue'
import AiAssistant from './components/AiAssistant.vue'
import { Loader2 } from 'lucide-vue-next'

const { api, loading, toast, showToast } = useApi()
const { speak, speakPdfWord, pronouncingId } = useAudio(api)

const currentUser = ref(null)
const authChecked = ref(false)

const health = ref(null)
const books = ref([])
const stats = ref(null)
const settings = ref({ daily_new_limit: 15, date_offset: 0, real_date: '', virtual_date: '' })
const todayData = ref({ reviews: [], new_words: [] })
const lookup = ref(null)
const lookupLoading = ref(false)
const activeSection = ref('study')

const queue = computed(() => [
  ...(todayData.value.reviews || []).map(item => reactive({ ...item, taskType: 'review' })),
  ...(todayData.value.new_words || []).map(item => reactive({ ...item, taskType: 'new' })),
])

async function checkAuth() {
  const token = localStorage.getItem('ciye_token')
  if (!token) {
    authChecked.value = true
    return
  }
  try {
    const user = await api('/api/auth/me')
    currentUser.value = user
    await refreshAll()
  } catch {
    localStorage.removeItem('ciye_token')
  } finally {
    authChecked.value = true
  }
}

async function refreshAll() {
  loading.value = true
  try {
    const [h, b, s, t, st] = await Promise.all([
      api('/api/health'),
      api('/api/books'),
      api('/api/settings'),
      api('/api/today'),
      api('/api/stats'),
    ])
    health.value = h
    books.value = b.books
    settings.value = s
    todayData.value = t
    stats.value = st
  } catch (e) {
    showToast(e.message)
  } finally {
    loading.value = false
  }
}

async function updateOffset(offset) {
  try {
    const result = await api('/api/settings', {
      method: 'POST',
      body: JSON.stringify({ date_offset: offset }),
    })
    settings.value = { ...settings.value, ...result }
    todayData.value = await api('/api/today')
    showToast(`模拟日期：${result.virtual_date}`)
  } catch (e) {
    showToast(e.message)
  }
}

async function resetToday() {
  try {
    await api('/api/reset-today', { method: 'POST' })
    await refreshAll()
    showToast('今日学习已重置')
  } catch (e) {
    showToast(e.message)
  }
}

async function lookupWord(word) {
  lookupLoading.value = true
  lookup.value = null
  try {
    lookup.value = await api(`/api/lookup?word=${encodeURIComponent(word)}`)
  } catch (e) {
    showToast(e.message)
  } finally {
    lookupLoading.value = false
  }
}

function closeLookup() {
  lookup.value = null
}

function onLogin(user) {
  currentUser.value = user
  refreshAll()
}

function onLogout() {
  localStorage.removeItem('ciye_token')
  currentUser.value = null
  activeSection.value = 'study'
}

function openAiAssistant() {
  window.dispatchEvent(new CustomEvent('ai-reset-position'))
}

onMounted(checkAuth)
</script>

<template>
  <!-- Loading auth state -->
  <div v-if="!authChecked" class="auth-loading">
    <Loader2 class="spin" :size="32" />
  </div>

  <!-- Not logged in -->
  <LoginPage
    v-else-if="!currentUser"
    :api="api"
    :show-toast="showToast"
    @login="onLogin"
  />

  <!-- Logged in -->
  <main v-else class="app-shell">
    <NavRail
      :active="activeSection"
      :role="currentUser.role"
      @navigate="activeSection = $event"
      @logout="onLogout"
      @ai-assistant="openAiAssistant"
    />

    <section class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">A private vocabulary room</p>
          <h1>把单词背成一页会留下痕迹的书。</h1>
        </div>
        <Loader2 v-if="loading" class="spin" :size="18" />
      </header>

      <StudyCard
        v-show="activeSection === 'study'"
        :queue="queue"
        :loading="loading"
        :health="health"
        :today-data="todayData"
        :api="api"
        :speak="speak"
        :show-toast="showToast"
        :lookup-word="lookupWord"
        @refresh="refreshAll"
        @update-stats="stats = $event"
        @navigate="activeSection = $event"
      />

      <BookShelf
        v-show="activeSection === 'shelf'"
        :books="books"
        :settings="settings"
        :api="api"
        :show-toast="showToast"
        :speak="speak"
        @refresh="refreshAll"
      />

      <StatsPanel
        v-show="activeSection === 'stats'"
        :stats="stats"
        :api="api"
      />

      <WrongWords
        v-show="activeSection === 'wrong'"
        :api="api"
        :speak="speak"
        :show-toast="showToast"
        :lookup-word="lookupWord"
      />

      <Favorites
        v-show="activeSection === 'fav'"
        :api="api"
        :speak="speak"
        :show-toast="showToast"
        :lookup-word="lookupWord"
      />

      <SpellingTest
        v-show="activeSection === 'test'"
        :api="api"
        :speak="speak"
        :show-toast="showToast"
      />

      <EbbinghausPanel
        v-show="activeSection === 'ebbinghaus'"
        :api="api"
        :speak="speak"
        :show-toast="showToast"
        :lookup-word="lookupWord"
      />

      <SettingsPanel
        v-if="currentUser.role === 'admin'"
        v-show="activeSection === 'settings'"
        :health="health"
        :settings="settings"
        :api="api"
        :show-toast="showToast"
        :current-user="currentUser"
        @update-offset="updateOffset"
        @reset-today="resetToday"
        @refresh="refreshAll"
      />
    </section>

    <LookupPopover
      :lookup="lookup"
      :loading="lookupLoading"
      :speak="speak"
      @close="closeLookup"
    />

    <AiAssistant :api="api" :show-toast="showToast" />

    <button v-if="toast" class="toast" @click="toast = ''">{{ toast }}</button>
  </main>
</template>

<style scoped>
.auth-loading {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 20% 8%, rgba(175, 135, 68, 0.18), transparent 30%),
    radial-gradient(circle at 80% 90%, rgba(111, 134, 111, 0.08), transparent 25%),
    linear-gradient(135deg, #efe7d8 0%, #f4efe4 42%, #e7ddce 100%);
}

.auth-loading .spin {
  animation: spin 1s var(--ease-out) infinite;
  color: var(--muted);
}

/* 工作区入场动画 */
.workspace {
  animation: workspaceIn 500ms var(--ease-out);
}

@keyframes workspaceIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Topbar 入场 */
.topbar {
  animation: topbarIn 600ms var(--ease-out) 100ms both;
}

@keyframes topbarIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
