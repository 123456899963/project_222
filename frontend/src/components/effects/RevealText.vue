<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 模糊聚焦入场（灵感来源：ReactBits Blur Text）
 * - 中文按字拆分、英文按词拆分，逐单位由虚到实（墨迹洇开）
 * - IntersectionObserver 触发，默认只播一次
 * - 开启"减少动态效果"时直接呈现静态文字
 */
const props = withDefaults(
  defineProps<{
    text: string
    as?: string
    by?: 'char' | 'word'
    delay?: number
    duration?: number
    once?: boolean
  }>(),
  { as: 'span', by: 'char', delay: 40, duration: 600, once: true },
)

const root = ref<HTMLElement | null>(null)
const visible = ref(false)
let observer: IntersectionObserver | null = null

const units = computed(() => {
  if (props.by === 'word') {
    const words = props.text.split(/\s+/).filter(Boolean)
    return words.map((word, index) => (index < words.length - 1 ? `${word}\u00A0` : word))
  }
  return Array.from(props.text).map((char) => (char === ' ' ? '\u00A0' : char))
})

const styleVars = computed(() => ({
  '--reveal-duration': `${props.duration}ms`,
  '--reveal-stagger': `${props.delay}ms`,
}))

onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  if (reduced || typeof IntersectionObserver === 'undefined') {
    visible.value = true
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return
      visible.value = true
      if (props.once) {
        observer?.disconnect()
        observer = null
      }
    },
    { threshold: 0.15 },
  )
  if (root.value) observer.observe(root.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <component
    :is="as"
    ref="root"
    class="reveal-text"
    :class="{ 'reveal-text--visible': visible }"
    :style="styleVars"
  >
    <span
      v-for="(unit, index) in units"
      :key="index"
      class="reveal-text__unit"
      :style="{ '--i': index }"
      >{{ unit }}</span
    >
  </component>
</template>

<style scoped>
.reveal-text__unit {
  display: inline-block;
  opacity: 0;
  filter: blur(10px);
  transform: translateY(10px);
  transition:
    opacity var(--reveal-duration, 600ms) var(--motion-ease),
    filter var(--reveal-duration, 600ms) var(--motion-ease),
    transform var(--reveal-duration, 600ms) var(--motion-ease);
  transition-delay: calc(var(--i, 0) * var(--reveal-stagger, 40ms));
  will-change: opacity, filter, transform;
}

.reveal-text--visible .reveal-text__unit {
  opacity: 1;
  filter: none;
  transform: none;
  will-change: auto;
}

@media (prefers-reduced-motion: reduce) {
  .reveal-text__unit {
    opacity: 1;
    filter: none;
    transform: none;
    transition: none;
  }
}
</style>
