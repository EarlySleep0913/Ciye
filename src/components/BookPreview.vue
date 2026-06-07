<script setup>
import { ref, watch } from 'vue'
import { X, ChevronLeft, ChevronRight, Trash2, Edit3, Check, Volume2, PenLine } from 'lucide-vue-next'

const props = defineProps({
  book: Object,
  api: Function,
  showToast: Function,
  speak: Function,
})

const emit = defineEmits(['close', 'refresh'])

const words = ref([])
const totalWords = ref(0)
const page = ref(1)
const totalPages = ref(1)
const loading = ref(false)
const editingWord = ref(null)
const editForm = ref({})
const renaming = ref(false)
const newName = ref('')

async function loadPage() {
  loading.value = true
  try {
    const data = await props.api(`/api/books/${props.book.id}/words?page=${page.value}&per_page=50`)
    words.value = data.words
    totalWords.value = data.total
    totalPages.value = data.total_pages
  } catch (e) {
    props.showToast(e.message)
  } finally {
    loading.value = false
  }
}

function startEdit(word) {
  editingWord.value = word.id
  editForm.value = {
    translation: word.translation || '',
    definition: word.definition || '',
    example: word.example || '',
  }
}

function cancelEdit() {
  editingWord.value = null
  editForm.value = {}
}

async function saveEdit(wordId) {
  try {
    await props.api(`/api/words/${wordId}`, {
      method: 'PUT',
      body: JSON.stringify(editForm.value),
    })
    const w = words.value.find(w => w.id === wordId)
    if (w) Object.assign(w, editForm.value)
    editingWord.value = null
    props.showToast('已保存')
  } catch (e) {
    props.showToast(e.message)
  }
}

async function deleteWord(wordId, wordName) {
  if (!confirm(`确定删除单词 "${wordName}" 吗？`)) return
  try {
    await props.api(`/api/words/${wordId}`, { method: 'DELETE' })
    words.value = words.value.filter(w => w.id !== wordId)
    totalWords.value--
    props.showToast('已删除')
  } catch (e) {
    props.showToast(e.message)
  }
}

function startRename() {
  newName.value = props.book.name
  renaming.value = true
}

async function saveRename() {
  if (!newName.value.trim()) return
  try {
    await props.api(`/api/books/${props.book.id}`, {
      method: 'PUT',
      body: JSON.stringify({ name: newName.value.trim() }),
    })
    props.book.name = newName.value.trim()
    renaming.value = false
    props.showToast('词书已重命名')
    emit('refresh')
  } catch (e) {
    props.showToast(e.message)
  }
}

async function deleteBook() {
  if (!confirm(`确定删除词书 "${props.book.name}" 吗？所有单词都会被删除，不可恢复。`)) return
  try {
    await props.api(`/api/books/${props.book.id}`, { method: 'DELETE' })
    props.showToast('词书已删除')
    emit('refresh')
    emit('close')
  } catch (e) {
    props.showToast(e.message)
  }
}

watch(() => props.book, () => {
  page.value = 1
  loadPage()
}, { immediate: true })
</script>

<template>
  <Teleport to="body">
    <div class="preview-overlay" @click.self="emit('close')">
      <div class="preview-panel">
        <header class="preview-header">
          <div class="preview-title-area">
            <template v-if="renaming">
              <div class="rename-row">
                <input v-model="newName" class="rename-input" @keydown.enter="saveRename" autofocus />
                <button class="icon-btn ok" @click="saveRename"><Check :size="14" /></button>
                <button class="icon-btn" @click="renaming = false"><X :size="14" /></button>
              </div>
            </template>
            <template v-else>
              <h2>
                {{ book.name }}
                <button v-if="book.is_owner" class="rename-btn" @click="startRename"><PenLine :size="14" /></button>
              </h2>
            </template>
            <span class="preview-meta">{{ totalWords }} 词 · 第 {{ page }}/{{ totalPages }} 页</span>
          </div>
          <div class="preview-actions">
            <button v-if="book.is_owner" class="quiet-btn danger-btn" @click="deleteBook">
              <Trash2 :size="14" /> 删除词书
            </button>
            <button class="quiet-btn" @click="emit('close')"><X :size="18" /></button>
          </div>
        </header>

        <!-- Word list -->
        <div class="word-table">
          <div class="wt-header">
            <span class="wt-col-word">单词</span>
            <span class="wt-col-trans">中文释义</span>
            <span class="wt-col-def">英文释义</span>
            <span class="wt-col-status">状态</span>
            <span class="wt-col-actions">操作</span>
          </div>
          <div v-if="loading" class="wt-loading">
            <Loader2 class="spin" :size="20" />
          </div>
          <template v-else>
            <div v-for="w in words" :key="w.id" class="wt-row" :class="{ editing: editingWord === w.id }">
              <!-- Word -->
              <div class="wt-col-word">
                <strong>{{ w.word }}</strong>
                <span v-if="w.phonetic" class="wt-phonetic">{{ w.phonetic }}</span>
              </div>

              <!-- Translation -->
              <div class="wt-col-trans">
                <template v-if="editingWord === w.id">
                  <input v-model="editForm.translation" class="edit-input" />
                </template>
                <template v-else>{{ w.translation || '-' }}</template>
              </div>

              <!-- Definition -->
              <div class="wt-col-def">
                <template v-if="editingWord === w.id">
                  <input v-model="editForm.definition" class="edit-input" />
                </template>
                <template v-else>{{ w.definition || '-' }}</template>
              </div>

              <!-- Status -->
              <div class="wt-col-status">
                <span class="status-tag" :class="w.status || 'new'">
                  {{ w.status === 'mastered' ? '已掌握' : w.status === 'learning' ? '学习中' : '未学' }}
                </span>
              </div>

              <!-- Actions -->
              <div class="wt-col-actions">
                <template v-if="editingWord === w.id">
                  <button class="icon-btn ok" title="保存" @click="saveEdit(w.id)"><Check :size="14" /></button>
                  <button class="icon-btn" title="取消" @click="cancelEdit"><X :size="14" /></button>
                </template>
                <template v-else>
                  <button class="icon-btn" title="发音" @click="speak(w)"><Volume2 :size="14" /></button>
                  <button v-if="book.is_owner" class="icon-btn" title="编辑" @click="startEdit(w)"><Edit3 :size="14" /></button>
                  <button v-if="book.is_owner" class="icon-btn danger" title="删除" @click="deleteWord(w.id, w.word)"><Trash2 :size="14" /></button>
                </template>
              </div>
            </div>
          </template>
        </div>

        <!-- Pagination -->
        <div class="preview-pagination">
          <button class="quiet-btn compact" :disabled="page <= 1" @click="page--; loadPage()">
            <ChevronLeft :size="14" /> 上一页
          </button>
          <span>{{ page }} / {{ totalPages }}</span>
          <button class="quiet-btn compact" :disabled="page >= totalPages" @click="page++; loadPage()">
            下一页 <ChevronRight :size="14" />
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(34, 59, 50, 0.5);
  z-index: 50;
  display: grid;
  place-items: center;
  backdrop-filter: blur(6px);
  animation: overlayFadeIn 250ms ease-out;
}

