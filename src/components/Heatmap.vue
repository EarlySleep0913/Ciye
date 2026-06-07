<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  api: Function,
})

const heatmapData = ref({})
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const data = await props.api('/api/heatmap')
    heatmapData.value = data.data || {}
  } catch {} finally {
    loading.value = false
  }
}

// Generate 52 weeks × 7 days grid
const weeks = computed(() => {
  const result = []
  const today = new Date()
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - 364) // Go back ~1 year
  // Align to Sunday
  startDate.setDate(startDate.getDate() - startDate.getDay())

  const current = new Date(startDate)
  let week = []

  while (current <= today) {
    const dateStr = current.toISOString().slice(0, 10)
    const count = heatmapData.value[dateStr] || 0
    week.push({ date: dateStr, count, day: current.getDay() })

    if (week.length === 7) {
      result.push(week)
      week = []
    }
    current.setDate(current.getDate() + 1)
  }
  if (week.length > 0) result.push(week)
  return result
})

function getColor(count) {
  if (count === 0) return 'var(--heatmap-empty)'
  if (count <= 2) return 'var(--heatmap-1)'
  if (count <= 5) return 'var(--heatmap-2)'
  if (count <= 10) return 'var(--heatmap-3)'
  return 'var(--heatmap-4)'
}

const monthLabels = computed(() => {
  const labels = []
  const today = new Date()
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - 364)

  let lastMonth = -1
  weeks.value.forEach((week, i) => {
    const firstDay = week[0]
    if (firstDay) {
      const d = new Date(firstDay.date)
      const m = d.getMonth()
      if (m !== lastMonth) {
        const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        labels.push({ index: i, name: monthNames[m] })
        lastMonth = m
      }
    }
  })
  return labels
})

const totalDays = computed(() => {
  return Object.values(heatmapData.value).filter(v => v > 0).length
})

onMounted(loadData)
</script>

<template>
  <article class="heatmap-card">
    <div class="heatmap-header">
      <div>
        <p class="eyebrow">Activity</p>
        <h3>学习打卡</h3>
      </div>
      <span class="heatmap-total">过去一年活跃 <strong>{{ totalDays }}</strong> 天</span>
    </div>

    <div class="heatmap-wrapper">
      <!-- Month labels -->
      <div class="month-labels">
        <span
          v-for="m in monthLabels"
          :key="m.index"
          :style="{ gridColumn: m.index + 1 }"
        >{{ m.name }}</span>
      </div>

      <div class="heatmap-grid-container">
        <!-- Day labels -->
        <div class="day-labels">
          <span>一</span><span></span><span>三</span><span></span><span>五</span><span></span><span></span>
        </div>

        <!-- Grid -->
        <div class="heatmap-grid">
          <div v-for="(week, wi) in weeks" :key="wi" class="heatmap-week">
            <div
              v-for="day in week"
              :key="day.date"
              class="heatmap-cell"
              :style="{ background: getColor(day.count) }"
              :title="`${day.date}: ${day.count} 次学习`"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="heatmap-legend">
      <span>少</span>
      <div class="legend-cell" style="background: var(--heatmap-empty)"></div>
      <div class="legend-cell" style="background: var(--heatmap-1)"></div>
      <div class="legend-cell" style="background: var(--heatmap-2)"></div>
      <div class="legend-cell" style="background: var(--heatmap-3)"></div>
      <div class="legend-cell" style="background: var(--heatmap-4)"></div>
      <span>多</span>
    </div>
  </article>
</template>

<style scoped>
.heatmap-card {
  --heatmap-empty: rgba(216, 203, 184, 0.3);
  --heatmap-1: rgba(111, 134, 111, 0.3);
  --heatmap-2: rgba(111, 134, 111, 0.5);
  --heatmap-3: rgba(111, 134, 111, 0.7);
  --heatmap-4: rgba(111, 134, 111, 0.95);
  position: relative;
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 24px;
  grid-column: 1 / -1;
}

.heatmap-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

.heatmap-header h3 {
  font-size: 18px;
  font-weight: 500;
  margin: 4px 0 0;
}

.heatmap-total {
  font-size: 13px;
  color: var(--muted);
}

.heatmap-total strong {
  color: var(--sage);
  font-size: 16px;
}

.heatmap-wrapper {
  overflow-x: auto;
  padding-bottom: 4px;
}

.month-labels {
  display: grid;
  grid-template-columns: repeat(53, 14px);
  gap: 2px;
  margin-left: 30px;
  margin-bottom: 4px;
}

.month-labels span {
  font-size: 10px;
  color: var(--muted);
  white-space: nowrap;
}

.heatmap-grid-container {
  display: flex;
  gap: 4px;
}

.day-labels {
  display: grid;
  grid-template-rows: repeat(7, 12px);
  gap: 2px;
  width: 22px;
  flex-shrink: 0;
}

.day-labels span {
  font-size: 10px;
  color: var(--muted);
  line-height: 12px;
}

.heatmap-grid {
  display: flex;
  gap: 2px;
}

.heatmap-week {
  display: grid;
  grid-template-rows: repeat(7, 12px);
  gap: 2px;
}

.heatmap-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background: rgba(216, 203, 184, 0.3);
  transition: all 100ms;
}

.heatmap-cell:hover {
  outline: 1px solid var(--gold);
  transform: scale(1.3);
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-end;
  margin-top: 12px;
  font-size: 11px;
  color: var(--muted);
}

.legend-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
</style>
