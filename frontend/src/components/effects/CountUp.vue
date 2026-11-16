<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * 数字滚动（灵感来源：ReactBits Count Up）
 * - 进入视口后由 0 递增到目标值，rAF 缓动，无第三方依赖
 * - 值变化时重新滚动（如收藏数被用户改动）
 * - 开启"减少动态效果"时直接显示最终值
 */
const props = withDefaults(
  defineProps<{
    value: number
    duration?: number
    decimals?: number
  }>(),
  { duration: 900, decimals: 0 },
)

const root = ref<HTMLElement | null>(null)
const display = ref(0)
let frame = 0
let observer: IntersectionObserver | null = null
let started = false

const formatted = computed(() =>
  display.value.toLocaleString('zh-CN', {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals,
  }),
)

function prefersReducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

function easeOutCubic(progress: number): number {
  return 1 - Math.pow(1 - progress, 3)
}

function animateTo(target: number) {
  if (frame) cancelAnimationFrame(frame)
  const from = display.value
  const delta = target - from
  if (!delta) return
  if (prefersReducedMotion()) {
    display.value = target
    return
  }
  const startTime = performance.now()
  const step = (now: number) => {
    const progress = Math.min((now - startTime) / props.duration, 1)
    display.value = from + delta * easeOutCubic(progress)
    if (progress < 1) {
      frame = requestAnimationFrame(step)
    } else {
      display.value = target
      frame = 0
    }
  }
  frame = requestAnimationFrame(step)
}

watch(
  () => props.value,
  (next) => {
    if (started) animateTo(next)
  },
)

onMounted(() => {
  if (prefersReducedMotion() || typeof IntersectionObserver === 'undefined') {
    started = true
    display.value = props.value
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return
      started = true
      observer?.disconnect()
      observer = null
      animateTo(props.value)
    },
    { threshold: 0.4 },
  )
  if (root.value) observer.observe(root.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  if (frame) cancelAnimationFrame(frame)
})
</script>

<template>
  <span ref="root" class="count-up">{{ formatted }}</span>
</template>
