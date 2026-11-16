<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 首页纯装饰滚动背景（ADR-0003 R7）
 * - 仅装饰：图片不可点击、不承载任何跳转
 * - 无死链：加载失败的图自动移出轮播；全部失败时整体不渲染（保留原渐变色）
 * - 自动轮播：尊重 prefers-reduced-motion（若用户开启"减少动态效果"，则只显示首张）
 */

interface Banner {
  key: string
  label: string
  /** 候选顺序：实拍 WebP → 实拍 JPEG → 内置水墨占位 SVG（保证不留死链） */
  sources: string[]
}

const BANNER_KEYS = [
  { key: 'green', label: '绿茶' },
  { key: 'white', label: '白茶' },
  { key: 'yellow', label: '黄茶' },
  { key: 'oolong', label: '乌龙茶' },
  { key: 'red', label: '红茶' },
  { key: 'dark', label: '黑茶' },
] as const

const BANNERS: Banner[] = BANNER_KEYS.map((item) => ({
  ...item,
  sources: [
    `/images/banners/banner-${item.key}.webp`,
    `/images/banners/banner-${item.key}.jpg`,
    `/images/banners/banner-${item.key}.svg`,
  ],
}))

const ROTATE_MS = 7000

const failed = ref<string[]>([])
const current = ref(0)
let timer: number | null = null

function currentSrc(banner: Banner): string {
  return banner.sources.find((src) => !failed.value.includes(src)) ?? ''
}

const available = computed(() => BANNERS.filter((banner) => currentSrc(banner) !== ''))
const activeIndex = computed(() =>
  available.value.length === 0 ? -1 : current.value % available.value.length,
)

function stop(): void {
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

function start(): void {
  stop()
  if (available.value.length < 2) return
  timer = window.setInterval(() => {
    current.value = (current.value + 1) % available.value.length
  }, ROTATE_MS)
}

function handleError(src: string): void {
  if (!failed.value.includes(src)) failed.value = [...failed.value, src]
  if (current.value >= available.value.length) current.value = 0
  start()
}

onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  if (!reduced) start()
})

onBeforeUnmount(stop)
</script>

<template>
  <div class="hero-bg">
    <div class="hero-bg__layer" aria-hidden="true">
      <img
        v-for="(banner, index) in available"
        :key="banner.key"
        class="hero-bg__img"
        :class="{ 'hero-bg__img--active': index === activeIndex }"
        :src="currentSrc(banner)"
        alt=""
        :loading="index === 0 ? 'eager' : 'lazy'"
        decoding="async"
        @error="handleError(currentSrc(banner))"
      />
      <div class="hero-bg__veil"></div>
    </div>
  </div>
</template>

<style scoped>
.hero-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.hero-bg__layer {
  position: absolute;
  inset: 0;
}

.hero-bg__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 1.2s ease-in-out;
  will-change: opacity;
}

.hero-bg__img--active {
  opacity: 1;
}

/* 遮罩：单一平铺淡色（无方向、无渐变），只做轻微提亮，避免出现可见的分层/拼接线 */
.hero-bg__veil {
  position: absolute;
  inset: 0;
  background: rgba(250, 248, 245, 0.12);
}

@media (prefers-reduced-motion: reduce) {
  .hero-bg__img {
    transition: none;
  }
}
</style>
