<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import TeaCard from '@/components/TeaCard.vue'
import { useTeaStore } from '@/stores/tea'
import { getHotTeas } from '@/api/teas'
import type { TeaCategory, TeaListItem, TeaSort } from '@/types'
import {
  CATEGORY_LABELS,
  TEA_CATEGORIES,
  TEA_FERMENTATIONS,
  TEA_SEASONS,
  buildListParams,
  defaultTeaFilterState,
  listActiveFilters,
  parseRouteQuery,
  serializeFilterState,
} from '@/utils/teaQuery'
import type { ActiveFilter, TeaFilterState } from '@/utils/teaQuery'

/** 价格区间下拉预设（元/斤，S2）：0 表示不限 */
const PRICE_OPTIONS = [0, 100, 300, 500, 1000, 3000, 5000] as const

const route = useRoute()
const router = useRouter()
const teaStore = useTeaStore()

/** 筛选状态唯一来源：从 URL 解析，修改后写回 URL，再统一由 URL 变化触发请求 */
const state = reactive<TeaFilterState>(defaultTeaFilterState())
const suggestions = ref<TeaListItem[]>([])
/** 高级筛选面板展开态：默认收起，首屏优先展示茶品 */
const filtersOpen = ref(false)

// —— URL → 状态 → 请求（浏览器的前进/后退也走这条链路）——
watch(
  () => route.query,
  (query) => {
    Object.assign(state, parseRouteQuery(query))
    void load()
  },
  { immediate: true, deep: true },
)

onMounted(() => {
  teaStore.fetchCategories().catch(() => {})
  teaStore.fetchOrigins().catch(() => {})
})

async function load() {
  await teaStore.fetchList(buildListParams(state))
  if (!teaStore.error && teaStore.total === 0) {
    void loadSuggestions()
  }
}

async function loadSuggestions() {
  if (suggestions.value.length) return
  try {
    const res = await getHotTeas(3)
    suggestions.value = res.data ?? []
  } catch {
    suggestions.value = []
  }
}

/** 修改筛选条件并写回 URL（默认重置到第 1 页） */
function commit(patch: Partial<TeaFilterState>, keepPage = false) {
  const next: TeaFilterState = { ...state, ...patch }
  next.page = keepPage ? (patch.page ?? state.page) : 1
  router.replace({ query: serializeFilterState(next) })
}

function toggleCategory(category: TeaCategory) {
  const next = state.categories.includes(category)
    ? state.categories.filter((c) => c !== category)
    : [...state.categories, category]
  commit({ categories: next })
}

function toggleOrigin(origin: string) {
  const next = state.origins.includes(origin)
    ? state.origins.filter((o) => o !== origin)
    : [...state.origins, origin]
  commit({ origins: next })
}

function toggleSeason(season: string) {
  const next = state.seasons.includes(season)
    ? state.seasons.filter((s) => s !== season)
    : [...state.seasons, season]
  commit({ seasons: next })
}

function toggleFermentation(fermentation: string) {
  const next = state.fermentations.includes(fermentation)
    ? state.fermentations.filter((f) => f !== fermentation)
    : [...state.fermentations, fermentation]
  commit({ fermentations: next })
}

/** 价格下拉：0 表示不限（null），上下限自动保持 min ≤ max */
function setPriceMin(raw: string) {
  const value = Number.parseInt(raw, 10)
  const priceMin = value > 0 ? value : null
  const priceMax =
    priceMin != null && state.priceMax != null && state.priceMax < priceMin
      ? priceMin
      : state.priceMax
  commit({ priceMin, priceMax })
}

function setPriceMax(raw: string) {
  const value = Number.parseInt(raw, 10)
  const next = value > 0 ? value : null
  commit({ priceMax: next })
}

function setFilterMode(mode: 'and' | 'or') {
  if (mode === state.filterMode) return
  commit({ filterMode: mode })
}

