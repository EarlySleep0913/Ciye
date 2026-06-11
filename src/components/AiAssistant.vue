<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Send, X, Minus, Maximize2, RotateCcw, GripVertical } from 'lucide-vue-next'

const props = defineProps({
  api: Function,
  showToast: Function,
})

const gifs = ['idle.gif', 'waving.gif', 'waiting.gif', 'review.gif', 'running.gif']
const currentGif = ref(0)
const open = ref(false)
const messages = ref([])
const input = ref('')
const loading = ref(false)
const chatBodyRef = ref(null)

// Position & size
const btnX = ref(0)
const btnY = ref(0)
const dlgX = ref(0)
const dlgY = ref(0)
const dlgW = ref(420)
const dlgH = ref(520)
const gifSize = ref(132)
const dragging = ref(null)
const dragOffset = ref({ x: 0, y: 0 })

function defaultGifSize() {
  return window.innerWidth < 720 ? 82 : 132
}

function placeButtonDefault() {
  const margin = 26
  btnX.value = Math.max(margin, window.innerWidth - gifSize.value - margin)
  btnY.value = Math.max(margin, window.innerHeight - gifSize.value - margin)
}

// Load settings from localStorage
onMounted(() => {
  gifSize.value = defaultGifSize()
  const size = localStorage.getItem('ai_gif_size')
  if (size) gifSize.value = Number(size) || defaultGifSize()
  if (window.innerWidth < 720 && gifSize.value > 110) gifSize.value = defaultGifSize()

  const saved = localStorage.getItem('ai_assistant_pos')
  if (saved) {
    try {
      const p = JSON.parse(saved)
      btnX.value = p.btnX ?? window.innerWidth - gifSize.value - 26
      btnY.value = p.btnY ?? window.innerHeight - gifSize.value - 26
      dlgX.value = p.dlgX ?? window.innerWidth - 480
      dlgY.value = p.dlgY ?? window.innerHeight - 600
      dlgW.value = p.dlgW ?? 420
      dlgH.value = p.dlgH ?? 520
      if (btnX.value < 260 && btnY.value > window.innerHeight - 320) {
        placeButtonDefault()
      }
    } catch {}
  } else {
    placeButtonDefault()
    dlgX.value = Math.max(20, window.innerWidth - 470)
    dlgY.value = window.innerHeight - 600
  }
  loadHistory()
  gifTimer = setInterval(() => {
    currentGif.value = (currentGif.value + 1) % gifs.length
  }, 4000)

  window.addEventListener('ai-size-changed', onSizeChanged)
  window.addEventListener('ai-reset-position', onResetPosition)
})

let gifTimer = null
function onSizeChanged(e) {
  gifSize.value = e.detail || defaultGifSize()
  placeButtonDefault()
  savePos()
}
function onResetPosition() {
  placeButtonDefault()
  positionDialog()
  savePos()
  open.value = true
  nextTick(scrollBottom)
}
onUnmounted(() => {
  if (gifTimer) clearInterval(gifTimer)
  window.removeEventListener('ai-size-changed', onSizeChanged)
  window.removeEventListener('ai-reset-position', onResetPosition)
})

function savePos() {
  localStorage.setItem('ai_assistant_pos', JSON.stringify({
    btnX: btnX.value, btnY: btnY.value,
    dlgX: dlgX.value, dlgY: dlgY.value,
    dlgW: dlgW.value, dlgH: dlgH.value,
  }))
}

