<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import FavoriteButton from '@/components/FavoriteButton.vue'
import SpotlightCard from '@/components/effects/SpotlightCard.vue'
import { CATEGORY_LABELS } from '@/utils/teaQuery'
import type { TeaListItem } from '@/types'

const props = defineProps<{
  tea: TeaListItem
  /** 紧凑模式：图片更矮、元信息更小（空状态推荐 / 横向推荐轨道） */
  compact?: boolean
}>()

const imageFailed = ref(false)
const favoriteCount = ref(props.tea.favorite_count)

watch(
  () => props.tea.favorite_count,
  (value) => {
    favoriteCount.value = value
  },
)

const showImage = computed(() => !!props.tea.main_image_url && !imageFailed.value)
const favoriteText = computed(() => favoriteCount.value.toLocaleString('zh-CN'))
const categoryLabel = computed(() => CATEGORY_LABELS[props.tea.category])
const categoryStyle = computed(() => ({
  '--cat-color': `var(--color-tea-${props.tea.category})`,
}))
</script>

<template>
  <SpotlightCard class="tea-card-wrap" radius="var(--radius-lg)">
    <RouterLink
      class="tea-card"
      :class="{ 'tea-card--compact': compact }"
      :to="{ name: 'tea-detail', params: { id: tea.id } }"
    >
      <div class="tea-card__media" :style="categoryStyle">
        <img
          v-if="showImage"
          class="tea-card__img"
          :src="tea.main_image_url as string"
          :alt="tea.name"
          loading="lazy"
          @error="imageFailed = true"
        />
        <div v-else class="tea-card__img tea-card__img--placeholder" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19.2 2.5c1 1.66.6 6-2 9-2 2.4-6.2 3-6.2 3zM2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"
            />
          </svg>
        </div>
      </div>

      <div class="tea-card__body">
        <h3 class="tea-card__name">{{ tea.name }}</h3>
        <div class="tea-card__meta">
          <span class="tea-card__dot" aria-hidden="true"></span>
          <span class="tea-card__meta-item">{{ categoryLabel }}</span>
          <span class="tea-card__meta-sep" aria-hidden="true">·</span>
          <span class="tea-card__meta-item tea-card__meta-item--origin">{{ tea.origin }}</span>
          <span class="tea-card__meta-sep" aria-hidden="true">·</span>
          <span class="tea-card__meta-item tea-card__meta-item--fav" title="收藏数">
            ♡ {{ favoriteText }}
          </span>
        </div>
      </div>
    </RouterLink>

    <FavoriteButton
      class="tea-card__fav-btn"
      :tea-id="tea.id"
      :count="favoriteCount"
      @change="favoriteCount = $event"
    />
  </SpotlightCard>
</template>

<style scoped>
.tea-card-wrap {
  position: relative;
}

.tea-card__fav-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
}

.tea-card {
  display: block;
}

.tea-card__media {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: var(--color-bg-muted);
  transform: translateZ(0);
}

.tea-card__img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  display: block;
  transition: transform var(--motion-duration-slow) var(--motion-ease);
}

.tea-card--compact .tea-card__img {
  aspect-ratio: 16 / 9;
}

.tea-card:hover .tea-card__img {
  transform: scale(1.04);
}

.tea-card__img--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.tea-card__img--placeholder svg {
  width: 32px;
  height: 32px;
  opacity: 0.5;
}

.tea-card__body {
  padding: 12px 2px 0;
}

.tea-card__name {
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color var(--motion-duration-fast) var(--motion-ease);
}

.tea-card:hover .tea-card__name {
  color: var(--color-primary);
}

.tea-card__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
}

.tea-card__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--cat-color, var(--color-primary));
  flex-shrink: 0;
}

.tea-card__meta-item--origin {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tea-card__meta-item--fav {
  flex-shrink: 0;
  margin-left: auto;
}

.tea-card__meta-sep {
  color: var(--color-border-dark);
  flex-shrink: 0;
}

.tea-card--compact .tea-card__name {
  font-size: var(--text-body);
}

.tea-card--compact .tea-card__meta {
  font-size: var(--text-caption);
}

@media (prefers-reduced-motion: reduce) {
  .tea-card__img,
  .tea-card__name {
    transition: none;
  }
  .tea-card:hover .tea-card__img {
    transform: none;
  }
}
</style>
