<script setup>
import { ref } from 'vue'
import { Check, Import, Loader2, Sparkles, Clipboard, Eye } from 'lucide-vue-next'
import BookPreview from './BookPreview.vue'

const props = defineProps({
  books: Array,
  settings: Object,
  api: Function,
  showToast: Function,
  speak: Function,
})

const emit = defineEmits(['refresh'])

// Bookshelf state
const showConfirm = ref(null) // book id being confirmed
const showImport = ref(false)
const confirmLimit = ref(15)
const previewBook = ref(null) // book being previewed

// Import state
const importText = ref('word,translation,definition,example\nserendipity,意外发现美好事物的能力,the chance discovery of something pleasant,Finding that old letter was pure serendipity.')
const bookName = ref('我的词书')
const preview = ref([])
const importing = ref(false)

const AI_PROMPT = `请把我提供的英语单词资料整理成标准 CSV。
要求：
1. 只输出 CSV，不要解释。
2. 表头固定为：word,translation,definition,example
3. word 只保留英文单词或短语，统一小写。
4. translation 写中文释义，definition 写英文释义，example 写一句英文例句。
5. 如果原资料缺少某列，请合理补全；不确定时留空。

待整理内容：
`

// Book color palette
const bookColors = [
  { spine: '#8b3a3a', pages: '#f4efe4' },
  { spine: '#223b32', pages: '#fff9ec' },
  { spine: '#af8744', pages: '#f4efe4' },
  { spine: '#6f866f', pages: '#fff9ec' },
  { spine: '#5a4f42', pages: '#f4efe4' },
  { spine: '#756b5d', pages: '#fff9ec' },
]

function getBookColor(index) {
  return bookColors[index % bookColors.length]
}

function progressPercent(book) {
  if (!book.total) return 0
  return Math.round((book.mastered_count / book.total) * 100)
}

function clickBook(book) {
  showConfirm.value = book.id
  confirmLimit.value = props.settings?.daily_new_limit || 15
}

async function confirmSwitch() {
  const bookId = showConfirm.value
  showConfirm.value = null
  try {
    await props.api('/api/books/activate', {
      method: 'POST',
      body: JSON.stringify({
        book_id: bookId,
        daily_new_limit: confirmLimit.value,
      }),
    })
    await emit('refresh')
    props.showToast(`已切换词书，每日 ${confirmLimit.value} 词`)
  } catch (e) {
    props.showToast(e.message)
  }
}

function cancelSwitch() {
  showConfirm.value = null
}

// Import functions
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
  importing.value = true
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
    showImport.value = false
    emit('refresh')
  } catch (e) {
    props.showToast(e.message)
  } finally {
    importing.value = false
  }
}

function copyPrompt() {
  navigator.clipboard.writeText(AI_PROMPT)
  props.showToast('AI 整理提示词已复制')
}

function toggleImport() {
  showImport.value = !showImport.value
}
</script>

<template>
  <section class="shelf-page">
    <div class="section-heading">
      <p class="eyebrow">Bookshelf</p>
      <div class="shelf-topbar">
        <h2>词书架</h2>
        <button class="quiet-btn" @click="toggleImport">
          <Import :size="18" />
          {{ showImport ? '返回书架' : '导入新词书' }}
        </button>
      </div>
    </div>

    <!-- Bookshelf View -->
    <div v-if="!showImport" class="bookshelf-wrapper">
      <div class="bookshelf">
        <div class="shelf-row">
          <div
            v-for="(book, i) in books"
            :key="book.id"
            class="book-item"
            :class="{ active: book.active }"
            @click="clickBook(book)"
          >
            <div class="book-cover" :style="{ '--spine-color': getBookColor(i).spine, '--page-color': getBookColor(i).pages }">
              <div class="book-spine"></div>
              <div class="book-front">
                <div class="book-front-inner">
                  <span class="book-title">{{ book.name }}</span>
                  <span class="book-count">{{ book.total }} 词</span>
                  <div class="book-progress-bar">
                    <div class="book-progress-fill" :style="{ width: progressPercent(book) + '%' }"></div>
                  </div>
                  <span class="book-progress-text">{{ progressPercent(book) }}% 已掌握</span>
                </div>
                <div v-if="book.active" class="book-active-badge">使用中</div>
              </div>
            </div>
            <div class="book-stats">
              <span class="stat-new">新 {{ book.new_count }}</span>
              <span class="stat-learning">学 {{ book.learning_count }}</span>
              <span class="stat-mastered">会 {{ book.mastered_count }}</span>
            </div>
            <button class="preview-btn" title="预览词表" @click.stop="previewBook = book">
              <Eye :size="14" /> 预览
            </button>
          </div>
        </div>
        <div class="shelf-base"></div>
      </div>

      <!-- Confirm Dialog -->
      <Teleport to="body">
        <div v-if="showConfirm" class="dialog-overlay" @click.self="cancelSwitch">
          <div class="dialog">
            <h3>{{ books.find(b => b.id === showConfirm)?.active ? '设置学习计划' : '切换词书' }}</h3>
            <p>
              <template v-if="!books.find(b => b.id === showConfirm)?.active">
                确定要切换到
                <strong>{{ books.find(b => b.id === showConfirm)?.name }}</strong>
                吗？
              </template>
              <template v-else>
                调整 <strong>{{ books.find(b => b.id === showConfirm)?.name }}</strong> 的每日学习计划。
              </template>
            </p>
            <div class="limit-control">
              <label>每天新词数</label>
              <div class="limit-row">
                <input
                  type="range"
                  min="3"
                  max="150"
                  v-model.number="confirmLimit"
                />
                <strong>{{ confirmLimit }}</strong>
              </div>
            </div>
            <div class="dialog-actions">
              <button class="quiet-btn" @click="cancelSwitch">取消</button>
              <button class="primary-btn" @click="confirmSwitch">
                <Check :size="16" /> 确认
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </div>

    <!-- Import View -->
    <div v-else class="import-section">
      <div class="import-grid">
        <article class="import-editor">
          <input class="book-name" v-model="bookName" placeholder="词书名称" />
          <textarea v-model="importText" />
          <div class="action-row">
            <button class="quiet-btn" @click="previewImport"><Eye :size="18" /> 预览</button>
            <button class="primary-btn" :disabled="importing" @click="createBook">
              <Loader2 v-if="importing" class="spin" :size="18" />
              <Check v-else :size="18" />
              导入词书
            </button>
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
    </div>

    <!-- Book Preview -->
    <BookPreview
      v-if="previewBook"
      :book="previewBook"
      :api="api"
      :speak="speak"
      :show-toast="showToast"
      @close="previewBook = null"
      @refresh="emit('refresh')"
    />
  </section>
