<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { CATEGORY_LABELS } from '@/utils/teaQuery'
import type { TeaCategory } from '@/types'

const props = defineProps<{
  category: TeaCategory
  /** 可点击时跳转列表页并带上该茶类筛选（详情页使用） */
  clickable?: boolean
}>()

const label = computed(() => CATEGORY_LABELS[props.category])
const modifier = computed(() => `category-tag--${props.category}`)
</script>

<template>
  <RouterLink
    v-if="clickable"
    class="category-tag"
    :class="modifier"
    :to="{ name: 'tea-list', query: { category } }"
    :title="`查看全部${label}`"
  >
    {{ label }}
  </RouterLink>
  <span v-else class="category-tag" :class="modifier">{{ label }}</span>
</template>

<style scoped>
.category-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  font-size: var(--text-caption);
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.category-tag--green {
  background: var(--color-tea-green);
  color: var(--color-text-inverse);
}

/* 白茶标签为浅色底 + 深色字（DESIGN_SYSTEM 特例） */
.category-tag--white {
  background: var(--color-tea-white);
  color: var(--color-text-primary);
}

.category-tag--yellow {
  background: var(--color-tea-yellow);
  color: var(--color-text-inverse);
}

.category-tag--red {
  background: var(--color-tea-red);
  color: var(--color-text-inverse);
}

.category-tag--oolong {
  background: var(--color-tea-oolong);
  color: var(--color-text-inverse);
}

.category-tag--dark {
  background: var(--color-tea-dark);
  color: var(--color-text-inverse);
}

.category-tag--reprocessed {
  background: var(--color-tea-reprocessed);
  color: var(--color-text-inverse);
}
</style>
