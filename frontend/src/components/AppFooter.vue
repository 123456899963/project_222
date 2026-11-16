<script setup lang="ts">
// 全站页脚（静态内容）
</script>

<template>
  <footer class="app-footer">
    <div class="app-footer__inner">
      <h4 class="app-footer__brand">茶·图鉴</h4>
      <p class="app-footer__desc">七大茶类 · 结构化知识库 · 让每一款茶都有据可循</p>
      <p class="app-footer__copy">© 2026 茶·图鉴 · 数据仅供参考</p>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  padding: 48px 0 32px;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.app-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
}

.app-footer__brand {
  font-family: var(--font-display);
  font-size: var(--text-h3);
  color: var(--color-primary-dark);
  font-weight: 600;
  margin: 0 0 8px;
}

.app-footer__desc {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin: 0 0 16px;
}

.app-footer__copy {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  margin: 0;
}

@media (max-width: 767px) {
  .app-footer__inner {
    padding: 0 16px;
  }
}
</style>
