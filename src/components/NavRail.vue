<script setup>
import { BookOpen, BookMarked, BarChart3, Settings, LogOut, Heart, AlertCircle, PenTool, Brain } from 'lucide-vue-next'
import iconUrl from '../assets/icon.png'

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
  { id: 'test', label: '拼写测试', icon: PenTool },
  { id: 'ebbinghaus', label: '遗忘曲线', icon: Brain },
  { id: 'stats', label: '学习统计', icon: BarChart3 },
]
</script>

<template>
  <aside class="rail" aria-label="主导航">
    <img class="brand-mark" :src="iconUrl" alt="Ciye" />
    <nav>
      <a
        v-for="(item, i) in navItems"
        :key="item.id"
        :class="{ active: active === item.id }"
        :style="{ '--i': i }"
        href="#"
        @click.prevent="emit('navigate', item.id)"
      >
        <component :is="item.icon" :size="18" />
        {{ item.label }}
      </a>
      <a
        v-if="role === 'admin'"
        :class="{ active: active === 'settings' }"
        :style="{ '--i': navItems.length }"
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

/* 导航项 stagger 入场 */
.rail nav a {
  animation: navSlideIn 400ms var(--ease-out) both;
  animation-delay: calc(var(--i, 0) * 60ms + 100ms);
}

@keyframes navSlideIn {
  from {
    opacity: 0;
    transform: translateX(-12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 品牌图标 hover */
.brand-mark {
  transition: transform 400ms var(--ease-spring);
}

.brand-mark:hover {
  transform: scale(1.08) rotate(-3deg);
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
  transition: all var(--transition-base);
}

.logout-link:hover {
  color: rgba(248, 240, 223, 0.9);
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(2px);
}
</style>
