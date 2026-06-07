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

// 图表显示天数
const chartDays = ref(30)

const allEvents = computed(() => {
  return (props.stats?.events || []).slice().reverse()
})

const chartEvents = computed(() => {
  return allEvents.value.slice(-chartDays.value)
})

// Bar chart
const barData = computed(() => ({
  labels: chartEvents.value.map(item => item.day.slice(5)),
  datasets: [{
    data: chartEvents.value.map(item => item.total),
    backgroundColor: 'rgba(139, 58, 58, 0.8)',
    borderRadius: 6,
    borderSkipped: false,
  }],
}))

const barOptions = {
  responsive: false,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { display: false }, ticks: { color: '#665a4c', maxRotation: 45 } },
    y: { allowDecimals: false, ticks: { color: '#665a4c' }, grid: { color: '#d9cebb' } },
  },
}

// Pie chart
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

// Line chart
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
    pointRadius: 3,
    pointHoverRadius: 6,
  }],
}))

const lineOptions = {
  responsive: false,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { display: false }, ticks: { color: '#665a4c', maxRotation: 45 } },
    y: { allowDecimals: false, ticks: { color: '#665a4c' }, grid: { color: '#d9cebb' } },
  },
}

// 图表宽度（根据天数动态计算）
const chartWidth = computed(() => {
  return Math.max(600, chartDays.value * 24)
})
</script>

<template>
  <section id="stats" class="stats-section">
    <div class="section-heading">
      <p class="eyebrow">Progress</p>
      <h2>学习痕迹</h2>
    </div>

    <!-- 数据概览 -->
    <div class="stats-grid">
      <article class="stat-card">
        <span>总单词</span>
        <strong>{{ stats?.counts?.total || 0 }}</strong>
      </article>
      <article class="stat-card">
        <span>待学习</span>
        <strong>{{ stats?.counts?.new_total || 0 }}</strong>
      </article>
      <article class="stat-card">
        <span>学习中</span>
        <strong>{{ stats?.counts?.learning || 0 }}</strong>
      </article>
      <article class="stat-card">
        <span>已掌握</span>
        <strong>{{ stats?.counts?.mastered || 0 }}</strong>
      </article>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 每日学习量柱状图 -->
      <article class="chart-card">
        <div class="chart-header">
          <h3>每日学习量</h3>
          <div class="chart-range">
            <button :class="{ active: chartDays === 14 }" @click="chartDays = 14">14天</button>
            <button :class="{ active: chartDays === 30 }" @click="chartDays = 30">30天</button>
            <button :class="{ active: chartDays === 90 }" @click="chartDays = 90">90天</button>
            <button :class="{ active: chartDays === 365 }" @click="chartDays = 365">全部</button>
          </div>
        </div>
        <div class="chart-scroll">
          <div :style="{ width: chartWidth + 'px', height: '220px' }">
            <Bar :data="barData" :options="barOptions" :width="chartWidth" :height="220" />
          </div>
        </div>
      </article>

      <!-- 单词状态饼图 -->
      <article class="chart-card">
        <h3>单词状态分布</h3>
        <div class="chart-container-pie">
          <Pie :data="pieData" :options="pieOptions" />
        </div>
      </article>

      <!-- 学习趋势折线图 -->
      <article class="chart-card">
        <div class="chart-header">
          <h3>学习趋势</h3>
          <div class="chart-range">
            <button :class="{ active: chartDays === 14 }" @click="chartDays = 14">14天</button>
            <button :class="{ active: chartDays === 30 }" @click="chartDays = 30">30天</button>
            <button :class="{ active: chartDays === 90 }" @click="chartDays = 90">90天</button>
            <button :class="{ active: chartDays === 365 }" @click="chartDays = 365">全部</button>
          </div>
        </div>
        <div class="chart-scroll">
          <div :style="{ width: chartWidth + 'px', height: '220px' }">
            <Line :data="lineData" :options="lineOptions" :width="chartWidth" :height="220" />
          </div>
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
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 20px;
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
  overflow: hidden;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-header h3 {
  font-size: 15px;
  font-weight: 500;
  margin: 0;
}

.chart-card > h3 {
  font-size: 15px;
  font-weight: 500;
  margin: 0 0 16px;
  color: var(--ink);
}

.chart-range {
  display: flex;
  gap: 4px;
}

.chart-range button {
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--muted);
  cursor: pointer;
  font-family: inherit;
  transition: all 160ms;
}

.chart-range button.active {
  background: var(--ink);
  color: #fff8e8;
  border-color: var(--ink);
}

.chart-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 8px;
}

.chart-container-pie {
  height: 260px;
}

@media (max-width: 720px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
}
</style>
