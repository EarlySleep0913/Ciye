<script setup>
import { ref, computed, onMounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js'
import { AlertTriangle, Brain, TrendingUp, Shield, Volume2, Search } from 'lucide-vue-next'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const props = defineProps({
  api: Function,
  speak: Function,
  showToast: Function,
  lookupWord: Function,
})

const overview = ref(null)
const reviewWords = ref([])
const selectedWord = ref(null)
const wordDetail = ref(null)
const loading = ref(false)
const activeTab = ref('overview') // 'overview' | 'review' | 'curve'

async function loadData() {
  loading.value = true
  try {
    const [ov, rq] = await Promise.all([
      props.api('/api/ebbinghaus'),
      props.api('/api/ebbinghaus/review'),
    ])
    overview.value = ov
    reviewWords.value = rq.words || []
  } catch (e) {
    props.showToast(e.message)
  } finally {
    loading.value = false
  }
}

async function showWordDetail(wordId) {
  try {
    wordDetail.value = await props.api(`/api/ebbinghaus/word/${wordId}`)
    activeTab.value = 'curve'
  } catch (e) {
    props.showToast(e.message)
  }
}

// 遗忘曲线图数据
const curveChartData = computed(() => {
  if (!overview.value?.curve_data) return null
  const colors = {
    '1.0': '#8b3a3a',
    '2.0': '#af8744',
    '4.0': '#6f866f',
    '7.0': '#223b32',
    '10.0': '#756b5d',
  }
  const datasets = Object.entries(overview.value.curve_data).map(([strength, points]) => ({
    label: `S=${strength}`,
    data: points.map(p => p.retention),
    borderColor: colors[strength] || '#999',
    backgroundColor: 'transparent',
    tension: 0.4,
    pointRadius: 0,
    borderWidth: 2,
  }))

  return {
    labels: Array.from({ length: 31 }, (_, i) => i),
    datasets,
  }
})

const curveChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#756b5d', font: { size: 11 }, padding: 12 },
    },
    tooltip: {
      callbacks: {
        title: (items) => `第 ${items[0].label} 天`,
        label: (item) => `保持率 ${item.raw}%`,
      },
    },
  },
  scales: {
    x: {
      title: { display: true, text: '天数', color: '#756b5d' },
      grid: { display: false },
      ticks: { color: '#665a4c' },
    },
    y: {
      title: { display: true, text: '记忆保持率 (%)', color: '#756b5d' },
      min: 0,
      max: 100,
      ticks: { color: '#665a4c' },
      grid: { color: 'rgba(216, 203, 184, 0.3)' },
    },
  },
}

// 单词详情遗忘曲线
const wordCurveData = computed(() => {
  if (!wordDetail.value?.curve) return null
  return {
    labels: wordDetail.value.curve.map(p => p.day),
    datasets: [
      {
        label: '记忆保持率',
        data: wordDetail.value.curve.map(p => p.retention),
        borderColor: '#8b3a3a',
        backgroundColor: 'rgba(139, 58, 58, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        borderWidth: 2,
      },
      {
        label: '复习阈值 (60%)',
        data: Array(31).fill(60),
        borderColor: 'rgba(175, 135, 68, 0.5)',
        borderDash: [6, 4],
        pointRadius: 0,
        borderWidth: 1.5,
        fill: false,
      },
    ],
  }
})

const wordCurveOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#756b5d', font: { size: 11 }, padding: 12 },
    },
  },
  scales: {
    x: {
      title: { display: true, text: '天数', color: '#756b5d' },
      grid: { display: false },
      ticks: { color: '#665a4c' },
    },
    y: {
      min: 0,
      max: 100,
      ticks: { color: '#665a4c' },
      grid: { color: 'rgba(216, 203, 184, 0.3)' },
    },
  },
}

onMounted(loadData)
</script>

