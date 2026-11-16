<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="page-404">
    <h1 class="text-display text-primary-dark">404</h1>
    <p class="text-secondary">页面不存在</p>
    <button type="button" class="page-404__back" @click="router.replace('/')">返回首页</button>
  </div>
</template>

<style scoped>
.page-404 {
  padding: 96px 16px;
  text-align: center;
}

.page-404__back {
  margin-top: 24px;
  padding: 10px 24px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--text-body);
  cursor: pointer;
  transition: background 0.2s ease;
}

.page-404__back:hover {
  background: var(--color-primary-hover);
}
</style>
