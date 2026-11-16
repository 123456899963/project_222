<script setup lang="ts">
/**
 * 七大茶类摘要对比（S3）
 *
 * 纯前端页面：每个茶类取一款代表茶（收藏最多）→ 拉取详情 → 组装七列对比表。
 * 无后端契约变更，数据全部来自既有只读接口。
 */

import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import CategoryTag from '@/components/CategoryTag.vue'
import { getTeaDetail, getTeaList } from '@/api/teas'
import { CATEGORY_LABELS, TEA_CATEGORIES } from '@/utils/teaQuery'
import { buildCompareMatrix } from '@/utils/compare'
import type { CompareMap } from '@/utils/compare'
import type { Tea, TeaCategory } from '@/types'

const loading = ref(true)
const teas = ref<CompareMap>({})

const columns = computed(() =>
  TEA_CATEGORIES.map((category) => ({
    category,
    label: CATEGORY_LABELS[category],
    tea: teas.value[category] ?? null,
  })),
)

const rows = computed(() => buildCompareMatrix(teas.value))

async function loadCategory(category: TeaCategory): Promise<[TeaCategory, Tea | null]> {
  try {
    const list = await getTeaList({ category, page: 1, page_size: 1, sort: 'favorite' })
    const first = list.data?.items?.[0]
    if (!first) return [category, null]
    const detail = await getTeaDetail(first.id)
    return [category, detail.data ?? null]
  } catch {
    return [category, null]
  }
}

async function load() {
  loading.value = true
  try {
    const results = await Promise.all(TEA_CATEGORIES.map((c) => loadCategory(c)))
    const map: CompareMap = {}
    for (const [category, tea] of results) map[category] = tea
    teas.value = map
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <AppHeader />

  <main class="compare-page">
    <div class="container">
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <RouterLink to="/teas">茶品列表</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">七大茶类对比</span>
      </nav>

      <header class="compare-header">
        <p class="page-kicker page-kicker--center">Side by Side</p>
        <h1 class="compare-header__title">七大茶类摘要对比</h1>
        <p class="compare-header__desc">
          每类甄选一款代表茶，横向对比外形、汤色、香气、滋味与冲泡要点。
        </p>
      </header>

      <div v-if="loading" class="compare-loading">对比数据加载中…</div>

      <div v-else class="compare-table-wrap">
        <table class="compare-table">
          <thead>
            <tr>
              <th scope="col" class="compare-table__corner">维度</th>
              <th v-for="col in columns" :key="col.category" scope="col">
                <RouterLink
                  class="compare-table__cat"
                  :to="{ name: 'tea-list', query: { category: col.category } }"
                >
                  <CategoryTag :category="col.category" />
                  <span class="compare-table__cat-name">{{ col.label }}</span>
                </RouterLink>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in rows" :key="row.label">
              <th scope="row" class="compare-table__row-label">{{ row.label }}</th>
              <td v-for="(value, colIndex) in row.values" :key="colIndex">
                <RouterLink
                  v-if="rowIndex === 0 && value && columns[colIndex]?.tea"
                  class="compare-table__tea-link"
                  :to="{ name: 'tea-detail', params: { id: columns[colIndex].tea!.id } }"
                >
                  {{ value }}
                </RouterLink>
                <template v-else>{{ value ?? '—' }}</template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </main>

  <AppFooter />
</template>

<style scoped>
.compare-page {
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
  .compare-page {
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

.compare-header {
  text-align: center;
  margin-bottom: 32px;
}

.compare-header__title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 8px;
}

.compare-header__desc {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin: 0;
}

.compare-loading {
  padding: 64px 0;
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-small);
}

.compare-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1000px;
}

.compare-table th,
.compare-table td {
  padding: 16px;
  text-align: left;
  font-size: var(--text-small);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: top;
}

.compare-table tbody tr:last-child th,
.compare-table tbody tr:last-child td {
  border-bottom: none;
}

.compare-table__corner,
.compare-table__row-label {
  width: 88px;
  color: var(--color-text-muted);
  font-weight: 500;
  background: var(--color-bg-muted);
  white-space: nowrap;
}

.compare-table thead th {
  background: var(--color-bg-muted);
  border-bottom: 1px solid var(--color-border);
}

.compare-table__cat {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.compare-table__cat-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.compare-table__tea-link {
  color: var(--color-primary);
  font-weight: 600;
}

.compare-table__tea-link:hover {
  text-decoration: underline;
}
</style>