function removeFilter(filter: ActiveFilter) {
  if (filter.dimension === 'categories') {
    commit({ categories: state.categories.filter((c) => c !== filter.value) })
  } else if (filter.dimension === 'origins') {
    commit({ origins: state.origins.filter((o) => o !== filter.value) })
  } else if (filter.dimension === 'fermentations') {
    commit({ fermentations: state.fermentations.filter((f) => f !== filter.value) })
  } else {
    commit({ seasons: state.seasons.filter((s) => s !== filter.value) })
  }
}

function clearPrice() {
  commit({ priceMin: null, priceMax: null })
}

function clearAll() {
  commit(defaultTeaFilterState())
}

function onSortChange(event: Event) {
  commit({ sort: (event.target as HTMLSelectElement).value as TeaSort })
}

function clearKeyword() {
  commit({ keyword: '' })
}

// —— 展示派生数据 ——
const categoryOptions = computed(() => {
  const countMap = new Map(teaStore.categories.map((c) => [c.category, c.count]))
  return TEA_CATEGORIES.map((category) => ({
    category,
    label: CATEGORY_LABELS[category],
    count: countMap.get(category) ?? 0,
  }))
})

const activeFilters = computed(() => listActiveFilters(state))
const hasPrice = computed(() => state.priceMin != null || state.priceMax != null)

/** 除茶类外的高级筛选数量，用于「筛选」按钮角标 */
const advancedFilterCount = computed(
  () =>
    state.origins.length +
    state.seasons.length +
    state.fermentations.length +
    (hasPrice.value ? 1 : 0),
)

/** 带高级筛选进入页面时自动展开面板，避免条件被折叠后看不见 */
watch(
  advancedFilterCount,
  (count) => {
    if (count > 0) filtersOpen.value = true
  },
  { immediate: true },
)
const hasAnyFilter = computed(
  () =>
    !!state.keyword ||
    state.categories.length +
      state.origins.length +
      state.seasons.length +
      state.fermentations.length >
      0 ||
    hasPrice.value,
)

/** 价格区间展示文案 */
const priceText = computed(() => {
  const min = state.priceMin
  const max = state.priceMax
  if (min != null && max != null) return `¥${min}–${max}/斤`
  if (min != null) return `¥${min} 以上/斤`
  if (max != null) return `¥${max} 以下/斤`
  return ''
})

const breadcrumbLabel = computed(() => {
  if (state.keyword) return `搜索："${state.keyword}"`
  if (state.categories.length === 1) return CATEGORY_LABELS[state.categories[0]]
  return '全部茶品'
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(teaStore.total / Math.max(1, teaStore.pageSize))),
)

const pageItems = computed<Array<number | 'ellipsis'>>(() => {
  const total = totalPages.value
  if (total <= 1) return []
  const current = teaStore.page
  const nums = new Set([1, total, current - 1, current, current + 1])
  const sorted = [...nums].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b)
  const items: Array<number | 'ellipsis'> = []
  let last = 0
  for (const n of sorted) {
    if (n - last > 1) items.push('ellipsis')
    items.push(n)
    last = n
  }
  return items
})

const resultText = computed(() => (teaStore.loading ? '加载中…' : `共 ${teaStore.total} 款茶`))

function goPage(page: number) {
  if (page < 1 || page > totalPages.value || page === teaStore.page) return
  commit({ page }, true)
  window.scrollTo({ top: 180, behavior: 'smooth' })
}
</script>

