import { ref } from 'vue'

export function useAudio(api) {
  const audioCache = ref({})
  const pronouncingId = ref(null)

  function speak(item) {
    if (!item) return
    if (item.audio_url) {
      const audio = new Audio(item.audio_url)
      audio.play().catch(() => speakByBrowser(item.word))
    } else {
      speakByBrowser(item.word)
    }
  }

  function speakByBrowser(word) {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(word)
    utterance.lang = 'en-US'
    utterance.rate = 0.78
    window.speechSynthesis.speak(utterance)
  }

  async function speakPdfWord(item) {
    pronouncingId.value = item.id
    try {
      const cached = audioCache.value[item.word]
      const data = cached || await api(`/api/lookup?word=${encodeURIComponent(item.word)}`)
      if (!cached) audioCache.value[item.word] = data
      speak(data.audio_url ? data : { word: item.word })
      return { ...data, translation: item.translation || data.translation }
    } catch {
      speakByBrowser(item.word)
      return null
    } finally {
      pronouncingId.value = null
    }
  }

  return { speak, speakByBrowser, speakPdfWord, audioCache, pronouncingId }
}
