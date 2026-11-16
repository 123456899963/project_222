<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { addFavorite, getFavoriteStatus, removeFavorite } from '@/api/favorites'
import { getMyLists } from '@/api/lists'
import { useUserStore } from '@/stores/user'
import { nextFavoriteState, nextListToggleState } from '@/utils/favorite'
import type { ListSummary } from '@/types'

const PENDING_KEY = 'pending_favorite_tea_id'

const props = withDefaults(
  defineProps<{
    teaId: number
    count?: number
    /** icon：卡片右上角心形；primary：详情页主按钮 */
    variant?: 'icon' | 'primary'
  }>(),
  { count: 0, variant: 'icon' },
)

const emit = defineEmits<{ change: [count: number] }>()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isFavorited = ref(false)
const favoriteCount = ref(props.count)
const pending = ref(false)

/** S9 清单选择面板：勾选态由收藏状态返回的 list_ids 驱动 */
const lists = ref<ListSummary[]>([])
const listIds = ref<number[]>([])
const listsLoaded = ref(false)
const pickerOpen = ref(false)
const groupRef = ref<HTMLElement | null>(null)
const caretRef = ref<HTMLButtonElement | null>(null)

watch(
  () => props.count,
  (value) => {
    favoriteCount.value = value
  },
)

watch(
  () => userStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      void syncStatus()
    } else {
      isFavorited.value = false
      listIds.value = []
      lists.value = []
      listsLoaded.value = false
      closePicker()
    }
  },
)

onMounted(() => {
  if (userStore.isLoggedIn) {
    void syncStatus()
  }
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onDocumentKeydown)
})

function apply(state: { is_favorited: boolean; favorite_count: number; list_ids?: number[] }) {
  isFavorited.value = state.is_favorited
  favoriteCount.value = state.favorite_count
  if (state.list_ids) listIds.value = state.list_ids
  emit('change', state.favorite_count)
}

async function syncStatus() {
  try {
    const res = await getFavoriteStatus(props.teaId)
    apply(res.data)
  } catch {
    // 茶品不存在或网络异常：保持未收藏展示，不阻断浏览
  }
  await replayPending()
}

/** 未登录点击 → 登录；登录成功回到原页后自动执行本次收藏 */
async function replayPending() {
  const raw = sessionStorage.getItem(PENDING_KEY)
  if (!raw || Number(raw) !== props.teaId) return
  sessionStorage.removeItem(PENDING_KEY)
  if (isFavorited.value) return
  await doToggle(false)
}

function requireLogin() {
  sessionStorage.setItem(PENDING_KEY, String(props.teaId))
  void router.push({ name: 'login', query: { redirect: route.fullPath } })
}

async function doToggle(optimistic = true) {
  if (pending.value) return
  const action = isFavorited.value ? 'remove' : 'add'
  const previous = {
    is_favorited: isFavorited.value,
    favorite_count: favoriteCount.value,
    list_ids: [...listIds.value],
  }

  if (optimistic) apply(nextFavoriteState(previous, action))

  pending.value = true
  try {
    const res =
      action === 'add' ? await addFavorite(props.teaId) : await removeFavorite(props.teaId)
    apply(res.data)
  } catch {
    apply(previous)
  } finally {
    pending.value = false
  }
}

function onClick() {
  if (pending.value) return
  if (!userStore.isLoggedIn) {
    requireLogin()
    return
  }
  void doToggle()
}

/** 打开/收起清单面板，首次打开时懒加载清单列表 */
async function togglePicker() {
  pickerOpen.value = !pickerOpen.value
  if (pickerOpen.value && !listsLoaded.value) {
    try {
      const res = await getMyLists()
      lists.value = res.data
      listsLoaded.value = true
    } catch {
      // 加载失败保持未加载态，下次打开重试
      listsLoaded.value = false
    }
  }
}

/** 切换某清单的收录状态：已含则移出、未含则加入（乐观更新 + 失败回滚） */
async function onToggleList(list: ListSummary) {
  if (pending.value) return
  const previous = {
    is_favorited: isFavorited.value,
    favorite_count: favoriteCount.value,
    list_ids: [...listIds.value],
  }
  const next = nextListToggleState(previous, list.id)
  apply({ ...next })
  pending.value = true
  try {
    const res =
      next.action === 'add'
        ? await addFavorite(props.teaId, list.id)
        : await removeFavorite(props.teaId, list.id)
    apply(res.data)
  } catch {
    apply(previous)
  } finally {
    pending.value = false
  }
}