<template>
  <AppHeader />

  <main class="tea-list-page">
    <div class="container">
      <!-- 面包屑 -->
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">{{ breadcrumbLabel }}</span>
        <RouterLink class="breadcrumb__compare" to="/compare">七大茶类对比 →</RouterLink>
      </nav>

      <!-- 工具条：茶类 + 筛选 + 排序 -->
      <section class="toolbar" aria-label="筛选与排序">
        <div class="toolbar__cats">
          <div class="filter-chips">
            <button
              v-for="option in categoryOptions"
              :key="option.category"
              type="button"
              class="chip"
              :class="[
                `chip--${option.category}`,
                { 'chip--active': state.categories.includes(option.category) },
              ]"
              :aria-pressed="state.categories.includes(option.category)"
              @click="toggleCategory(option.category)"
            >
              {{ option.label }}
              <span class="chip__count">{{ option.count }}</span>
            </button>
          </div>
        </div>

        <div class="toolbar__actions">
          <button
            type="button"
            class="filter-toggle"
            :class="{ 'filter-toggle--open': filtersOpen }"
            :aria-expanded="filtersOpen"
            @click="filtersOpen = !filtersOpen"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path d="M3 6h18M7 12h10M11 18h2" />
            </svg>
            <span>筛选</span>
            <span v-if="advancedFilterCount" class="filter-toggle__badge">
              {{ advancedFilterCount }}
            </span>
            <svg
              class="filter-toggle__chevron"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>

          <select
            class="sort-select"
            :value="state.sort"
            aria-label="排序方式"
            @change="onSortChange"
          >
            <option value="newest">最新上架</option>
            <option value="favorite">收藏最多</option>
          </select>
        </div>
      </section>

      <!-- 高级筛选面板（默认收起） -->
      <section v-show="filtersOpen" class="filter-panel" aria-label="更多筛选条件">
        <div class="filter-group">
          <div class="filter-group__label">产地</div>
          <div class="filter-chips">
            <button
              v-for="option in teaStore.origins"
              :key="option.origin"
              type="button"
              class="chip chip--default"
              :class="{ 'chip--active': state.origins.includes(option.origin) }"
              :aria-pressed="state.origins.includes(option.origin)"
              @click="toggleOrigin(option.origin)"
            >
              {{ option.origin }}
              <span class="chip__count">{{ option.count }}</span>
            </button>
            <span v-if="!teaStore.origins.length" class="filter-group__hint">产地选项加载中…</span>
          </div>
        </div>

        <div class="filter-group">
          <div class="filter-group__label">采摘季节</div>
          <div class="filter-chips">
            <button
              v-for="season in TEA_SEASONS"
              :key="season"
              type="button"
              class="chip chip--default"
              :class="{ 'chip--active': state.seasons.includes(season) }"
              :aria-pressed="state.seasons.includes(season)"
              @click="toggleSeason(season)"
            >
              {{ season }}
            </button>
          </div>
        </div>

        <div class="filter-group">
          <div class="filter-group__label">发酵程度</div>
          <div class="filter-chips">
            <button
              v-for="fermentation in TEA_FERMENTATIONS"
              :key="fermentation"
              type="button"
              class="chip chip--default"
              :class="{ 'chip--active': state.fermentations.includes(fermentation) }"
              :aria-pressed="state.fermentations.includes(fermentation)"
              @click="toggleFermentation(fermentation)"
            >
              {{ fermentation }}
            </button>
          </div>
        </div>

        <div class="filter-group">
          <div class="filter-group__label">价格区间（元/斤）</div>
          <div class="price-range">
            <select
              class="price-range__select"
              aria-label="价格下限"
              :value="state.priceMin ?? 0"
              @change="setPriceMin(($event.target as HTMLSelectElement).value)"
            >
              <option v-for="opt in PRICE_OPTIONS" :key="`min-${opt}`" :value="opt">
                {{ opt === 0 ? '最低不限' : `¥${opt}` }}
              </option>
            </select>
            <span class="price-range__sep">–</span>
            <select
              class="price-range__select"
              aria-label="价格上限"
              :value="state.priceMax ?? 0"
              @change="setPriceMax(($event.target as HTMLSelectElement).value)"
            >
              <option v-for="opt in PRICE_OPTIONS" :key="`max-${opt}`" :value="opt">
                {{ opt === 0 ? '最高不限' : `¥${opt}` }}
              </option>
            </select>
          </div>
        </div>

        <div class="filter-group">
          <div class="filter-group__label">组合方式</div>
          <div class="mode-switch" role="group" aria-label="筛选组合方式">
            <button
              type="button"
              class="mode-switch__btn"
              :class="{ 'mode-switch__btn--active': state.filterMode === 'and' }"
              :aria-pressed="state.filterMode === 'and'"
              @click="setFilterMode('and')"
            >
              同时满足
            </button>
            <button
              type="button"
              class="mode-switch__btn"
              :class="{ 'mode-switch__btn--active': state.filterMode === 'or' }"
              :aria-pressed="state.filterMode === 'or'"
              @click="setFilterMode('or')"
            >
              任一满足
            </button>
          </div>
        </div>
      </section>

      <!-- 已选条件 -->
      <div class="filter-selected">
        <span class="filter-selected__label">已选：</span>
        <span v-if="!hasAnyFilter" class="filter-selected__empty">暂无筛选，显示全部</span>
        <span v-if="state.keyword" class="filter-selected__pill">
          搜索：{{ state.keyword }}
          <button type="button" aria-label="移除关键词" @click="clearKeyword">×</button>
        </span>
        <span
          v-for="filter in activeFilters"
          :key="`${filter.dimension}-${filter.value}`"
          class="filter-selected__pill"
        >
          {{ filter.label }}
          <button type="button" :aria-label="`移除${filter.label}`" @click="removeFilter(filter)">
            ×
          </button>
        </span>
        <span v-if="hasPrice" class="filter-selected__pill">
          {{ priceText }}
          <button type="button" aria-label="移除价格区间" @click="clearPrice">×</button>
        </span>
        <button v-if="hasAnyFilter" type="button" class="filter-selected__clear" @click="clearAll">
          清除全部
        </button>
      </div>

      <!-- 结果数 -->
      <div class="list-meta">{{ resultText }}</div>

      <!-- 骨架屏 -->
      <div v-if="teaStore.loading" class="tea-grid" aria-hidden="true">
        <div v-for="n in 6" :key="n" class="skeleton-card">
          <div class="skeleton skeleton-card__img"></div>
          <div class="skeleton-card__body">
            <div class="skeleton skeleton-card__line skeleton-card__line--title"></div>
            <div class="skeleton skeleton-card__line" style="width: 60%"></div>
            <div
              class="skeleton skeleton-card__line skeleton-card__line--sm"
              style="width: 40%"
            ></div>
          </div>
        </div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="teaStore.error" class="state-box">
        <p class="state-box__text">加载失败：{{ teaStore.error }}</p>
        <button type="button" class="btn btn--secondary" @click="load">重新加载</button>
      </div>

      <!-- 结果网格 -->
      <template v-else-if="teaStore.list.length">
        <div class="tea-grid">
          <TeaCard v-for="tea in teaStore.list" :key="tea.id" :tea="tea" />
        </div>

        <nav v-if="totalPages > 1" class="pagination" aria-label="分页">
          <button
            type="button"
            class="pagination__btn"
            :disabled="teaStore.page <= 1"
            aria-label="上一页"
            @click="goPage(teaStore.page - 1)"
          >
            ‹
          </button>
          <template v-for="(item, index) in pageItems" :key="index">
            <span v-if="item === 'ellipsis'" class="pagination__ellipsis">…</span>
            <button
              v-else
              type="button"
              class="pagination__btn"
              :class="{ 'pagination__btn--active': item === teaStore.page }"
              @click="goPage(item)"
            >
              {{ item }}
            </button>
          </template>
          <button
            type="button"
            class="pagination__btn"
            :disabled="teaStore.page >= totalPages"
            aria-label="下一页"
            @click="goPage(teaStore.page + 1)"
          >
            ›
          </button>
        </nav>
      </template>

      <!-- 空结果 -->
      <div v-else class="empty-state">
        <div class="empty-state__icon">🫖</div>
        <h3 class="empty-state__title">暂无符合条件的茶品</h3>
        <p class="empty-state__desc">试试调整筛选条件，或者清除全部筛选看看</p>
        <button type="button" class="btn btn--secondary" @click="clearAll">清除全部筛选</button>

        <div v-if="suggestions.length" class="empty-state__suggest">
          <TeaCard v-for="tea in suggestions" :key="tea.id" :tea="tea" compact />
        </div>
      </div>
    </div>
  </main>

  <AppFooter />