<template>
  <section class="ebbinghaus-page">
    <div class="section-heading">
      <p class="eyebrow">Ebbinghaus Forgetting Curve</p>
      <h2>艾宾浩斯遗忘曲线</h2>
    </div>

    <!-- Tab 切换 -->
    <div class="eb-tabs">
      <button :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">
        <Brain :size="16" /> 记忆总览
      </button>
      <button :class="{ active: activeTab === 'review' }" @click="activeTab = 'review'">
        <AlertTriangle :size="16" /> 待复习
        <span v-if="reviewWords.length" class="tab-badge">{{ reviewWords.length }}</span>
      </button>
      <button :class="{ active: activeTab === 'curve' }" @click="activeTab = 'curve'">
        <TrendingUp :size="16" /> 遗忘曲线
      </button>
    </div>

    <!-- 记忆总览 -->
    <div v-if="activeTab === 'overview'" class="eb-content">
      <div class="overview-cards" v-if="overview">
        <article v-spotlight class="ov-card ov-retention">
          <div class="ov-icon"><Brain :size="24" /></div>
          <div class="ov-body">
            <span class="ov-label">平均保持率</span>
            <strong class="ov-value">{{ overview.avg_retention }}%</strong>
          </div>
        </article>
        <article v-spotlight class="ov-card ov-risk">
          <div class="ov-icon"><AlertTriangle :size="24" /></div>
          <div class="ov-body">
            <span class="ov-label">即将遗忘</span>
            <strong class="ov-value">{{ overview.at_risk }} 词</strong>
          </div>
        </article>
        <article v-spotlight class="ov-card ov-strong">
          <div class="ov-icon"><Shield :size="24" /></div>
          <div class="ov-body">
            <span class="ov-label">记忆牢固</span>
            <strong class="ov-value">{{ overview.strong }} 词</strong>
          </div>
        </article>
        <article v-spotlight class="ov-card ov-total">
          <div class="ov-icon"><TrendingUp :size="24" /></div>
          <div class="ov-body">
            <span class="ov-label">已学习</span>
            <strong class="ov-value">{{ overview.total }} 词</strong>
          </div>
        </article>
      </div>

      <!-- 记忆分布 -->
      <div v-spotlight class="distribution-card" v-if="overview">
        <h3>记忆强度分布</h3>
        <div class="dist-bars">
          <div class="dist-row">
            <span class="dist-label">牢固 (S≥4)</span>
            <div class="dist-bar">
              <div class="dist-fill strong" :style="{ width: (overview.total ? overview.strong / overview.total * 100 : 0) + '%' }"></div>
            </div>
            <span class="dist-count">{{ overview.strong }}</span>
          </div>
          <div class="dist-row">
            <span class="dist-label">中等 (2≤S<4)</span>
            <div class="dist-bar">
              <div class="dist-fill moderate" :style="{ width: (overview.total ? overview.moderate / overview.total * 100 : 0) + '%' }"></div>
            </div>
            <span class="dist-count">{{ overview.moderate }}</span>
          </div>
          <div class="dist-row">
            <span class="dist-label">薄弱 (S<2)</span>
            <div class="dist-bar">
              <div class="dist-fill weak" :style="{ width: (overview.total ? overview.weak / overview.total * 100 : 0) + '%' }"></div>
            </div>
            <span class="dist-count">{{ overview.weak }}</span>
          </div>
        </div>
      </div>

      <!-- 标准遗忘曲线图 -->
      <div v-spotlight class="curve-card" v-if="curveChartData">
        <h3>不同记忆强度的遗忘曲线</h3>
        <p class="curve-desc">记忆强度 S 越大，遗忘越慢。每次成功回忆会增强 S。</p>
        <div class="chart-container">
          <Line :data="curveChartData" :options="curveChartOptions" />
        </div>
      </div>
    </div>

    <!-- 待复习列表 -->
    <div v-if="activeTab === 'review'" class="eb-content">
      <div v-if="reviewWords.length === 0" class="empty-state">
        <Shield :size="48" />
        <p>目前没有需要复习的单词，记忆保持良好！</p>
      </div>
      <div v-else class="review-list">
        <div class="review-header">
          <span>共 {{ reviewWords.length }} 个词需要复习</span>
          <span class="review-hint">保持率低于 60% 的词会出现在这里</span>
        </div>
        <div v-for="w in reviewWords" :key="w.id" class="review-item" @click="showWordDetail(w.id)">
          <div class="review-word">
            <strong>{{ w.word }}</strong>
            <span class="review-trans">{{ w.translation }}</span>
          </div>
          <div class="review-meta">
            <div class="retention-badge" :class="{ danger: w.retention < 30, warn: w.retention < 60 }">
              {{ w.retention }}%
            </div>
            <div class="review-info">
              <span>S={{ w.strength }}</span>
              <span>{{ w.days_since }}天未复习</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 遗忘曲线详情 -->
    <div v-if="activeTab === 'curve'" class="eb-content">
      <div v-if="!wordDetail" class="curve-placeholder">
        <TrendingUp :size="48" />
        <p>点击"待复习"列表中的单词，查看其遗忘曲线详情</p>
      </div>
      <div v-else class="word-detail">
        <div class="wd-header">
          <div>
            <h3>{{ wordDetail.word_id ? '' : '' }}单词遗忘曲线</h3>
            <p class="wd-formula">R = e<sup>-t/S</sup> · S={{ wordDetail.memory_strength }} · 当前保持率 {{ wordDetail.current_retention }}%</p>
          </div>
          <button class="quiet-btn" @click="activeTab = 'review'">返回列表</button>
        </div>

        <div class="wd-stats">
          <div class="wd-stat">
            <span>记忆强度</span>
            <strong>S={{ wordDetail.memory_strength }}</strong>
          </div>
          <div class="wd-stat">
            <span>当前保持率</span>
            <strong :class="{ danger: wordDetail.at_risk }">{{ wordDetail.current_retention }}%</strong>
          </div>
          <div class="wd-stat">
            <span>复习间隔</span>
            <strong>{{ wordDetail.review_interval }} 天</strong>
          </div>
          <div class="wd-stat">
            <span>距上次学习</span>
            <strong>{{ wordDetail.days_elapsed }} 天</strong>
          </div>
        </div>

        <div class="chart-container">
          <Line v-if="wordCurveData" :data="wordCurveData" :options="wordCurveOptions" />
        </div>

        <!-- 学习历史 -->
        <div class="wd-history" v-if="wordDetail.history?.length">
          <h4>学习历史</h4>
          <div class="history-list">
            <div v-for="(h, i) in wordDetail.history" :key="i" class="history-item">
              <span class="history-date">{{ h.date }}</span>
              <span class="history-action" :class="h.action">{{ h.action }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ebbinghaus-page { position: relative; }

.eb-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.eb-tabs button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 249, 236, 0.86);
  color: var(--muted);
  font-family: inherit;
  font-size: 14px;
  cursor: pointer;
  transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1);
}

