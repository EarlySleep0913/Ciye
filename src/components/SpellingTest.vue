<script setup>
import { ref, computed, onMounted } from 'vue'
import { Check, X, ArrowRight, RotateCcw, Loader2, Trophy, Volume2 } from 'lucide-vue-next'

const props = defineProps({
  api: Function,
  speak: Function,
  showToast: Function,
})

// State
const phase = ref('setup') // 'setup' | 'testing' | 'result'
const rangeType = ref('all')
const questionCount = ref(20)
const words = ref([])
const loading = ref(false)
const currentIndex = ref(0)
const userAnswer = ref('')
const feedback = ref(null) // null | { correct: boolean, correctWord: string }
const score = ref({ correct: 0, wrong: 0 })
const wrongList = ref([])
const inputRef = ref(null)

const currentWord = computed(() => words.value[currentIndex.value])
const progress = computed(() =>
  words.value.length ? Math.round(((currentIndex.value) / words.value.length) * 100) : 0
)
const isFinished = computed(() => currentIndex.value >= words.value.length && words.value.length > 0)

const rangeOptions = [
  { value: 'all', label: '全部单词', desc: '从当前词书中随机抽取' },
  { value: 'today', label: '今日学过的词', desc: '测试今天学习的单词' },
  { value: 'wrong', label: '错词本', desc: '针对性复习错词' },
]

async function startTest() {
  loading.value = true
  try {
    const data = await props.api(
      `/api/test/words?range=${rangeType.value}&limit=${questionCount.value}`
    )
    if (data.words.length === 0) {
      props.showToast('没有可测试的单词')
      return
    }
    words.value = data.words
    currentIndex.value = 0
    userAnswer.value = ''
    feedback.value = null
    score.value = { correct: 0, wrong: 0 }
    wrongList.value = []
    phase.value = 'testing'
    setTimeout(() => inputRef.value?.focus(), 100)
  } catch (e) {
    props.showToast(e.message)
  } finally {
    loading.value = false
  }
}

async function submitAnswer() {
  if (feedback.value) {
    // Already showing feedback, go to next
    nextQuestion()
    return
  }
  if (!userAnswer.value.trim()) return

  const word = currentWord.value
  try {
    const result = await props.api('/api/test/check', {
      method: 'POST',
      body: JSON.stringify({
        word_id: word.id,
        answer: userAnswer.value.trim(),
      }),
    })
    feedback.value = result
    if (result.correct) {
      score.value.correct++
    } else {
      score.value.wrong++
      wrongList.value.push({
        ...word,
        userAnswer: userAnswer.value.trim(),
      })
    }
  } catch (e) {
    props.showToast(e.message)
  }
}

function nextQuestion() {
  currentIndex.value++
  userAnswer.value = ''
  feedback.value = null
  if (isFinished.value) {
    phase.value = 'result'
  } else {
    setTimeout(() => inputRef.value?.focus(), 100)
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    submitAnswer()
  }
}

function restart() {
  phase.value = 'setup'
  words.value = []
}

onMounted(() => {
  phase.value = 'setup'
})
</script>

