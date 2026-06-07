<script setup>
import { ref, computed } from 'vue'
import { Bar, Pie, Line } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  ArcElement, PointElement, LineElement, Filler,
  Title, Tooltip, Legend,
} from 'chart.js'
import Heatmap from './Heatmap.vue'

ChartJS.register(
  CategoryScale, LinearScale, BarElement,
  ArcElement, PointElement, LineElement, Filler,
  Title, Tooltip, Legend,
)

const props = defineProps({
  stats: Object,
  api: Function,
})

const chartDays = ref(30)

const allEvents = computed(() => {
  return (props.stats?.events || []).slice().reverse()
})

const chartEvents = computed(() => {
  return allEvents.value.slice(-chartDays.value)
})

const barData = computed(() => ({
  labels: chartEvents.value.map(item => item.day.slice(5)),
  datasets: [{
    data: chartEvents.value.map(item => item.total),
    backgroundColor: 'rgba(139, 58, 58, 0.8)',
    borderRadius: 4,
    borderSkipped: false,
    barPercentage: 0.7,
  }],
}))

const barOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        color: '#665a4c',
        maxRotation: 60,
        autoSkip: true,
        maxTicksLimit: chartDays.value > 60 ? 30 : undefined,
      },
    },
    y: {
      allowDecimals: false,
      ticks: { color: '#665a4c' },
      grid: { color: 'rgba(216, 203, 184, 0.4)' },
    },
  },
}))

const pieData = computed(() => {
  const c = props.stats?.counts || {}
  return {
    labels: ['待学习', '学习中', '已掌握'],
    datasets: [{
      data: [c.new_total || 0, c.learning || 0, c.mastered || 0],
      backgroundColor: [
        'rgba(175, 135, 68, 0.8)',
        'rgba(111, 134, 111, 0.8)',
        'rgba(34, 59, 50, 0.8)',
      ],
      borderColor: '#fff9ec',
      borderWidth: 2,
    }],
  }
})

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#756b5d', font: { size: 12 }, padding: 16 },
    },
  },
}

const lineData = computed(() => ({
  labels: chartEvents.value.map(item => item.day.slice(5)),
  datasets: [{
    label: '学习量',
    data: chartEvents.value.map(item => item.total),
    borderColor: '#8b3a3a',
    backgroundColor: 'rgba(139, 58, 58, 0.08)',
    fill: true,
    tension: 0.4,
    pointBackgroundColor: '#8b3a3a',
    pointRadius: chartDays.value > 60 ? 1.5 : 3,
    pointHoverRadius: 6,
  }],
}))

const lineOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        color: '#665a4c',
        maxRotation: 60,
        autoSkip: true,
        maxTicksLimit: chartDays.value > 60 ? 30 : undefined,
      },
    },
    y: {
      allowDecimals: false,
      ticks: { color: '#665a4c' },
      grid: { color: 'rgba(216, 203, 184, 0.4)' },
    },
  },
}))
</script>

<template>
  <section id="stats" class="stats-section">
    <div class="section-heading">
      <p class="eyebrow">Progress</p>
      <h2>学习痕迹</h2>
    </div>

    <!-- 数据概览 -->
    <div class="stats-grid">
      <article v-spotlight class="stat-card" style="--i: 0">
        <span>总单词</span>
        <strong>{{ stats?.counts?.total || 0 }}</strong>
      </article>
      <article v-spotlight class="stat-card" style="--i: 1">
        <span>待学习</span>
        <strong>{{ stats?.counts?.new_total || 0 }}</strong>
      </article>
      <article v-spotlight class="stat-card" style="--i: 2">
        <span>学习中</span>
        <strong>{{ stats?.counts?.learning || 0 }}</strong>
      </article>
      <article v-spotlight class="stat-card" style="--i: 3">
        <span>已掌握</span>
        <strong>{{ stats?.counts?.mastered || 0 }}</strong>
      </article>
    </div>

    <!-- 时间范围选择 -->
    <div class="range-bar">
      <span class="range-label">数据范围</span>
      <div class="chart-range">
        <button :class="{ active: chartDays === 14 }" @click="chartDays = 14">14天</button>
        <button :class="{ active: chartDays === 30 }" @click="chartDays = 30">30天</button>
        <button :class="{ active: chartDays === 90 }" @click="chartDays = 90">90天</button>
        <button :class="{ active: chartDays === 365 }" @click="chartDays = 365">全部</button>
      </div>
      <span class="range-hint">共 {{ allEvents.length }} 天数据</span>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 每日学习量柱状图 -->
      <article v-spotlight class="chart-card">
        <h3>每日学习量</h3>
        <div class="chart-container">
          <Bar :data="barData" :options="barOptions" />
        </div>
      </article>

      <!-- 单词状态饼图 -->
      <article v-spotlight class="chart-card">
        <h3>单词状态分布</h3>
        <div class="chart-container chart-container-pie">
          <Pie :data="pieData" :options="pieOptions" />
        </div>
      </article>

      <!-- 学习趋势折线图 -->
      <article v-spotlight class="chart-card chart-card-wide">
        <h3>学习趋势</h3>
        <div class="chart-container">
          <Line :data="lineData" :options="lineOptions" />
        </div>
      </article>
    </div>

    <!-- 热力图 -->
    <Heatmap :api="api" />
  </section>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(130px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  position: relative;
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 20px;
  transition: all 260ms cubic-bezier(0.16, 1, 0.3, 1);
  animation: statCardIn 400ms cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: calc(var(--i, 0) * 80ms + 100ms);
}

@keyframes statCardIn {
  from { opacity: 0; transform: translateY(16px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 32px 80px rgba(42, 30, 18, 0.18);
}

.stat-card span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.stat-card strong {
  display: block;
  margin-top: 8px;
  font-size: 38px;
  font-variant-numeric: tabular-nums;
}

.range-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
}

.range-label {
  font-size: 13px;
  color: var(--muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.chart-range {
  display: flex;
  gap: 4px;
}

.chart-range button {
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 6px 14px;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--muted);
  cursor: pointer;
  font-family: inherit;
  transition: all 160ms cubic-bezier(0.16, 1, 0.3, 1);
}

.chart-range button:hover {
  transform: translateY(-1px);
  border-color: var(--gold);
  color: var(--ink);
}

.chart-range button:active {
  transform: translateY(0) scale(0.97);
}

.chart-range button.active {
  background: var(--ink);
  color: #fff8e8;
  border-color: var(--ink);
}

.range-hint {
  font-size: 12px;
  color: var(--muted);
  margin-left: auto;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  position: relative;
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 20px;
  transition: all 260ms cubic-bezier(0.16, 1, 0.3, 1);
}

.chart-card:hover {
  box-shadow: 0 32px 80px rgba(42, 30, 18, 0.18);
}

.chart-card-wide {
  grid-column: 1 / -1;
}

.chart-card h3 {
  font-size: 15px;
  font-weight: 500;
  margin: 0 0 16px;
  color: var(--ink);
}

.chart-container {
  height: 260px;
}

.chart-container-pie {
  height: 280px;
}

@media (max-width: 720px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .range-bar { flex-wrap: wrap; }
}
</style>