.eb-tabs button:hover {
  transform: translateY(-1px);
  border-color: var(--gold);
  color: var(--ink);
}

.eb-tabs button:active {
  transform: translateY(0) scale(0.97);
}

.eb-tabs button.active {
  background: var(--ink);
  color: #fff8e8;
  border-color: var(--ink);
  box-shadow: 0 4px 12px rgba(34, 59, 50, 0.2);
}

.tab-badge {
  font-size: 11px;
  padding: 1px 7px;
  background: var(--red);
  color: white;
  border-radius: 10px;
}

.eb-content { display: grid; gap: 20px; }

/* Overview cards */
.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.ov-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  transition: all 260ms cubic-bezier(0.16, 1, 0.3, 1);
  animation: ovCardIn 400ms cubic-bezier(0.16, 1, 0.3, 1) both;
}

.ov-card:nth-child(1) { animation-delay: 80ms; }
.ov-card:nth-child(2) { animation-delay: 160ms; }
.ov-card:nth-child(3) { animation-delay: 240ms; }
.ov-card:nth-child(4) { animation-delay: 320ms; }

@keyframes ovCardIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.ov-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 32px 80px rgba(42, 30, 18, 0.16);
}

.ov-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  flex-shrink: 0;
}

.ov-retention .ov-icon { background: rgba(34, 59, 50, 0.1); color: var(--ink); }
.ov-risk .ov-icon { background: rgba(139, 58, 58, 0.1); color: var(--red); }
.ov-strong .ov-icon { background: rgba(111, 134, 111, 0.1); color: var(--sage); }
.ov-total .ov-icon { background: rgba(175, 135, 68, 0.1); color: var(--gold); }

