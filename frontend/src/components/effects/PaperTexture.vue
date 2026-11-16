<script setup lang="ts">
/**
 * 宣纸纸纹层（灵感来源：ReactBits Noise）
 * - 静态 SVG fractalNoise，一次绘制，无 rAF 重绘，滚动不额外消耗
 * - 纯装饰：pointer-events: none，不承载任何交互
 * - 透明度由 --paper-noise-opacity 统一控制，后台路由不挂载
 */
</script>

<template>
  <div class="paper-texture" aria-hidden="true"></div>
</template>

<style scoped>
.paper-texture {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: var(--paper-noise-opacity);
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 160px 160px;
}
</style>
