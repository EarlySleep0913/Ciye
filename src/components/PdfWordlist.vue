<script setup>
import { ref, computed, watch } from 'vue'
import { Check, Loader2, Volume2 } from 'lucide-vue-next'

const props = defineProps({
  pdfWords: Object,
  speakPdfWord: Function,
  pronouncingId: Number,
  api: Function,
  showToast: Function,
  lookupWord: Function,
})

const emit = defineEmits(['refresh', 'update-words'])

const activePdfDay = ref(null)

const activePdfGroup = computed(() => {
  return props.pdfWords.days?.find(d => d.day === activePdfDay.value)
    || props.pdfWords.days?.[0]
    || { words: [] }
})

watch(() => props.pdfWords.days, (days) => {
  if (!activePdfDay.value && days?.length) {
    activePdfDay.value = days[0].day
  }
}, { immediate: true })

async function togglePdfMark(item) {
  const crossed = !item.crossed
  const updated = {
    ...props.pdfWords,
    crossed_total: props.pdfWords.crossed_total + (crossed ? 1 : -1),
    days: props.pdfWords.days.map(day => ({
      ...day,
      words: day.words.map(w => w.id === item.id ? { ...w, crossed } : w),
    })),
  }
  emit('update-words', updated)
  try {
    await props.api('/api/pdf-words/mark', {
      method: 'POST',
      body: JSON.stringify({ word_id: item.id, crossed }),
    })
  } catch (e) {
    props.showToast(e.message)
    emit('refresh')
  }
}
</script>

<template>
  <section id="pdf-list" class="pdf-section">
    <div class="pdf-toolbar">
      <div>
        <p class="eyebrow">CET-4 PDF Wordlist</p>
        <h2>英语四级高频词汇</h2>
        <p>按 PDF 的 Day 分组排版。点单词听发音；点前面的小框给这个词划线，再点一次取消。</p>
      </div>
      <div class="pdf-summary">
        <strong>{{ pdfWords.total }}</strong>
        <span>PDF 词条</span>
        <strong>{{ pdfWords.crossed_total }}</strong>
        <span>已划线</span>
      </div>
    </div>

    <div class="day-tabs" aria-label="PDF Day 切换">
      <button
        v-for="day in pdfWords.days"
        :key="day.day"
        :class="{ active: day.day === activePdfGroup.day }"
        @click="activePdfDay = day.day"
      >
        Day {{ day.day }}
      </button>
    </div>

    <article class="pdf-page">
      <header class="pdf-page-head">
        <div>
          <span>第一章 大学英语四级高频词汇</span>
          <h3>DAY {{ activePdfGroup.day || '-' }}</h3>
        </div>
        <small>{{ activePdfGroup.words.length }} words</small>
      </header>
      <div class="pdf-word-grid">
        <div
          v-for="item in activePdfGroup.words"
          :key="item.id"
          class="pdf-word-row"
          :class="{ crossed: item.crossed }"
        >
          <button
            class="mark-box"
            :aria-label="`${item.crossed ? '取消划线' : '划线'} ${item.word}`"
            @click="togglePdfMark(item)"
          >
            <Check v-if="item.crossed" :size="14" />
          </button>
          <button class="pdf-word" @click="speakPdfWord(item)">
            <Loader2 v-if="pronouncingId === item.id" class="spin" :size="13" />
            <Volume2 v-else :size="13" />
            {{ item.word }}
          </button>
          <span class="pdf-meaning">{{ item.translation }}</span>
        </div>
      </div>
    </article>
  </section>
</template>
