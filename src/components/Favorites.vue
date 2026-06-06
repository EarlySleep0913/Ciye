<script setup>
import { ref, onMounted } from 'vue'
import { Volume2, Search, Heart, BookOpen, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  api: Function,
  speak: Function,
  showToast: Function,
  lookupWord: Function,
})

const words = ref([])
const loading = ref(false)

async function loadWords() {
  loading.value = true
  try {
    const data = await props.api('/api/favorites')
    words.value = data.words
  } catch (e) {
    props.showToast(e.message)
  } finally {
    loading.value = false
  }
}

async function removeFavorite(wordId) {
  try {
    await props.api('/api/favorite', {
      method: 'POST',
      body: JSON.stringify({ word_id: wordId, favorite: false }),
    })
    words.value = words.value.filter(w => w.id !== wordId)
    props.showToast('已取消收藏')
  } catch (e) {
    props.showToast(e.message)
  }
}

onMounted(loadWords)
</script>

<template>
  <section class="favorites-page">
    <div class="section-heading">
      <p class="eyebrow">Favorites</p>
      <div class="heading-row">
        <h2>收藏夹</h2>
        <span class="word-count">{{ words.length }} 个收藏</span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <Loader2 class="spin" :size="24" />
    </div>

    <div v-else-if="words.length === 0" class="empty-state">
      <Heart :size="48" />
      <p>还没有收藏的单词，学习时点击心形按钮收藏。</p>
    </div>

    <div v-else class="word-list">
      <div v-for="word in words" :key="word.id" class="word-card">
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
            <button class="icon-btn unfav" title="取消收藏" @click="removeFavorite(word.id)">
              <Heart :size="16" fill="currentColor" />
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
      </div>
    </div>
  </section>
</template>

<style scoped>
.favorites-page { position: relative; }

.heading-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.word-count {
  font-size: 14px;
  color: var(--red);
  padding: 4px 12px;
  border: 1px solid rgba(139,58,58,0.3);
  border-radius: 12px;
  background: rgba(139,58,58,0.05);
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

.icon-btn.unfav {
  color: var(--red);
  border-color: rgba(139,58,58,0.3);
}

.icon-btn.unfav:hover {
  background: rgba(139,58,58,0.05);
  border-color: var(--red);
}

.word-detail {
  padding-left: 16px;
  border-left: 3px solid var(--gold);
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

@keyframes spin {
  to { transform: rotate(360deg); }
}
.spin { animation: spin 900ms linear infinite; }
</style>
