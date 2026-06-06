<script setup>
import { ref, computed, watch } from 'vue'
import {
  ChevronRight, Heart, Loader2, Star, Volume2,
} from 'lucide-vue-next'

const props = defineProps({
  queue: Array,
  loading: Boolean,
  health: Object,
  todayData: Object,
  api: Function,
  speak: Function,
  showToast: Function,
  lookupWord: Function,
})

const emit = defineEmits(['refresh', 'update-stats', 'navigate'])

const feedbacks = [
  { action: 'forgot', label: '不认识', hint: '明天复习', tone: 'danger' },
  { action: 'vague', label: '模糊', hint: '2 天后复习', tone: 'warn' },
  { action: 'known', label: '认识', hint: '4 天后复习', tone: 'ok' },
  { action: 'easy', label: '很熟', hint: '7 天后复习', tone: 'calm' },
]

const index = ref(0)
const revealed = ref(false)

const current = computed(() => props.queue[index.value])
const learnedCount = computed(() => index.value)
const totalCount = computed(() => props.queue.length)
const finished = computed(() => totalCount.value > 0 && index.value >= totalCount.value)
const reviewCount = computed(() => props.todayData?.reviews?.length || 0)
const newCount = computed(() => props.todayData?.new_words?.length || 0)

// When queue updates, skip past words already studied today (marked by backend)
watch(() => props.queue, (q) => {
  let i = 0
  while (i < q.length && q[i].studied_today) {
    i++
  }
  index.value = i
  revealed.value = false
}, { deep: true })

watch(() => current.value?.id, async (id) => {
  if (!id || !current.value) return
  if (current.value.image_url) return
  const word = current.value.word
  try {
    const data = await props.api(`/api/lookup?word=${encodeURIComponent(word)}`)
    if (current.value?.id === id) Object.assign(current.value, data)
  } catch {}
  // If still no image, retry after 3s (background enrichment may still be running)
  if (current.value?.id === id && !current.value.image_url) {
    await new Promise(r => setTimeout(r, 3000))
    if (current.value?.id !== id) return
    try {
      const data = await props.api(`/api/lookup?word=${encodeURIComponent(word)}`)
      if (current.value?.id === id) Object.assign(current.value, data)
    } catch {}
  }
})

function exampleTokens(example) {
  return String(example || '').split(/(\b[A-Za-z][A-Za-z'-]*\b)/g)
}

async function submitFeedback(action) {
  if (!current.value) return
  try {
    await props.api('/api/progress', {
      method: 'POST',
      body: JSON.stringify({ word_id: current.value.id, action }),
    })
    // Mark as studied locally for immediate UI feedback
    current.value.studied_today = true
    revealed.value = false
    index.value++
    const s = await props.api('/api/stats')
    emit('update-stats', s)
  } catch (e) {
    props.showToast(e.message)
  }
}

async function toggleFavorite() {
  if (!current.value) return
  const wordId = current.value.id
  const favorite = !current.value.is_favorite
  // Update queue item directly for reactivity
  const item = props.queue[index.value]
  if (item) item.is_favorite = favorite ? 1 : 0
  try {
    await props.api('/api/favorite', {
      method: 'POST',
      body: JSON.stringify({ word_id: wordId, favorite }),
    })
  } catch (e) {
    // Revert on error
    if (item) item.is_favorite = favorite ? 0 : 1
    props.showToast(e.message)
  }
}
</script>

<template>
  <section id="study" class="study-grid">
    <article class="word-stage">
      <div class="paper-corner" />
      <div class="task-strip">
        <span>{{ current?.taskType === 'review' ? '今日复习' : '今日新词' }}</span>
        <span>{{ Math.min(learnedCount + 1, totalCount || 1) }} / {{ totalCount || 1 }}</span>
      </div>

      <div v-if="loading" class="empty-state">
        <Loader2 class="spin" /> 正在准备今日词单...
      </div>

      <div v-else-if="finished || !current" class="completion">
        <Star :size="42" />
        <h2>今天的单词背完了</h2>
        <p>新词和复习任务都已处理。明天到期的词会自动回到复习队列。</p>
        <button class="primary-btn" style="margin-top:16px" @click="emit('navigate', 'test')">
          开始拼写测试
        </button>
      </div>

      <template v-else>
        <div class="word-main">
          <div>
            <p class="word-label">Vocabulary</p>
            <h2>{{ current.word }}</h2>
            <button class="audio-btn" @click="speak(current)">
              <Volume2 :size="20" />
              {{ current.phonetic || '播放发音' }}
            </button>
          </div>
          <button
            class="favorite-btn"
            :class="{ saved: current.is_favorite }"
            @click="toggleFavorite"
          >
            <Heart :size="20" :fill="current.is_favorite ? 'currentColor' : 'none'" />
          </button>
        </div>

        <div class="answer-panel">
          <div>
            <span class="field-label">中文释义</span>
            <p>{{ revealed ? (current.translation || '暂无中文释义') : '先在心里想一想，再翻开释义。' }}</p>
          </div>
          <div>
            <span class="field-label">英文释义</span>
            <p>{{ revealed ? (current.definition || 'No definition yet.') : 'Definition is hidden.' }}</p>
          </div>
          <div>
            <span class="field-label">例句</span>
            <p class="sentence">
              <template v-if="revealed">
                <template v-for="(part, i) in exampleTokens(current.example)" :key="`${part}-${i}`">
                  <button v-if="/^[A-Za-z]/.test(part)" @click="lookupWord(part)">{{ part }}</button>
                  <span v-else>{{ part }}</span>
                </template>
              </template>
              <template v-else>例句会在翻开后出现，单词可点击查询。</template>
            </p>
          </div>
        </div>

        <div class="visual-row">
          <div class="memory-photo">
            <img v-if="current.image_url" :src="current.image_url" :alt="`${current.word} memory`" />
            <div v-else class="photo-fallback">
              <strong>暂无配图</strong>
              <span>{{ health?.pexels?.ok ? '这个词可能太抽象' : '请检查 Pexels Key' }}</span>
            </div>
          </div>
          <div class="reveal-box">
            <button class="primary-btn" @click="revealed = true">
              翻开释义 <ChevronRight :size="18" />
            </button>
            <p>先回忆，再查看含义。反馈会影响下一次复习日期。</p>
          </div>
        </div>

        <div class="feedback-row">
          <button
            v-for="item in feedbacks"
            :key="item.action"
            class="feedback"
            :class="item.tone"
            @click="submitFeedback(item.action)"
          >
            <span>{{ item.label }}</span>
            <small>{{ item.hint }}</small>
          </button>
        </div>
      </template>
    </article>

    <!-- Plan sidebar -->
    <aside class="side-stack">
      <section class="plan-card">
        <p class="eyebrow">Today</p>
        <h2>今日计划</h2>
        <div class="plan-numbers">
          <div><strong>{{ newCount }}</strong><span>新词</span></div>
          <div><strong>{{ reviewCount }}</strong><span>复习</span></div>
          <div><strong>{{ learnedCount }}</strong><span>已完成</span></div>
        </div>
        <div class="progress-track">
          <span :style="{ width: `${totalCount ? (learnedCount / totalCount) * 100 : 0}%` }" />
        </div>
      </section>

    </aside>
  </section>
</template>