// Drag handlers
function onBtnDown(e) {
  e.preventDefault()
  dragging.value = 'btn'
  dragOffset.value = { x: e.clientX - btnX.value, y: e.clientY - btnY.value }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

function onDlgDown(e) {
  if (e.target.closest('.chat-body') || e.target.closest('.chat-input-row') || e.target.closest('.resize-handle')) return
  e.preventDefault()
  dragging.value = 'dlg'
  dragOffset.value = { x: e.clientX - dlgX.value, y: e.clientY - dlgY.value }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

function onResizeDown(e) {
  e.preventDefault()
  e.stopPropagation()
  dragging.value = 'resize'
  dragOffset.value = { x: e.clientX, y: e.clientY, w: dlgW.value, h: dlgH.value }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e) {
  if (dragging.value === 'btn') {
    btnX.value = e.clientX - dragOffset.value.x
    btnY.value = e.clientY - dragOffset.value.y
  } else if (dragging.value === 'dlg') {
    dlgX.value = e.clientX - dragOffset.value.x
    dlgY.value = e.clientY - dragOffset.value.y
  } else if (dragging.value === 'resize') {
    dlgW.value = Math.max(320, dragOffset.value.w + (e.clientX - dragOffset.value.x))
    dlgH.value = Math.max(300, dragOffset.value.h + (e.clientY - dragOffset.value.y))
  }
}

function onDragEnd() {
  dragging.value = null
  savePos()
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}

// Chat
async function loadHistory() {
  try {
    const data = await props.api('/api/ai/history')
    messages.value = data.messages || []
  } catch {}
}

async function send() {
  const msg = input.value.trim()
  if (!msg || loading.value) return
  messages.value.push({ role: 'user', content: msg })
  input.value = ''
  loading.value = true
  await nextTick()
  scrollBottom()
  try {
    const data = await props.api('/api/ai/assistant', {
      method: 'POST',
      body: JSON.stringify({ messages: messages.value }),
      timeout: 120000,
    })
    messages.value.push({ role: 'assistant', content: data.reply })
  } catch (e) {
    messages.value.push({ role: 'error', content: e.message })
  } finally {
    loading.value = false
    await nextTick()
    scrollBottom()
  }
}

function clearChat() {
  messages.value = []
  props.showToast('对话已清空')
}

function scrollBottom() {
  if (chatBodyRef.value) {
    chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
  }
}

function positionDialog() {
  const gap = 12
  const dw = dlgW.value
  const dh = dlgH.value
  let x = btnX.value + gifSize.value + gap
  let y = btnY.value + gifSize.value - dh
  if (x + dw > window.innerWidth - 10) x = btnX.value - dw - gap
  if (y < 10) y = 10
  if (y + dh > window.innerHeight - 10) y = window.innerHeight - dh - 10
  dlgX.value = x
  dlgY.value = y
}

function toggleOpen() {
  open.value = !open.value
  if (open.value) {
    positionDialog()
    nextTick(scrollBottom)
  }
}
</script>

<template>
  <!-- Floating button -->
  <div
    class="ai-fab"
    :style="{ left: btnX + 'px', top: btnY + 'px', width: gifSize + 'px', height: gifSize + 'px' }"
    @mousedown="onBtnDown"
    @click="toggleOpen"
    :class="{ dragging: dragging === 'btn' }"
  >
    <img :src="'/' + gifs[currentGif]" alt="AI" class="ai-fab-gif" :style="{ width: gifSize + 'px', height: gifSize + 'px' }" />
  </div>

  <!-- Chat dialog -->
  <Teleport to="body">
    <Transition name="ai-dlg">
      <div
        v-if="open"
        class="ai-dialog"
        :style="{ left: dlgX + 'px', top: dlgY + 'px', width: dlgW + 'px', height: dlgH + 'px' }"
        @mousedown="onDlgDown"
      >
        <!-- Header -->
        <div class="ai-header">
          <div class="ai-header-left">
            <img :src="'/' + gifs[currentGif]" alt="BingBing" class="ai-header-avatar" />
            <div>
              <strong>BingBing</strong>
              <span class="ai-status">英语学习助手</span>
            </div>
          </div>
          <div class="ai-header-actions">
            <button @click="clearChat" title="清空对话"><RotateCcw :size="14" /></button>
            <button @click="open = false" title="最小化"><Minus :size="14" /></button>
          </div>
        </div>

        <!-- Body -->
        <div ref="chatBodyRef" class="chat-body">
          <div v-if="messages.length === 0" class="chat-empty">
            <img :src="'/waving.gif'" alt="" class="empty-gif" />
            <p>你好！我是 BingBing，你的英语学习助手。<br>有什么英语问题都可以问我哦～</p>
          </div>
          <div v-for="(msg, i) in messages" :key="i" class="chat-msg" :class="msg.role">
            <div class="chat-bubble">
              <pre>{{ msg.content }}</pre>
            </div>
          </div>
          <div v-if="loading" class="chat-msg assistant">
            <div class="chat-bubble typing">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="chat-input-row">
          <input
            v-model="input"
            class="chat-input"
            placeholder="问我任何英语问题..."
            @keydown.enter.prevent="send"
            :disabled="loading"
          />
          <button class="chat-send-btn" :disabled="!input.trim() || loading" @click="send">
            <Send :size="16" />
          </button>
        </div>

        <!-- Resize handle -->
        <div class="resize-handle" @mousedown="onResizeDown">
          <GripVertical :size="12" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* Floating button */
.ai-fab {
  position: fixed;
  z-index: 9999;
  cursor: pointer;
  transition: transform 200ms;
  user-select: none;
  -webkit-user-drag: none;
}

.ai-fab:hover {
  transform: scale(1.12);
  filter: drop-shadow(0 4px 12px rgba(42, 30, 18, 0.3));
}

.ai-fab.dragging {
  transition: none;
  cursor: grabbing;
}

.ai-fab-gif {
  object-fit: contain;
  pointer-events: none;
  -webkit-user-drag: none;
}

/* Dialog */
.ai-dialog {
  position: fixed;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line, #d8cbb8);
  background: var(--paper, #f4efe4);
  box-shadow: 0 32px 80px rgba(42, 30, 18, 0.25);
  overflow: hidden;
  user-select: none;
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line, #d8cbb8);
  background: rgba(255, 249, 236, 0.9);
  cursor: move;
  flex-shrink: 0;
}

.ai-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-header-left strong {
  font-size: 15px;
  font-family: var(--body-font, serif);
  display: block;
}

.ai-status {
  font-size: 11px;
  color: var(--muted, #756b5d);
}

.ai-header-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--line, #d8cbb8);
}

.ai-header-actions {
  display: flex;
  gap: 6px;
}

.ai-header-actions button {
  width: 28px;
  height: 28px;
  border: 1px solid var(--line, #d8cbb8);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--muted, #756b5d);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 160ms;
}

.ai-header-actions button:hover {
  color: var(--ink, #223b32);
  border-color: var(--gold, #af8744);
}

/* Chat body */
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: default;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--muted, #756b5d);
  text-align: center;
}

.empty-gif {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
}

.chat-empty p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
}

.chat-msg {
  display: flex;
  max-width: 85%;
  animation: msgIn 300ms var(--ease-out, ease) both;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-msg.user {
  align-self: flex-end;
}

.chat-msg.error {
  align-self: stretch;
  max-width: 100%;
}

.chat-bubble {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid var(--line, #d8cbb8);
  background: var(--paper-2, #fff9ec);
  overflow-x: auto;
}

.chat-bubble pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--body-font, serif);
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
  color: var(--red, #8b3a3a);
  width: 100%;
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
  background: var(--muted, #756b5d);
  animation: dotPulse 1.2s ease-in-out infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

/* Input */
.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--line, #d8cbb8);
  background: rgba(255, 249, 236, 0.6);
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  height: 40px;
  padding: 0 14px;
  border: 1px solid var(--line, #d8cbb8);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--ink, #223b32);
  font-family: var(--body-font, serif);
  font-size: 14px;
  outline: none;
}

.chat-input:focus {
  border-color: var(--gold, #af8744);
}

.chat-input:disabled {
  opacity: 0.6;
}

.chat-send-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--ink, #223b32);
  border-radius: 6px;
  background: var(--ink, #223b32);
  color: #fff8e8;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 160ms;
}

.chat-send-btn:hover:not(:disabled) {
  background: #1a2f28;
  transform: translateY(-1px);
}

.chat-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Resize handle */
.resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 20px;
  height: 20px;
  cursor: nwse-resize;
  display: grid;
  place-items: center;
  color: var(--muted, #756b5d);
  opacity: 0.4;
  transition: opacity 160ms;
}

.resize-handle:hover {
  opacity: 0.8;
}

/* Transition */
.ai-dlg-enter-active {
  animation: dlgIn 300ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

.ai-dlg-leave-active {
  animation: dlgOut 200ms ease-in forwards;
}

@keyframes dlgIn {
  from { opacity: 0; transform: scale(0.9) translateY(12px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

@keyframes dlgOut {
  from { opacity: 1; transform: scale(1) translateY(0); }
  to { opacity: 0; transform: scale(0.9) translateY(12px); }
}
</style>
