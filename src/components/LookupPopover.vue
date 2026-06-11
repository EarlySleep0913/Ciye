<script setup>
import { Loader2, Volume2, X } from 'lucide-vue-next'

defineProps({
  lookup: Object,
  loading: Boolean,
  speak: Function,
})

const emit = defineEmits(['close'])
</script>

<template>
  <Transition name="popover">
    <div v-if="lookup || loading" class="lookup-popover">
      <button class="close-btn" @click="emit('close')"><X :size="16" /></button>
      <p v-if="loading"><Loader2 class="spin" :size="16" /> 查询中...</p>
      <template v-else>
        <h3>{{ lookup.word }}</h3>
        <button class="audio-btn compact" @click="speak(lookup)">
          <Volume2 :size="16" /> {{ lookup.phonetic || '发音' }}
        </button>
        <p>{{ lookup.translation || lookup.definition || '没有查到释义' }}</p>
      </template>
    </div>
  </Transition>
</template>