.ov-label {
  display: block;
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.ov-value {
  font-size: 24px;
  font-family: var(--english-display);
}

/* Distribution */
.distribution-card {
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 24px;
}

.distribution-card h3 {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 20px;
}

.dist-bars { display: grid; gap: 14px; }

.dist-row {
  display: grid;
  grid-template-columns: 100px 1fr 50px;
  align-items: center;
  gap: 12px;
}

.dist-label {
  font-size: 13px;
  color: var(--muted);
}

.dist-bar {
  height: 20px;
  background: rgba(216, 203, 184, 0.3);
  border-radius: 4px;
  overflow: hidden;
}

.dist-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 800ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

.dist-fill.strong { background: var(--sage); }
.dist-fill.moderate { background: var(--gold); }
.dist-fill.weak { background: var(--red); }

.dist-count {
  font-size: 14px;
  font-weight: 600;
  text-align: right;
}

/* Curve card */
.curve-card {
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 24px;
}

.curve-card h3 {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 4px;
}

.curve-desc {
  font-size: 13px;
  color: var(--muted);
  margin: 0 0 16px;
}

.chart-container {
  height: 300px;
}

/* Review list */
.review-list {
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  font-size: 14px;
}

.review-hint {
  font-size: 12px;
  color: var(--muted);
}

.review-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(216, 203, 184, 0.3);
  cursor: pointer;
  transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1);
}

.review-item:hover {
  background: rgba(175, 135, 68, 0.05);
  transform: translateX(3px);
}

.review-item:active {
  transform: translateX(1px);
}

.review-word strong {
  font-family: var(--english-display);
  font-size: 18px;
  display: block;
}

.review-trans {
  font-size: 13px;
  color: var(--muted);
}

.review-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.retention-badge {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(111, 134, 111, 0.15);
  color: var(--sage);
}

.retention-badge.warn {
  background: rgba(175, 135, 68, 0.15);
  color: var(--gold);
}

.retention-badge.danger {
  background: rgba(139, 58, 58, 0.15);
  color: var(--red);
}

.review-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: var(--muted);
  text-align: right;
}

/* Word detail */
.word-detail {
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 24px;
}

.wd-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.wd-header h3 {
  font-size: 18px;
  font-weight: 500;
  margin: 0 0 4px;
}

.wd-formula {
  font-size: 13px;
  color: var(--muted);
  font-family: var(--english-display);
}

.wd-formula sup {
  font-size: 0.7em;
}

.wd-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.wd-stat {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
  text-align: center;
}

.wd-stat span {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}

.wd-stat strong {
  font-size: 20px;
  font-family: var(--english-display);
}

.wd-stat strong.danger { color: var(--red); }

.wd-history {
  margin-top: 20px;
}

.wd-history h4 {
  font-size: 14px;
  font-weight: 500;
  margin: 0 0 12px;
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  font-size: 12px;
}

.history-date { color: var(--muted); }

.history-action {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 11px;
}

.history-action.forgot { color: var(--red); }
.history-action.vague { color: var(--gold); }
.history-action.known { color: var(--sage); }
.history-action.easy { color: var(--ink); }

.curve-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: var(--muted);
  gap: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: var(--muted);
  gap: 16px;
}

@media (max-width: 720px) {
  .overview-cards { grid-template-columns: repeat(2, 1fr); }
  .wd-stats { grid-template-columns: repeat(2, 1fr); }
  .eb-tabs { flex-wrap: wrap; }
}
</style>
