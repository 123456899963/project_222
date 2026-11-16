<script setup lang="ts">
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="app-toast" aria-live="polite">
    <TransitionGroup name="app-toast">
      <div
        v-for="item in toast.items"
        :key="item.id"
        class="app-toast__item"
        :class="`app-toast__item--${item.type}`"
        role="status"
        @click="toast.remove(item.id)"
      >
        {{ item.message }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.app-toast {
  position: fixed;
  top: 76px;
  left: 50%;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transform: translateX(-50%);
  pointer-events: none;
}

.app-toast__item {
  min-width: 220px;
  max-width: min(90vw, 420px);
  padding: 10px 16px;
  border-left: 3px solid var(--color-info);
  border-radius: var(--radius-sm);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-dropdown);
  color: var(--color-text-primary);
  font-size: var(--text-small);
  cursor: pointer;
  pointer-events: auto;
}

.app-toast__item--success {
  border-left-color: var(--color-success);
}

.app-toast__item--warning {
  border-left-color: var(--color-warning);
}

.app-toast__item--error {
  border-left-color: var(--color-error);
}

.app-toast__item--info {
  border-left-color: var(--color-info);
}

.app-toast-enter-active,
.app-toast-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.app-toast-enter-from,
.app-toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
