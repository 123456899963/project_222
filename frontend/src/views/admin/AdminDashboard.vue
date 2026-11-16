<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getAdminStats, getAdminTeas } from '@/api/admin'
import { CATEGORY_LABELS } from '@/utils/teaQuery'
import type { AdminStatsData, AdminTeaListItem, TeaCategory } from '@/types'

const loading = ref(true)
const stats = ref<AdminStatsData | null>(null)
const recent = ref<AdminTeaListItem[]>([])

const maxCategoryCount = computed(() => {
  const values = stats.value?.category_distribution.map((item) => item.count) ?? [0]
  return Math.max(1, ...values)
})

function barWidth(count: number) {
  return `${Math.round((count / maxCategoryCount.value) * 100)}%`
}

onMounted(async () => {
  try {
    const [statsRes, recentRes] = await Promise.all([
      getAdminStats(),
      getAdminTeas({ page: 1, page_size: 5, sort: 'newest' }),
    ])
    stats.value = statsRes.data
    recent.value = recentRes.data.items
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <h2 class="text-h2">数据概览</h2>
      <el-button type="primary" @click="$router.push({ name: 'admin-tea-new' })">
        新增茶品
      </el-button>
    </div>

    <div v-if="stats" class="stat-grid">
      <div class="stat-card">
        <span class="stat-label">茶品总数</span>
        <strong class="stat-value">{{ stats.total_count }}</strong>
      </div>
      <div class="stat-card">
        <span class="stat-label">已上架</span>
        <strong class="stat-value text-success">{{ stats.active_count }}</strong>
      </div>
      <div class="stat-card">
        <span class="stat-label">已下架</span>
        <strong class="stat-value text-muted">{{ stats.inactive_count }}</strong>
      </div>
    </div>

    <section v-if="stats" class="panel">
      <h3 class="text-h3 panel-title">七大茶类分布</h3>
      <div class="distribution">
        <div
          v-for="item in stats.category_distribution"
          :key="item.category"
          class="distribution-row"
        >
          <span class="distribution-label">
            {{ CATEGORY_LABELS[item.category as TeaCategory] }}
          </span>
          <div class="distribution-track">
            <div class="distribution-bar" :style="{ width: barWidth(item.count) }" />
          </div>
          <span class="distribution-count">{{ item.count }}</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3 class="text-h3 panel-title">最近更新的茶品</h3>
        <router-link class="text-small" :to="{ name: 'admin-teas' }">查看全部 →</router-link>
      </div>
      <el-table :data="recent" size="small" empty-text="暂无茶品">
        <el-table-column prop="name" label="茶名" min-width="140" />
        <el-table-column label="茶类" width="90">
          <template #default="{ row }">
            {{ CATEGORY_LABELS[row.category as TeaCategory] }}
          </template>
        </el-table-column>
        <el-table-column prop="origin" label="产地" min-width="140" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '已上架' : '已下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="$router.push({ name: 'admin-tea-edit', params: { id: row.id } })"
            >
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-head h2 {
  margin: 0;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-hero);
}
.stat-label {
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}
.stat-value {
  font-size: var(--text-h1);
  line-height: 1.2;
}
.panel {
  margin-bottom: 20px;
  padding: 20px 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-title {
  margin: 0 0 16px;
}
.panel-head .panel-title {
  margin-bottom: 12px;
}
.distribution {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.distribution-row {
  display: grid;
  grid-template-columns: 72px 1fr 40px;
  align-items: center;
  gap: 12px;
}
.distribution-label {
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}
.distribution-track {
  height: 10px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  overflow: hidden;
}
.distribution-bar {
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--color-primary);
}
.distribution-count {
  text-align: right;
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
</style>
