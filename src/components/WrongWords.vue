<script setup>
import { ref, onMounted } from 'vue'
import { Volume2, Search, X, BookOpen, Loader2, CheckCircle2 } from 'lucide-vue-next'

const props = defineProps({
  api: Function,
  speak: Function,
  showToast: Function,
  lookupWord: Function,
})

const words = ref([])
const loading = ref(false)

function isRecovering(word) {
  return ['known', 'easy'].includes(word.last_grade)
}

async function loadWords() {
  loading.value = true
  try {
    const data = await props.api('/api/wrong-words')
    words.value = data.words
  } catch (e) {
    props.showToast(e.message)
  } finally {
    loading.value = false
  }
}

async function removeWord(wordId) {
  try {
    await props.api('/api/wrong-words/remove', {
      method: 'POST',
      body: JSON.stringify({ word_id: wordId }),
    })
    words.value = words.value.filter(w => w.id !== wordId)
    props.showToast('已从错词本移除')
  } catch (e) {
    props.showToast(e.message)
  }
}

onMounted(loadWords)
</script>

<template>
  <section class="wrong-words-page">
    <div class="section-heading">
      <p class="eyebrow">Wrong Words</p>
      <div class="heading-row">
        <h2>错词本</h2>
        <span class="word-count">{{ words.length }} 个错词</span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <Loader2 class="spin" :size="24" />
    </div>

    <div v-else-if="words.length === 0" class="empty-state">
      <div class="empty-icon-wrap"><BookOpen :size="48" /></div>
      <p>还没有错词，继续加油！</p>
    </div>

    <div v-else class="word-list">
      <div v-for="(word, index) in words" :key="word.id" class="word-card" :style="{ '--i': index }">
        <div class="word-main">
          <div class="word-info">
            <h3>{{ word.word }}</h3>
            <span class="phonetic" v-if="word.phonetic">{{ word.phonetic }}</span>
          </div>
          <div class="word-actions">
            <button class="icon-btn" title="播放发音" @click="speak(word)">
              <Volume2 :size="16" />
            </button>
            <button class="icon-btn" title="查词详情" @click="lookupWord(word.word)">
              <Search :size="16" />
            </button>
            <button class="icon-btn remove" title="从错词本移除" @click="removeWord(word.id)">
              <X :size="16" />
            </button>
          </div>
        </div>
        <div class="word-detail">
          <p class="translation">{{ word.translation || '暂无中文释义' }}</p>
          <p class="definition" v-if="word.definition">{{ word.definition }}</p>
          <p class="example" v-if="word.example">
            <span class="field-label">例句</span>
            {{ word.example }}
          </p>
        </div>
        <div class="word-meta">
          <span class="meta-item">答错 <strong>{{ word.attempts - word.correct }}</strong> 次</span>
          <span class="meta-item">遗忘 <strong>{{ word.lapse_count || 0 }}</strong> 次</span>
          <span class="meta-item">熟悉度 <strong>{{ word.familiarity }}/10</strong></span>
          <span class="meta-item" v-if="word.due_date">下次 {{ word.due_date }}</span>
          <span class="meta-item" v-if="word.last_seen">上次学习 {{ word.last_seen?.slice(0, 10) }}</span>
        </div>
        <div v-if="isRecovering(word)" class="recovery-hint">
          <CheckCircle2 :size="15" />
          已有一次正向反馈，再答对一次会自动移出错词本
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.wrong-words-page { position: relative; }

.heading-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.word-count {
  font-size: 14px;
  color: var(--muted);
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255,249,236,0.86);
}

.loading-state {
  display: grid;
  place-items: center;
  min-height: 200px;
}

.empty-state {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--muted);
}

.word-list {
  display: grid;
  gap: 16px;
}

.word-card {
  border: 1px solid var(--line);
  background: rgba(255,249,236,0.86);
  box-shadow: var(--shadow);
  padding: 20px;
  animation: wordCardIn 400ms var(--ease-out) both;
  animation-delay: calc(var(--i, 0) * 60ms);
  transition: box-shadow var(--transition-base), transform var(--transition-base);
}

.word-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateX(3px);
}

@keyframes wordCardIn {
  from { opacity: 0; transform: translateX(-12px); }
  to { opacity: 1; transform: translateX(0); }
}

.empty-icon-wrap {
  animation: emptyFloat 3s ease-in-out infinite;
}

@keyframes emptyFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.word-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.word-info h3 {
  font-family: var(--english-display);
  font-size: 28px;
  font-weight: 600;
  margin: 0;
}

.phonetic {
  font-size: 14px;
  color: var(--muted);
  margin-top: 4px;
  display: block;
}

.word-actions {
  display: flex;
  gap: 6px;
}

.icon-btn {
  width: 34px;
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--paper-2);
  color: var(--muted);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 160ms ease;
}

.icon-btn:hover {
  color: var(--ink);
  border-color: var(--ink);
}

.icon-btn.remove:hover {
  color: var(--red);
  border-color: var(--red);
  background: rgba(139,58,58,0.05);
}

.word-detail {
  padding-left: 16px;
  border-left: 3px solid var(--gold);
  margin-bottom: 12px;
}

.translation {
  font-size: 16px;
  color: var(--ink);
  margin: 0 0 6px;
}

.definition {
  font-size: 14px;
  color: var(--muted);
  margin: 0 0 6px;
  line-height: 1.5;
}

.example {
  font-size: 13px;
  color: #392f27;
  line-height: 1.6;
  margin: 0;
}

.field-label {
  display: inline-block;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-right: 6px;
}

.word-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--muted);
}

.meta-item strong {
  color: var(--ink);
  font-weight: 600;
}

.recovery-hint {
  margin-top: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--sage);
  font-size: 13px;
  padding: 7px 10px;
  border: 1px solid rgba(111, 134, 111, 0.28);
  background: rgba(111, 134, 111, 0.08);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.spin { animation: spin 900ms linear infinite; }
</style>
