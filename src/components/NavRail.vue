<script setup>
import { BookOpen, BookMarked, BarChart3, Settings } from 'lucide-vue-next'

defineProps({ active: String })
const emit = defineEmits(['navigate'])

const navItems = [
  { id: 'study', label: '今日学习', icon: BookOpen },
  { id: 'shelf', label: '词书架', icon: BookMarked },
  { id: 'stats', label: '学习统计', icon: BarChart3 },
  { id: 'settings', label: '设置', icon: Settings },
]
</script>

<template>
  <aside class="rail" aria-label="主导航">
    <div class="brand-mark">词</div>
    <nav>
      <a
        v-for="item in navItems"
        :key="item.id"
        :class="{ active: active === item.id }"
        href="#"
        @click.prevent="emit('navigate', item.id)"
      >
        <component :is="item.icon" :size="18" />
        {{ item.label }}
      </a>
    </nav>
  </aside>
</template>
