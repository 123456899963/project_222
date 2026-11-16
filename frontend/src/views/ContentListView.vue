<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import { getContentList, getContentTypes } from '@/api/contents'
import type { ContentItem, ContentTypeCode, ContentTypeItem } from '@/types'

const route = useRoute()
const typeCode = computed<ContentTypeCode>(
  () => (route.params.code as ContentTypeCode) ?? 'teaware',
)

const types = ref<ContentTypeItem[]>([])
const items = ref<ContentItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(true)
const headerItem = ref<ContentTypeItem | null>(null)

const keyword = ref('')
const searchInput = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

async function loadTypes() {
  try {
    types.value = await getContentTypes()
    headerItem.value = types.value.find((t) => t.code === typeCode.value) ?? null
  } catch {
    types.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await getContentList({
      type: typeCode.value,
      keyword: keyword.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    items.value = data.items
    total.value = data.total
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function onPageChange(p: number) {
  page.value = p
  void loadList()
}

function clearSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchInput.value = ''
  if (!keyword.value) return
  keyword.value = ''
  page.value = 1
  void loadList()
}

onMounted(async () => {
  await loadTypes()
  await loadList()
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

// 关键词输入 300ms 防抖；变化后回到第 1 页重新查询
watch(searchInput, (value) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    const next = value.trim()
    if (next === keyword.value) return
    keyword.value = next
    page.value = 1
    void loadList()
  }, 300)
})

// 五个板块共用 /contents/:code，切换时组件实例被复用，
// 必须监听参数变化重新加载，否则内容停留在旧板块。
watch(
  () => route.params.code,
  async (code) => {
    if (!code || code === headerItem.value?.code) return
    page.value = 1
    headerItem.value = types.value.find((t) => t.code === code) ?? null
    if (types.value.length === 0) {
      await loadTypes()
    }
    await loadList()
  },
)
</script>

<template>
  <div class="content-list-page">
    <AppHeader />

    <main class="content-list-page__main">
      <!-- 面包屑 -->
      <nav class="content-list-page__breadcrumb">
        <RouterLink to="/">首页</RouterLink>
        <span class="separator">›</span>
        <span>茶文化</span>
        <span class="separator">›</span>
        <span class="current">{{ headerItem?.name ?? typeCode }}</span>
      </nav>

      <!-- 板块头部：标题与搜索同排 -->
      <section v-if="headerItem" class="content-list-page__hero">
        <div class="content-list-page__hero-main">
          <p class="page-kicker">Tea Culture</p>
          <div class="content-list-page__hero-title">
            <span class="content-list-page__icon">{{ headerItem.icon ?? '📖' }}</span>
            <h1 class="content-list-page__title">{{ headerItem.name }}</h1>
          </div>
          <p v-if="headerItem.description" class="content-list-page__desc">
            {{ headerItem.description }}
          </p>
        </div>

        <div class="content-list-page__search">
          <svg
            class="content-list-page__search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            v-model="searchInput"
            class="content-list-page__search-input"
            type="text"
            maxlength="100"
            placeholder="搜索标题或摘要"
            aria-label="搜索本板块内容"
          />
          <button
            v-if="searchInput"
            class="content-list-page__search-clear"
            type="button"
            aria-label="清空搜索"
            @click="clearSearch"
          >
            ×
          </button>
        </div>
      </section>

      <!-- 列表 -->
      <section class="content-list-page__grid-section">
        <!-- 结果统计 -->
        <p class="content-list-page__result">
          <template v-if="keyword">
            找到 <strong>{{ total }}</strong> 篇与「{{ keyword }}」相关的内容
          </template>
          <template v-else>
            共 <strong>{{ total }}</strong> 篇内容
          </template>
        </p>

        <div v-if="loading" class="content-list-page__loading">加载中...</div>

        <div v-else-if="items.length === 0" class="content-list-page__empty">
          <p>该板块暂无内容</p>
          <p class="hint">管理员正在持续补充中，敬请期待～</p>
        </div>

        <div v-else class="content-list-page__grid">
          <article v-for="item in items" :key="item.id" class="content-list-page__card">
            <RouterLink :to="`/contents/${typeCode}/${item.id}`" class="card-link">
              <div v-if="item.cover_image" class="card-image">
                <img :src="item.cover_image" :alt="item.title" loading="lazy" />
              </div>
              <div v-else class="card-image card-image--placeholder">
                <span class="placeholder-icon">{{ headerItem?.icon ?? '📖' }}</span>
              </div>
              <div class="card-body">
                <h3 class="card-title">{{ item.title }}</h3>
                <p v-if="item.summary" class="card-summary">{{ item.summary }}</p>
              </div>
            </RouterLink>
          </article>
        </div>

        <!-- 分页 -->
        <nav v-if="totalPages > 1" class="content-list-page__pagination" aria-label="分页">
          <button class="page-btn" :disabled="page <= 1" @click="onPageChange(page - 1)">
            上一页
          </button>
          <span class="page-info"> {{ page }} / {{ totalPages }} </span>
          <button class="page-btn" :disabled="page >= totalPages" @click="onPageChange(page + 1)">
            下一页
          </button>
        </nav>
      </section>
    </main>

    <AppFooter />
  </div>
</template>

<style scoped>
.content-list-page__main {
  max-width: 1200px;
  margin: 88px auto 0;
  padding: 0 32px 80px;
}

.content-list-page__breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin-bottom: 24px;
}
.content-list-page__breadcrumb a {
  color: var(--color-text-secondary);
}
.content-list-page__breadcrumb a:hover {
  color: var(--color-primary);
}
.content-list-page__breadcrumb .separator {
  color: var(--color-border);
}
.content-list-page__breadcrumb .current {
  color: var(--color-text-primary);
}

.content-list-page__hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  padding: 8px 0 28px;
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: 24px;
}
.content-list-page__hero-main {
  min-width: 0;
}
.content-list-page__hero-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.content-list-page__icon {
  font-size: 36px;
  line-height: 1;
}
.content-list-page__title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  color: var(--color-primary-dark);
  margin: 0;
}
.content-list-page__desc {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  max-width: 640px;
  margin: 10px 0 0;
  line-height: 1.8;
}