</template>

<style scoped>
.tea-list-page {
  padding-top: 88px;
  padding-bottom: 48px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
}

@media (max-width: 1023px) {
  .container {
    padding: 0 24px;
  }
}

@media (max-width: 767px) {
  .tea-list-page {
    padding-top: 76px;
  }
  .container {
    padding: 0 16px;
  }
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  padding: 8px 0 20px;
}

.breadcrumb__sep {
  color: var(--color-border-dark);
}

.breadcrumb__current {
  color: var(--color-text-primary);
}

.breadcrumb__compare {
  margin-left: auto;
  font-size: var(--text-small);
  color: var(--color-primary);
}

.breadcrumb__compare:hover {
  text-decoration: underline;
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar__cats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.toolbar__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.filter-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-dark);
  background: var(--color-bg-surface);
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    border-color 0.2s,
    color 0.2s;
}

.filter-toggle:hover,
.filter-toggle--open {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.filter-toggle__badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: 11px;
  line-height: 18px;
  text-align: center;
}

.filter-toggle__chevron {
  transition: transform 0.2s;
}

.filter-toggle--open .filter-toggle__chevron {
  transform: rotate(180deg);
}

.filter-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 20px;
  margin-bottom: 16px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group__label {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  font-weight: 500;
  letter-spacing: 0.5px;
}