<template>
  <section class="spelling-page">
    <!-- Setup Phase -->
    <div v-if="phase === 'setup'" class="setup-card">
      <div class="setup-header">
        <p class="eyebrow">Spelling Test</p>
        <h2>拼写测试</h2>
        <p class="setup-desc">看中文释义，输入英文单词。即时判对错，错了自动加入错词本。</p>
      </div>

      <div class="setup-form">
        <div class="form-section">
          <label>测试范围</label>
          <div class="range-options">
            <button
              v-for="opt in rangeOptions"
              :key="opt.value"
              class="range-btn"
              :class="{ active: rangeType === opt.value }"
              @click="rangeType = opt.value"
            >
              <span class="range-label">{{ opt.label }}</span>
              <span class="range-desc">{{ opt.desc }}</span>
            </button>
          </div>
        </div>

        <div class="form-section">
          <label>题目数量</label>
          <div class="count-row">
            <input
              type="range"
              min="5"
              max="100"
              step="5"
              v-model.number="questionCount"
            />
            <strong>{{ questionCount }} 题</strong>
          </div>
        </div>

        <button class="primary-btn start-btn" :disabled="loading" @click="startTest">
          <Loader2 v-if="loading" class="spin" :size="18" />
          <template v-else>开始测试</template>
        </button>
      </div>
    </div>

    <!-- Testing Phase -->
    <div v-else-if="phase === 'testing'" class="test-card">
      <div class="test-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <span class="progress-text">{{ currentIndex + 1 }} / {{ words.length }}</span>
      </div>

      <div class="score-strip">
        <span class="score-correct">✓ {{ score.correct }}</span>
        <span class="score-wrong">✗ {{ score.wrong }}</span>
      </div>

      <div class="question-area" v-if="currentWord">
        <p class="field-label">中文释义</p>
        <h2 class="translation-text">{{ currentWord.translation || '暂无释义' }}</h2>

        <div class="answer-area">
          <div class="input-row">
            <input
              ref="inputRef"
              v-model="userAnswer"
              type="text"
              class="answer-input"
              :class="{ correct: feedback?.correct, wrong: feedback && !feedback.correct }"
              placeholder="输入英文单词..."
              :disabled="!!feedback"
              @keydown="handleKeydown"
              autocomplete="off"
              spellcheck="false"
            />
            <button
              v-if="!feedback"
              class="submit-btn"
              :disabled="!userAnswer.trim()"
              @click="submitAnswer"
            >
              确认
            </button>
            <button
              v-else
              class="next-btn"
              @click="nextQuestion"
            >
              <ArrowRight :size="18" />
              {{ isFinished ? '查看结果' : '下一题' }}
            </button>
          </div>

          <!-- Feedback -->
          <div v-if="feedback" class="feedback-area">
            <div v-if="feedback.correct" class="feedback-correct">
              <Check :size="20" />
              <span>正确！</span>
            </div>
            <div v-else class="feedback-wrong">
              <X :size="20" />
              <div>
                <span>错误</span>
                <p class="correct-answer">
                  正确答案：<strong>{{ feedback.correct_word }}</strong>
                </p>
                <p class="your-answer" v-if="feedback.user_answer">
                  你的答案：{{ feedback.user_answer }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Result Phase -->
    <div v-else-if="phase === 'result'" class="result-card">
      <div class="result-header">
        <Trophy :size="48" />
        <h2>测试完成</h2>
      </div>

      <div class="result-score">
        <div class="score-circle">
          <span class="score-num">{{ words.length ? Math.round(score.correct / words.length * 100) : 0 }}</span>
          <span class="score-unit">%</span>
        </div>
        <p class="score-detail">
          共 {{ words.length }} 题，答对 {{ score.correct }} 题，答错 {{ score.wrong }} 题
        </p>
      </div>

      <div v-if="wrongList.length > 0" class="wrong-review">
        <h3>错词回顾</h3>
        <div class="wrong-list">
          <div v-for="w in wrongList" :key="w.id" class="wrong-item">
            <div class="wrong-word">{{ w.word }}</div>
            <div class="wrong-detail">
              <span class="wrong-translation">{{ w.translation }}</span>
              <span class="wrong-your">你的答案：{{ w.userAnswer }}</span>
            </div>
            <button class="icon-btn" title="播放发音" @click="speak(w)">
              <Volume2 :size="14" />
            </button>
          </div>
        </div>
      </div>

      <div class="result-actions">
        <button class="primary-btn" @click="startTest">
          <RotateCcw :size="16" /> 再来一次
        </button>
        <button class="quiet-btn" @click="restart">返回选择</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.spelling-page { position: relative; }

/* ── Setup ── */
.setup-card {
  max-width: 560px;
  margin: 0 auto;
  border: 1px solid var(--line);
  background: rgba(255,249,236,0.86);
  box-shadow: var(--shadow);
  padding: 36px;
}

.setup-header { text-align: center; margin-bottom: 32px; }
.setup-header h2 {
  font-family: var(--display-font);
  font-size: 34px;
  font-weight: 400;
  margin: 8px 0 12px;
}
.setup-desc { color: var(--muted); line-height: 1.6; }

.setup-form { display: flex; flex-direction: column; gap: 24px; }
.form-section label {
  display: block;
  font-size: 13px;
  color: var(--muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.range-options { display: grid; gap: 10px; }
.range-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255,255,255,0.5);
  cursor: pointer;
  transition: all 160ms;
  text-align: left;
  font-family: inherit;
}
.range-btn:hover { border-color: var(--gold); }
.range-btn.active {
  border-color: var(--ink);
  background: rgba(34,59,50,0.05);
}
.range-label { font-size: 15px; font-weight: 500; color: var(--ink); }
.range-desc { font-size: 13px; color: var(--muted); }

.count-row {
  display: grid;
  grid-template-columns: 1fr 60px;
  align-items: center;
  gap: 14px;
}
.count-row strong { font-size: 18px; text-align: center; }

.start-btn {
  width: 100%;
  justify-content: center;
  height: 50px;
  font-size: 16px;
}

/* ── Testing ── */
.test-card {
  max-width: 640px;
  margin: 0 auto;
  border: 1px solid var(--line);
  background: rgba(255,249,236,0.86);
  box-shadow: var(--shadow);
  padding: 36px;
  position: relative;
}

.test-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--line);
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--sage);
  border-radius: 3px;
  transition: width 300ms ease;
}
.progress-text {
  font-size: 13px;
  color: var(--muted);
  white-space: nowrap;
}

