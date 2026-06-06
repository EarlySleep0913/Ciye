<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip)

const props = defineProps({ stats: Object })

const chartData = computed(() => {
  const rows = props.stats?.events || []
  return {
    labels: rows.slice().reverse().map(item => item.day.slice(5)),
    datasets: [{
      data: rows.slice().reverse().map(item => item.total),
      backgroundColor: '#8b3a3a',
      borderRadius: 6,
    }],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { display: false }, ticks: { color: '#665a4c' } },
    y: { allowDecimals: false, ticks: { color: '#665a4c' }, grid: { color: '#d9cebb' } },
  },
}
</script>

<template>
  <section id="stats" class="stats-section">
    <div class="section-heading">
      <p class="eyebrow">Progress</p>
      <h2>学习痕迹</h2>
    </div>
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
      <article class="chart-card">
        <div style="height: 220px">
          <Bar :data="chartData" :options="chartOptions" />
        </div>
      </article>
    </div>
  </section>
</template>