@keyframes overlayFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.preview-panel {
  width: min(1100px, 95vw);
  max-height: 90vh;
  background: var(--paper-2);
  border: 1px solid var(--line);
  box-shadow: 0 32px 80px rgba(42, 30, 18, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: panelSlideIn 400ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes panelSlideIn {
  from { opacity: 0; transform: translateY(24px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
}

.preview-header h2 {
  font-family: var(--display-font);
  font-size: 24px;
  font-weight: 400;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rename-btn {
  border: none;
  background: none;
  color: var(--muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 160ms;
}

.rename-btn:hover {
  color: var(--ink);
  background: rgba(175, 135, 68, 0.1);
}

.rename-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rename-input {
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--gold);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.8);
  font-family: var(--display-font);
  font-size: 20px;
  color: var(--ink);
  outline: none;
  min-width: 200px;
}

.preview-meta {
  font-size: 13px;
  color: var(--muted);
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.danger-btn {
  color: var(--red) !important;
  border-color: rgba(139, 58, 58, 0.3) !important;
}

.danger-btn:hover {
  background: rgba(139, 58, 58, 0.05) !important;
}

/* Word table */
.word-table {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.wt-header {
  display: grid;
  grid-template-columns: 160px 1fr 1fr 70px 90px;
  gap: 12px;
  padding: 10px 24px;
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid var(--line);
  position: sticky;
  top: 0;
  background: var(--paper-2);
  z-index: 1;
}

.wt-row {
  display: grid;
  grid-template-columns: 160px 1fr 1fr 70px 90px;
  gap: 12px;
  padding: 10px 24px;
  border-bottom: 1px solid rgba(216, 203, 184, 0.3);
  align-items: center;
  font-size: 14px;
  transition: background 160ms, transform 200ms cubic-bezier(0.16, 1, 0.3, 1);
}

.wt-row:hover {
  background: rgba(175, 135, 68, 0.05);
  transform: translateX(2px);
}
.wt-row.editing { background: rgba(175, 135, 68, 0.08); }

.wt-col-word strong {
  font-family: var(--english-display);
  font-size: 16px;
  display: block;
}

.wt-phonetic {
  font-size: 12px;
  color: var(--muted);
}

.wt-col-trans, .wt-col-def {
  font-size: 13px;
  color: #392f27;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.edit-input {
  width: 100%;
  height: 32px;
  padding: 0 8px;
  border: 1px solid var(--gold);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  font-family: inherit;
  outline: none;
}

.status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 500;
}

.status-tag.new { background: rgba(216, 203, 184, 0.3); color: var(--muted); }
.status-tag.learning { background: rgba(175, 135, 68, 0.15); color: var(--gold); }
.status-tag.mastered { background: rgba(111, 134, 111, 0.15); color: var(--sage); }

.wt-col-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--muted);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 160ms cubic-bezier(0.16, 1, 0.3, 1);
}

.icon-btn:hover {
  color: var(--ink);
  border-color: var(--ink);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(42, 30, 18, 0.1);
}
.icon-btn:active { transform: translateY(0) scale(0.95); }
.icon-btn.ok:hover { color: var(--sage); border-color: var(--sage); }
.icon-btn.danger:hover { color: var(--red); border-color: var(--red); }

.wt-loading {
  display: grid;
  place-items: center;
  padding: 40px;
}

/* Pagination */
.preview-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 14px 24px;
  border-top: 1px solid var(--line);
  font-size: 13px;
  color: var(--muted);
}

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 900ms linear infinite; }
</style>