.score-strip {
  display: flex;
  gap: 16px;
  margin-bottom: 28px;
  font-size: 14px;
}
.score-correct { color: var(--sage); font-weight: 600; }
.score-wrong { color: var(--red); font-weight: 600; }

.question-area { text-align: center; }

.translation-text {
  font-family: var(--body-font);
  font-size: clamp(28px, 5vw, 42px);
  font-weight: 500;
  color: var(--ink);
  margin: 8px 0 32px;
  line-height: 1.4;
}

.answer-area { max-width: 420px; margin: 0 auto; }

.input-row {
  display: flex;
  gap: 10px;
}

.answer-input {
  flex: 1;
  height: 50px;
  padding: 0 16px;
  border: 2px solid var(--line);
  border-radius: 6px;
  background: rgba(255,255,255,0.6);
  color: var(--ink);
  font-family: var(--english-display);
  font-size: 20px;
  font-weight: 600;
  text-align: center;
  outline: none;
  transition: border-color 200ms;
}
.answer-input:focus { border-color: var(--gold); }
.answer-input.correct { border-color: var(--sage); background: rgba(111,134,111,0.05); }
.answer-input.wrong { border-color: var(--red); background: rgba(139,58,58,0.05); }

.submit-btn, .next-btn {
  height: 50px;
  padding: 0 20px;
  border: 1px solid var(--ink);
  border-radius: 6px;
  background: var(--ink);
  color: #fff8e8;
  font-family: inherit;
  font-size: 15px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.feedback-area {
  margin-top: 20px;
  text-align: left;
}

.feedback-correct {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(111,134,111,0.1);
  border: 1px solid rgba(111,134,111,0.3);
  border-radius: 6px;
  color: var(--sage);
  font-size: 16px;
  font-weight: 600;
}

.feedback-wrong {
  display: flex;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(139,58,58,0.06);
  border: 1px solid rgba(139,58,58,0.25);
  border-radius: 6px;
  color: var(--red);
}
.feedback-wrong span { font-size: 16px; font-weight: 600; }
.correct-answer {
  margin: 6px 0 0;
  color: var(--ink);
  font-size: 15px;
}
.correct-answer strong {
  font-family: var(--english-display);
  font-size: 20px;
  color: var(--sage);
}
.your-answer {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
}

/* ── Result ── */
.result-card {
  max-width: 560px;
  margin: 0 auto;
  border: 1px solid var(--line);
  background: rgba(255,249,236,0.86);
  box-shadow: var(--shadow);
  padding: 36px;
  text-align: center;
}

.result-header { margin-bottom: 24px; }
.result-header h2 {
  font-family: var(--display-font);
  font-size: 34px;
  font-weight: 400;
  margin: 12px 0 0;
}

.result-score { margin-bottom: 28px; }
.score-circle {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
}
.score-num {
  font-family: var(--english-display);
  font-size: 72px;
  font-weight: 700;
  color: var(--ink);
}
.score-unit {
  font-size: 24px;
  color: var(--muted);
}
.score-detail {
  color: var(--muted);
  margin: 8px 0 0;
}

.wrong-review {
  text-align: left;
  margin-bottom: 28px;
}
.wrong-review h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: var(--red);
}
.wrong-list { display: grid; gap: 8px; }
.wrong-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255,255,255,0.5);
}
.wrong-word {
  font-family: var(--english-display);
  font-size: 18px;
  font-weight: 600;
  min-width: 100px;
}
.wrong-detail { flex: 1; font-size: 13px; }
.wrong-translation { color: var(--ink); display: block; }
.wrong-your { color: var(--muted); }

.icon-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: rgba(255,255,255,0.5);
  color: var(--muted);
  display: grid;
  place-items: center;
  cursor: pointer;
}
.icon-btn:hover { color: var(--ink); border-color: var(--ink); }

.result-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.result-actions .quiet-btn {
  border: 1px solid var(--line);
  background: var(--paper-2);
  color: var(--ink);
  border-radius: 6px;
  min-height: 42px;
  padding: 10px 20px;
  font-family: inherit;
  cursor: pointer;
}

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 900ms linear infinite; }
</style>
