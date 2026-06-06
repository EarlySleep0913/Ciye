<script setup>
import { BookOpen, BookMarked, BarChart3, Settings, LogOut, Heart, AlertCircle } from 'lucide-vue-next'

const props = defineProps({
  active: String,
  role: String,
})

const emit = defineEmits(['navigate', 'logout'])

const navItems = [
  { id: 'study', label: '今日学习', icon: BookOpen },
  { id: 'shelf', label: '词书架', icon: BookMarked },
  { id: 'wrong', label: '错词本', icon: AlertCircle },
  { id: 'fav', label: '收藏夹', icon: Heart },
  { id: 'stats', label: '学习统计', icon: BarChart3 },
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
      <a
        v-if="role === 'admin'"
        :class="{ active: active === 'settings' }"
        href="#"
        @click.prevent="emit('navigate', 'settings')"
      >
        <Settings :size="18" />
        设置
      </a>
    </nav>
    <div class="rail-bottom">
      <a href="#" class="logout-link" @click.prevent="emit('logout')">
        <LogOut :size="16" />
        退出登录
      </a>
    </div>
  </aside>
</template>

<style scoped>
.rail-bottom {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 28px;
}

.logout-link {
  color: rgba(248, 240, 223, 0.5);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  transition: 160ms ease;
}

.logout-link:hover {
  color: rgba(248, 240, 223, 0.9);
  background: rgba(255, 255, 255, 0.08);
}
</style>