.filter-group__hint {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.price-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.price-range__select {
  height: 36px;
  padding: 0 28px 0 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-dark);
  background: var(--color-bg-surface);
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  cursor: pointer;
  outline: none;
  appearance: none;
}

.price-range__select:focus {
  border-color: var(--color-primary);
}

.price-range__sep {
  color: var(--color-text-muted);
}

.mode-switch {
  display: inline-flex;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.mode-switch__btn {
  height: 36px;
  padding: 0 16px;
  border: none;
  background: transparent;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s;
}

.mode-switch__btn + .mode-switch__btn {
  border-left: 1px solid var(--color-border-dark);
}

.mode-switch__btn--active {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  font-size: var(--text-small);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  background: transparent;
  border: 1px solid var(--color-border-dark);
  color: var(--color-text-secondary);
  user-select: none;
}

.chip:hover {
  background: var(--color-bg-muted);
}

.chip__count {
  font-size: var(--text-caption);
  opacity: 0.75;
}

.chip--green {
  border-color: var(--color-tea-green);
  color: var(--color-tea-green);
}

.chip--green.chip--active {
  background: var(--color-tea-green);
  color: var(--color-text-inverse);
}

.chip--white {
  border-color: var(--color-tea-white);
  color: var(--color-primary-dark);
}

.chip--white.chip--active {
  background: var(--color-tea-white);
  color: var(--color-text-primary);
}

.chip--yellow {
  border-color: var(--color-tea-yellow);
  color: var(--color-primary-dark);
}

.chip--yellow.chip--active {
  background: var(--color-tea-yellow);
  color: var(--color-text-inverse);
}

.chip--red {
  border-color: var(--color-tea-red);
  color: var(--color-tea-red);
}

.chip--red.chip--active {
  background: var(--color-tea-red);
  color: var(--color-text-inverse);
}

.chip--oolong {
  border-color: var(--color-tea-oolong);
  color: var(--color-tea-oolong);
}

.chip--oolong.chip--active {
  background: var(--color-tea-oolong);
  color: var(--color-text-inverse);
}

.chip--dark {
  border-color: var(--color-tea-dark);
  color: var(--color-tea-dark);
}

.chip--dark.chip--active {
  background: var(--color-tea-dark);
  color: var(--color-text-inverse);
}

.chip--reprocessed {
  border-color: var(--color-tea-reprocessed);
  color: var(--color-tea-reprocessed);
}

.chip--reprocessed.chip--active {
  background: var(--color-tea-reprocessed);
  color: var(--color-text-inverse);
}

.chip--default.chip--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.filter-selected {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  margin-bottom: 24px;
  min-height: 48px;
}

.filter-selected__label {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  margin-right: 4px;
}

.filter-selected__empty {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.filter-selected__pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 8px 0 12px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  font-size: var(--text-caption);
  color: var(--color-text-primary);
}

.filter-selected__pill button {
  width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  border: none;
  background: var(--color-border-dark);
  color: var(--color-bg-surface);
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.filter-selected__pill button:hover {
  background: var(--color-error);
}

.filter-selected__clear {
  margin-left: auto;
  font-size: var(--text-small);
  color: var(--color-primary);
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
}

.filter-selected__clear:hover {
  color: var(--color-primary-hover);
}

.list-meta {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin-bottom: 12px;
}

.sort-select {
  height: 36px;
  padding: 0 32px 0 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-dark);
  background: var(--color-bg-surface);
  font-size: var(--text-small);
  color: var(--color-text-primary);
  cursor: pointer;
  outline: none;
  appearance: none;
}

.sort-select:focus {
  border-color: var(--color-primary);
}

.tea-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

@media (max-width: 1023px) {
  .tea-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}

@media (max-width: 639px) {
  .tea-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.skeleton-card {
  border-radius: var(--radius-lg);
}

.skeleton {
  background: var(--color-bg-muted);
  border-radius: var(--radius-sm);
  position: relative;
  overflow: hidden;
}

.skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    var(--color-bg-muted) 0%,
    var(--color-border) 50%,
    var(--color-bg-muted) 100%
  );
  animation: skeleton-shimmer 1.5s infinite;
}