function closePicker() {
  pickerOpen.value = false
}

function onDocumentClick(event: MouseEvent) {
  if (pickerOpen.value && !groupRef.value?.contains(event.target as Node)) {
    closePicker()
  }
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && pickerOpen.value) {
    closePicker()
    caretRef.value?.focus()
  }
}
</script>

<template>
  <div ref="groupRef" class="fav-group" :class="{ 'fav-group--joined': variant === 'primary' }">
    <button
      type="button"
      class="fav-btn"
      :class="[
        `fav-btn--${variant}`,
        { 'fav-btn--active': isFavorited, 'fav-btn--pending': pending },
      ]"
      :aria-pressed="isFavorited"
      :aria-label="isFavorited ? '取消收藏' : '收藏茶品'"
      :title="isFavorited ? '取消收藏' : '加入我的清单'"
      @click.stop.prevent="onClick"
    >
      <svg
        class="fav-btn__heart"
        viewBox="0 0 24 24"
        :fill="isFavorited ? 'currentColor' : 'none'"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <path
          d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"
        />
      </svg>
      <span v-if="variant === 'primary'" class="fav-btn__text">
        {{ isFavorited ? '已在我的清单' : '加入我的清单' }}
      </span>
    </button>
    <button
      v-if="variant === 'primary' && userStore.isLoggedIn"
      ref="caretRef"
      type="button"
      class="fav-caret"
      :class="{ 'fav-caret--active': isFavorited }"
      aria-haspopup="true"
      :aria-expanded="pickerOpen"
      aria-label="选择要加入的清单"
      :disabled="pending"
      @click="togglePicker"
    >
      <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
        <path
          d="M2 4l4 4 4-4"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>
    <div v-if="pickerOpen" class="fav-picker" role="menu" aria-label="收藏清单">
      <button
        v-for="list in lists"
        :key="list.id"
        type="button"
        role="menuitemcheckbox"
        class="fav-picker__item"
        :class="{ 'fav-picker__item--active': listIds.includes(list.id) }"
        :aria-checked="listIds.includes(list.id)"
        @click="onToggleList(list)"
      >
        <svg
          v-if="listIds.includes(list.id)"
          class="fav-picker__check"
          viewBox="0 0 12 12"
          width="12"
          height="12"
          aria-hidden="true"
        >
          <path
            d="M2 6l3 3 5-6"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span class="fav-picker__title">{{ list.title }}</span>
        <span class="fav-picker__count">{{ list.tea_count }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.fav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  font-family: inherit;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s,
    transform 0.15s;
}

.fav-btn--icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text-secondary);
  backdrop-filter: blur(4px);
}

.fav-btn--icon:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.fav-btn--icon.fav-btn--active {
  color: var(--color-error);
  border-color: var(--color-error);
}

.fav-btn--primary {
  height: 44px;
  padding: 0 24px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--text-body);
  font-weight: 500;
}

.fav-btn--primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.fav-btn--primary.fav-btn--active {
  background: transparent;
  color: var(--color-primary);
}

.fav-group {
  position: relative;
  display: inline-flex;
  align-items: stretch;
}

.fav-group--joined .fav-btn--primary {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
  border-right: none;
}

.fav-caret {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 44px;
  border: 1px solid var(--color-primary);
  border-top-right-radius: var(--radius-full);
  border-bottom-right-radius: var(--radius-full);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
}

.fav-caret--active {
  background: transparent;
  color: var(--color-primary);
}

.fav-caret:hover:not(:disabled) {
  background: var(--color-primary-hover);
  color: var(--color-text-inverse);
}

.fav-caret--active:hover:not(:disabled) {
  background: var(--color-bg-muted);
  color: var(--color-primary);
}

.fav-caret:disabled {
  opacity: 0.7;
  cursor: wait;
}

.fav-picker {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  max-width: 300px;
  padding: 8px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-dropdown);
  z-index: 60;
}

.fav-picker__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-small);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.fav-picker__item:hover {
  background: var(--color-bg-muted);
}

.fav-picker__item--active {
  color: var(--color-primary);
}

.fav-picker__check {
  flex-shrink: 0;
}

.fav-picker__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-picker__count {
  margin-left: auto;
  color: var(--color-text-muted);
}

.fav-btn--pending {
  opacity: 0.7;
  cursor: wait;
}

.fav-btn__heart {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.fav-btn--primary .fav-btn__heart {
  width: 16px;
  height: 16px;
}
</style>