</template>

<style scoped>
.shelf-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Bookshelf */
.bookshelf-wrapper {
  margin-top: 8px;
}

.bookshelf {
  position: relative;
  padding: 34px 26px 0;
  background:
    linear-gradient(180deg, rgba(34, 59, 50, 0.055) 0%, transparent 46%),
    linear-gradient(90deg, rgba(175, 135, 68, 0.04) 1px, transparent 1px),
    rgba(255, 249, 236, 0.68);
  background-size: auto, 28px 28px, auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,0.46);
}

.shelf-row {
  display: flex;
  gap: 28px;
  flex-wrap: wrap;
  justify-content: center;
  padding-bottom: 20px;
  min-height: 280px;
  align-items: flex-end;
}

.shelf-base {
  height: 20px;
  background:
    repeating-linear-gradient(
      90deg,
      transparent 0px,
      rgba(160, 120, 70, 0.12) 1px,
      transparent 3px,
      rgba(140, 100, 55, 0.08) 6px,
      transparent 8px,
      rgba(120, 85, 45, 0.06) 12px,
      transparent 14px
    ),
    repeating-linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.06) 0px,
      transparent 2px,
      rgba(0, 0, 0, 0.04) 4px,
      transparent 6px
    ),
    linear-gradient(180deg, #c4a882 0%, #b0895e 35%, #a07a50 70%, #8a6840 100%);
  border-radius: 0 0 8px 8px;
  box-shadow:
    0 8px 24px rgba(42, 30, 18, 0.22),
    inset 0 2px 6px rgba(255, 255, 255, 0.35),
    inset 0 -3px 6px rgba(42, 30, 18, 0.2);
  position: relative;
}

/* 木纹高光线 */
.shelf-base::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 5%;
  right: 5%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
  border-radius: 1px;
}

/* Book item */
.book-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: transform 400ms var(--ease-spring), filter 300ms ease;
  transform-style: preserve-3d;
}

.book-item:hover {
  transform: translateY(-12px) rotateY(-4deg) rotateX(2deg);
  filter: drop-shadow(0 18px 30px rgba(42, 30, 18, 0.24));
}

.book-item.active .book-cover {
  filter: drop-shadow(0 10px 26px rgba(139, 58, 58, 0.28));
}

/* 3D Book cover */
.book-cover {
  position: relative;
  width: 126px;
  height: 178px;
  perspective: 800px;
  transition: transform 400ms var(--ease-spring);
}

/* 书籍入场 stagger 动画 */
.book-item {
  animation: bookAppear 500ms var(--ease-out) both;
}

.book-item:nth-child(1) { animation-delay: 80ms; }
.book-item:nth-child(2) { animation-delay: 160ms; }
.book-item:nth-child(3) { animation-delay: 240ms; }
.book-item:nth-child(4) { animation-delay: 320ms; }
.book-item:nth-child(5) { animation-delay: 400ms; }
.book-item:nth-child(6) { animation-delay: 480ms; }

@keyframes bookAppear {
  from { opacity: 0; transform: translateY(24px) scale(0.9); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.book-spine {
  position: absolute;
  left: 0;
  top: 0;
  width: 14px;
  height: 100%;
  background: var(--spine-color);
  border-radius: 3px 0 0 3px;
  box-shadow: inset -3px 0 6px rgba(0, 0, 0, 0.2);
  transform: rotateY(-2deg);
  transform-origin: left center;
  /* K. 书脊光影（增强） */
  background-image: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.2) 0%,
    rgba(255, 255, 255, 0.08) 8%,
    transparent 18%,
    transparent 82%,
    rgba(0, 0, 0, 0.12) 92%,
    rgba(0, 0, 0, 0.18) 100%
  );
  background-blend-mode: overlay;
}

