<script setup>
import { ref } from 'vue'
import { Check, Clipboard, Search, Sparkles } from 'lucide-vue-next'

const props = defineProps({
  api: Function,
  showToast: Function,
})

const emit = defineEmits(['refresh'])

const AI_PROMPT = `请把我提供的英语单词资料整理成标准 CSV。
要求：
1. 只输出 CSV，不要解释。
2. 表头固定为：word,translation,definition,example
3. word 只保留英文单词或短语，统一小写。
4. translation 写中文释义，definition 写英文释义，example 写一句英文例句。
5. 如果原资料缺少某列，请合理补全；不确定时留空。

待整理内容：
`

const importText = ref('word,translation,definition,example\nserendipity,意外发现美好事物的能力,the chance discovery of something pleasant,Finding that old letter was pure serendipity.')
const bookName = ref('我的文艺词书')
const preview = ref([])

async function previewImport() {
  try {
    const data = await props.api('/api/import/preview', {
      method: 'POST',
      body: JSON.stringify({ text: importText.value }),
    })
    preview.value = data.words
    props.showToast(`识别到 ${data.total} 个单词`)
  } catch (e) {
    props.showToast(e.message)
  }
}

async function createBook() {
  const words = preview.value.length
    ? preview.value
    : (await props.api('/api/import/preview', {
        method: 'POST',
        body: JSON.stringify({ text: importText.value }),
      })).words
  try {
    const data = await props.api('/api/books', {
      method: 'POST',
      body: JSON.stringify({ name: bookName.value, words }),
    })
    props.showToast(`已导入 ${data.inserted} 个单词`)
    preview.value = []
    emit('refresh')
  } catch (e) {
    props.showToast(e.message)
  }
}

function copyPrompt() {
  navigator.clipboard.writeText(AI_PROMPT)
  props.showToast('AI 整理提示词已复制')
}
</script>

<template>
  <section id="import" class="import-section">
    <div class="section-heading">
      <p class="eyebrow">Import</p>
      <h2>导入单词书</h2>
    </div>
    <div class="import-grid">
      <article class="import-editor">
        <input
          class="book-name"
          v-model="bookName"
          placeholder="词书名称"
        />
        <textarea v-model="importText" />
        <div class="action-row">
          <button class="quiet-btn" @click="previewImport"><Search :size="18" /> 预览</button>
          <button class="primary-btn" @click="createBook"><Check :size="18" /> 导入词书</button>
        </div>
        <div class="preview-table">
          <div v-for="item in preview.slice(0, 6)" :key="item.word">
            <strong>{{ item.word }}</strong>
            <span>{{ item.translation || item.definition || '待自动补全' }}</span>
          </div>
        </div>
      </article>

      <article class="prompt-note">
        <div class="note-pin" />
        <div class="note-title">
          <Sparkles :size="20" />
          <h3>AI 整理提示词</h3>
        </div>
        <pre>{{ AI_PROMPT }}</pre>
        <button class="quiet-btn" @click="copyPrompt"><Clipboard :size="18" /> 复制提示词</button>
      </article>
    </div>
  </section>
</template>
