import { createApp } from 'vue'
import App from './App.vue'
import './styles/main.css'

const app = createApp(App)

// v-reveal directive: animate elements into view on scroll
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible')
        revealObserver.unobserve(entry.target)
      }
    })
  },
  { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
)

app.directive('reveal', {
  mounted(el, binding) {
    const type = binding.arg || 'up'
    if (type === 'left') el.classList.add('reveal-left')
    else if (type === 'scale') el.classList.add('reveal-scale')
    else el.classList.add('reveal')
    revealObserver.observe(el)
  },
})

// v-spotlight directive: mouse-following glow on cards
app.directive('spotlight', {
  mounted(el) {
    el.classList.add('spotlight-card')
    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect()
      el.style.setProperty('--mx', `${e.clientX - rect.left}px`)
      el.style.setProperty('--my', `${e.clientY - rect.top}px`)
    })
  },
})

app.mount('#app')