/* 书脊顶部高光条 */
.book-spine::after {
  content: "";
  position: absolute;
  left: 2px;
  top: 8px;
  bottom: 8px;
  width: 1px;
  background: linear-gradient(180deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  pointer-events: none;
}

.book-front {
  position: absolute;
  left: 12px;
  top: 0;
  width: 114px;
  height: 100%;
  background: var(--spine-color);
  border-radius: 0 4px 4px 0;
  box-shadow:
    3px 6px 16px rgba(0, 0, 0, 0.18),
    inset 0 0 0 1px rgba(255, 255, 255, 0.12),
    inset 12px 0 18px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.book-front-inner {
  flex: 1;
  padding: 16px 12px 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  gap: 6px;
}

.book-title {
  font-family: var(--body-font);
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.book-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
}

.book-progress-bar {
  width: 80%;
  height: 4px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.book-progress-fill {
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 2px;
  transition: width 300ms ease;
}

.book-progress-text {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
}

.book-active-badge {
  padding: 4px 0;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: white;
  background: rgba(139, 58, 58, 0.9);
  border-radius: 0 0 4px 4px;
}

.preview-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
  background: none;
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 5px 11px;
  cursor: pointer;
  transition: all 160ms;
  font-family: inherit;
}

.preview-btn:hover {
  color: var(--ink);
  border-color: var(--gold);
  background: rgba(255, 249, 236, 0.86);
  transform: translateY(-1px);
}

.ai-btn {
  color: var(--gold) !important;
  border-color: rgba(175, 135, 68, 0.4) !important;
}

.ai-btn:hover:not(:disabled) {
  background: rgba(175, 135, 68, 0.08) !important;
  border-color: var(--gold) !important;
}

/* Book stats */
.book-stats {
  display: flex;
  gap: 8px;
  font-size: 11px;
  padding: 5px 8px;
  border: 1px solid rgba(216, 203, 184, 0.72);
  background: rgba(255, 249, 236, 0.72);
  border-radius: 7px;
}

.stat-new { color: var(--muted); }
.stat-learning { color: var(--gold); }
.stat-mastered { color: var(--sage); }

/* Confirm Dialog */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(34, 59, 50, 0.4);
  display: grid;
  place-items: center;
  z-index: 50;
  backdrop-filter: blur(6px);
  animation: overlayIn 250ms ease-out;
}

@keyframes overlayIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.dialog {
  background: var(--paper-2);
  border: 1px solid var(--line);
  box-shadow: 0 32px 80px rgba(42, 30, 18, 0.25);
  padding: 32px;
  max-width: 400px;
  width: 90%;
  animation: dialogIn 350ms var(--ease-out);
}

@keyframes dialogIn {
  from { opacity: 0; transform: translateY(16px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.dialog h3 {
  font-size: 22px;
  font-family: var(--display-font);
  margin-bottom: 12px;
}

.dialog p {
  color: var(--ink);
  line-height: 1.6;
}

.limit-control {
  margin: 20px 0;
  padding: 16px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.limit-control label {
  display: block;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.limit-row {
  display: grid;
  grid-template-columns: 1fr 46px;
  align-items: center;
  gap: 14px;
}

.limit-row strong {
  font-size: 24px;
  text-align: center;
  color: var(--ink);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

/* Import section */
.import-section {
  margin-top: 8px;
}

.import-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
  gap: 22px;
}

.import-editor, .prompt-note {
  padding: 22px;
  min-width: 0;
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
}

.book-name, .import-editor textarea {
  width: 100%;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.54);
  color: var(--ink);
  border-radius: 6px;
  outline: 0;
}

.book-name {
  height: 46px;
  padding: 0 14px;
  margin-bottom: 12px;
}

.import-editor textarea {
  min-height: 190px;
  resize: vertical;
  padding: 14px;
  line-height: 1.65;
  font-family: Consolas, "Courier New", monospace;
}

.action-row {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin: 14px 0;
}

.preview-table { display: grid; gap: 8px; }

.preview-table div {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 12px;
  padding: 10px 0;
  border-top: 1px dashed var(--line);
}

.prompt-note {
  position: relative;
  background: #fff2bf;
  transform: rotate(0.6deg);
}

.note-pin {
  position: absolute;
  width: 18px;
  height: 18px;
  top: 15px;
  right: 18px;
  border-radius: 50%;
  background: var(--red);
  box-shadow: inset 0 0 0 4px rgba(255, 255, 255, 0.28);
}

.note-title {
  display: flex;
  align-items: center;
  gap: 9px;
}

@media (max-width: 720px) {
  .shelf-row { gap: 16px; }
  .book-cover { width: 90px; height: 130px; }
  .book-spine { width: 10px; }
  .book-front { left: 8px; width: 82px; }
  .book-front-inner { padding: 10px 8px; }
  .book-title { font-size: 11px; }
  .import-grid { grid-template-columns: 1fr; }
}
</style>
