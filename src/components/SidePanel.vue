<script setup>
import { RotateCcw } from 'lucide-vue-next'

defineProps({
  newCount: Number,
  reviewCount: Number,
  learnedCount: Number,
  totalCount: Number,
  settings: Object,
  books: Array,
})

const emit = defineEmits(['update-limit', 'activate-book', 'reset-today'])
</script>

<template>
  <aside class="side-stack">
    <section class="plan-card">
      <p class="eyebrow">Today</p>
      <h2>今日计划</h2>
      <div class="plan-numbers">
        <div><strong>{{ newCount }}</strong><span>新词</span></div>
        <div><strong>{{ reviewCount }}</strong><span>复习</span></div>
        <div><strong>{{ learnedCount }}</strong><span>已完成</span></div>
      </div>
      <div class="progress-track">
        <span :style="{ width: `${totalCount ? (learnedCount / totalCount) * 100 : 0}%` }" />
      </div>
      <p class="plan-copy">每日上限可以调小一点，先让你舒服地试用。</p>
    </section>

    <section class="settings-card">
      <label for="daily">每天新词数</label>
      <div class="range-row">
        <input
          id="daily"
          type="range"
          min="3"
          max="150"
          :value="settings.daily_new_limit"
          @input="emit('update-limit', $event.target.value)"
        />
        <strong>{{ settings.daily_new_limit }}</strong>
      </div>
      <button class="quiet-btn reset-btn" @click="emit('reset-today')">
        <RotateCcw :size="16" />
        重置今日学习
      </button>
    </section>

    <section class="books-card">
      <h3>词书</h3>
      <div
        v-for="book in books"
        :key="book.id"
        class="book-row"
        :class="{ 'active-book': book.active }"
        @click="emit('activate-book', book.id)"
      >
        <span>{{ book.name }}{{ book.active ? ' · 默认' : '' }}</span>
        <strong>{{ book.total }}</strong>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.book-row { cursor: pointer; }
.book-row:hover { color: var(--red); }
.reset-btn {
  margin-top: 14px;
  width: 100%;
  justify-content: center;
  font-size: 13px;
  min-height: 36px;
}
</style>