/* —— 结果统计 —— */
.content-list-page__result {
  margin: 0 0 16px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
}
.content-list-page__result strong {
  color: var(--color-text-primary);
  font-weight: 600;
}

.content-list-page__search {
  position: relative;
  flex: 0 0 300px;
  align-self: center;
}
.content-list-page__search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
  pointer-events: none;
  transition: color 0.2s;
}
.content-list-page__search:focus-within .content-list-page__search-icon {
  color: var(--color-primary);
}
.content-list-page__search-input {
  width: 100%;
  height: 38px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  padding: 0 34px 0 38px;
  font-size: var(--text-small);
  color: var(--color-text-primary);
  outline: none;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
.content-list-page__search-input::placeholder {
  color: var(--color-text-muted);
}
.content-list-page__search-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(139, 115, 85, 0.08);
}
.content-list-page__search-clear {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}
.content-list-page__search-clear:hover {
  color: var(--color-primary);
}

.content-list-page__loading,
.content-list-page__empty {
  text-align: center;
  padding: 60px 0;
  color: var(--color-text-muted);
}
.content-list-page__empty p {
  margin: 8px 0;
}
.content-list-page__empty .hint {
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.content-list-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
}

.content-list-page__card {
  background: var(--color-bg-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--color-border-light);
  transition:
    box-shadow 0.2s,
    transform 0.2s;
}
.content-list-page__card:hover {
  box-shadow: 0 4px 20px rgba(139, 115, 85, 0.1);
  transform: translateY(-2px);
}
.content-list-page__card .card-link {
  display: block;
  text-decoration: none;
  color: inherit;
}
.card-image {
  width: 100%;
  height: 180px;
  overflow: hidden;
  background: var(--color-bg-muted);
}
.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.card-image--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}
.placeholder-icon {
  font-size: 56px;
  opacity: 0.3;
}
.card-body {
  padding: 16px 20px 20px;
}
.card-title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--color-primary-dark);
  margin: 0 0 8px;
  line-height: 1.4;
}
.card-summary {
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}

.content-list-page__pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 48px;
}
.page-btn {
  padding: 8px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-secondary);
  font-size: var(--text-small);
  cursor: pointer;
  transition: all 0.2s;
}
.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

@media (max-width: 767px) {
  .content-list-page__main {
    padding: 0 16px 40px;
    margin-top: 76px;
  }
  .content-list-page__grid {
    grid-template-columns: 1fr;
  }
  .content-list-page__hero {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
    padding: 4px 0 20px;
    margin-bottom: 16px;
  }
  .content-list-page__search {
    flex: 1 1 auto;
  }
}
</style>
