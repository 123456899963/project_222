<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminTeas, toggleAdminTea } from '@/api/admin'
import { CATEGORY_LABELS, TEA_CATEGORIES } from '@/utils/teaQuery'
import type { AdminTeaListItem, AdminTeaListParams, TeaCategory } from '@/types'

const router = useRouter()

const items = ref<AdminTeaListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)

const filters = reactive({
  category: '' as '' | TeaCategory,
  status: 'all' as 'all' | 'true' | 'false',
  keyword: '',
})

async function load() {
  loading.value = true
  try {
    const params: AdminTeaListParams = { page: page.value, page_size: pageSize }
    if (filters.category) params.category = filters.category
    if (filters.status === 'true') params.is_active = true
    if (filters.status === 'false') params.is_active = false
    const keyword = filters.keyword.trim()
    if (keyword) params.keyword = keyword

    const res = await getAdminTeas(params)
    items.value = res.data.items
    total.value = res.data.total
    page.value = res.data.page
  } finally {
    loading.value = false
  }
}

function handleFilter() {
  page.value = 1
  load()
}

async function handleToggle(row: AdminTeaListItem) {
  const direction = row.is_active ? '下架' : '上架'
  try {
    await ElMessageBox.confirm(
      `确定要${direction}「${row.name}」吗？${row.is_active ? '下架后前台将不再展示，但不会删除收藏与分享记录。' : '上架后前台立即可见。'}`,
      `${direction}确认`,
      { type: 'warning', confirmButtonText: `确认${direction}`, cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await toggleAdminTea(row.id)
    ElMessage.success(`已${res.data.is_active ? '上架' : '下架'}：${row.name}`)
    await load()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2 class="text-h2">茶品管理</h2>
        <p class="text-small text-secondary">包含已下架茶品；上下架不会物理删除数据。</p>
      </div>
      <el-button type="primary" @click="router.push({ name: 'admin-tea-new' })">
        新增茶品
      </el-button>
    </div>

    <div class="toolbar">
      <el-select
        v-model="filters.category"
        placeholder="全部茶类"
        clearable
        class="filter-select"
        @change="handleFilter"
      >
        <el-option
          v-for="category in TEA_CATEGORIES"
          :key="category"
          :label="CATEGORY_LABELS[category]"
          :value="category"
        />
      </el-select>

      <el-select v-model="filters.status" class="filter-select" @change="handleFilter">
        <el-option label="全部状态" value="all" />
        <el-option label="已上架" value="true" />
        <el-option label="已下架" value="false" />
      </el-select>

      <el-input
        v-model="filters.keyword"
        placeholder="搜索茶名 / 产地（最多 50 字）"
        clearable
        class="filter-keyword"
        maxlength="50"
        @keyup.enter="handleFilter"
        @clear="handleFilter"
      />
      <el-button @click="handleFilter">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="items" empty-text="暂无符合条件的茶品">
      <el-table-column label="主图" width="76">
        <template #default="{ row }">
          <img v-if="row.main_image_url" :src="row.main_image_url" :alt="row.name" class="thumb" />
          <span v-else class="text-caption text-muted">无图</span>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="ID" width="64" />
      <el-table-column prop="name" label="茶名" min-width="140" />
      <el-table-column label="茶类" width="90">
        <template #default="{ row }">
          {{ CATEGORY_LABELS[row.category as TeaCategory] }}
        </template>
      </el-table-column>
      <el-table-column prop="origin" label="产地" min-width="150" />
      <el-table-column prop="season" label="季节" width="80">
        <template #default="{ row }">{{ row.season || '—' }}</template>
      </el-table-column>
      <el-table-column prop="favorite_count" label="收藏" width="70" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '已上架' : '已下架' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click="router.push({ name: 'admin-tea-edit', params: { id: row.id } })"
          >
            编辑
          </el-button>
          <el-button link :type="row.is_active ? 'warning' : 'success'" @click="handleToggle(row)">
            {{ row.is_active ? '下架' : '上架' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        background
        @current-change="load"
      />
    </div>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}
.page-head h2 {
  margin: 0 0 4px;
}
.page-head p {
  margin: 0;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
}
.filter-select {
  width: 150px;
}
.filter-keyword {
  width: 280px;
}
.thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  background: var(--color-bg-muted);
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
