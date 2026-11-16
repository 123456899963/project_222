<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

/**
 * 柔光跟随卡片（灵感来源：ReactBits Spotlight Card）
 * - pointermove 写入 CSS 变量，柔光以茶褐色柔和叠加，rAF 合并高频事件
 * - tilt 开启后附带 ≤ maxTilt 度的 3D 倾斜，仅建议用于单张大卡
 * - 触摸设备与"减少动态效果"自动降级为静态卡片
 */
const props = withDefaults(
  defineProps<{
    radius?: string
    size?: number
    intensity?: number
    tilt?: boolean
    maxTilt?: number
  }>(),
  { radius: 'var(--radius-lg)', size: 260, intensity: 1, tilt: false, maxTilt: 4 },
)

const root = ref<HTMLElement | null>(null)
const active = ref(false)
let frame = 0
let pendingX = 0
let pendingY = 0

const styleVars = computed(() => ({
  '--spotlight-radius': props.radius,
  '--spotlight-size': `${props.size}px`,
  '--spotlight-intensity': String(props.intensity),
}))

function canHover(): boolean {
  return window.matchMedia?.('(hover: hover)').matches ?? false
}

function apply() {
  frame = 0
  const element = root.value
  if (!element) return
  const rect = element.getBoundingClientRect()
  const x = pendingX - rect.left
  const y = pendingY - rect.top
  element.style.setProperty('--mx', `${x}px`)
  element.style.setProperty('--my', `${y}px`)
  if (props.tilt && rect.width > 0 && rect.height > 0) {
    const rotateX = ((y / rect.height - 0.5) * -2 * props.maxTilt).toFixed(2)
    const rotateY = ((x / rect.width - 0.5) * 2 * props.maxTilt).toFixed(2)
    element.style.setProperty('--rx', `${rotateX}deg`)
    element.style.setProperty('--ry', `${rotateY}deg`)
  }
}

function onPointerMove(event: PointerEvent) {
  if (!canHover()) return
  active.value = true
  pendingX = event.clientX
  pendingY = event.clientY
  if (!frame) frame = requestAnimationFrame(apply)
}

function onPointerLeave() {
  active.value = false
  if (frame) {
    cancelAnimationFrame(frame)
    frame = 0
  }
  const element = root.value
  if (!element) return
  element.style.setProperty('--mx', '50%')
  element.style.setProperty('--my', '50%')
  element.style.setProperty('--rx', '0deg')
  element.style.setProperty('--ry', '0deg')
}

onBeforeUnmount(() => {
  if (frame) cancelAnimationFrame(frame)
})
</script>

<template>
  <div
    ref="root"
    class="spotlight-card"
    :class="{ 'spotlight-card--tilt': tilt, 'spotlight-card--active': active }"
    :style="styleVars"
    @pointerenter="onPointerMove"
    @pointermove="onPointerMove"
    @pointerleave="onPointerLeave"
  >
    <slot />
    <span class="spotlight-card__glow" aria-hidden="true"></span>
  </div>
</template>

<style scoped>
.spotlight-card {
  position: relative;
}

.spotlight-card--tilt {
  transform: perspective(900px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg));
  transition: transform var(--motion-duration-base) var(--motion-ease);
  will-change: transform;
}

.spotlight-card__glow {
  position: absolute;
  inset: 0;
  border-radius: var(--spotlight-radius);
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(
    circle var(--spotlight-size) at var(--mx, 50%) var(--my, 50%),
    var(--spotlight-color),
    transparent 70%
  );
  mix-blend-mode: soft-light;
  transition: opacity var(--motion-duration-base) var(--motion-ease);
}

.spotlight-card--active .spotlight-card__glow {
  opacity: var(--spotlight-intensity);
}

@media (hover: none) {
  .spotlight-card__glow {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spotlight-card--tilt {
    transform: none;
    transition: none;
  }
  .spotlight-card__glow {
    transition: none;
  }
}
</style>