@keyframes skeleton-shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.skeleton-card__img {
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: var(--radius-lg);
}

.skeleton-card__body {
  padding: 12px 2px 0;
}

.skeleton-card__line {
  height: 16px;
  margin-bottom: 10px;
  border-radius: var(--radius-sm);
}

.skeleton-card__line--title {
  width: 70%;
  height: 20px;
}

.skeleton-card__line--sm {
  width: 40%;
  height: 14px;
}

.state-box {
  padding: 64px 24px;
  text-align: center;
}

.state-box__text {
  font-size: var(--text-small);
  color: var(--color-error);
  margin: 0 0 20px;
}

.empty-state {
  text-align: center;
  padding: 64px 24px;
}

.empty-state__icon {
  font-size: 56px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-state__title {
  font-size: var(--text-h3);
  color: var(--color-text-secondary);
  margin: 0 0 8px;
}

.empty-state__desc {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin: 0 0 24px;
}

.empty-state__suggest {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 560px;
  margin: 32px auto 0;
}

@media (max-width: 639px) {
  .empty-state__suggest {
    grid-template-columns: 1fr;
  }
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0 20px;
}

.pagination__btn {
  min-width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  color: var(--color-text-secondary);
  font-size: var(--text-small);
  cursor: pointer;
  transition: all 0.2s;
}

.pagination__btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.pagination__btn--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.pagination__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination__ellipsis {
  color: var(--color-text-muted);
  font-size: var(--text-small);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  padding: 0 24px;
  border-radius: var(--radius-full);
  font-size: var(--text-body);
  font-weight: 500;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
  white-space: nowrap;
}

.btn--secondary {
  background: transparent;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}

.btn--secondary:hover {
  background: var(--color-bg-muted);
}
</style>
