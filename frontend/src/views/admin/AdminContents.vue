<script setup lang="ts">
/**
 * 管理员内容管理后台（批次五 R1–R5）：列表 + 筛选 + 软删除
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RouterLink, useRouter } from 'vue-router'
import { deleteAdminContent, getAdminContents } from '@/api/admin'
import type { AdminContentListData, AdminContentListItem, ContentTypeCode } from '@/types'

const router = useRouter()

const TYPE_LABELS: Record<ContentTypeCode, string> = {
  teaware: '茶具茶器',
  origin: '茶叶产地',
  culture: '茶叶文化',
  brand: '茶叶品牌',
  knowledge: '茶叶知识',
}

const state = ref<'loading' | 'ready' | 'error'>('loading')
const data = ref<AdminContentListData>({ items: [], total: 0, page: 1, page_size: 12 })
const filters = reactive<{ type: ContentTypeCode | ''; is_active: boolean | null }>({
  type: '',
  is_active: null,
})
const page = ref(1)
const pageSize = ref(12)

async function load() {
  state.value = 'loading'
  try {
    const res = await getAdminContents({
      type: filters.type || undefined,
      is_active: filters.is_active,
      page: page.value,
      page_size: pageSize.value,
    })
    data.value = res.data
    state.value = 'ready'
  } catch {
    state.value = 'error'
  }
}

function onFilterChange() {
  page.value = 1
  void load()
}

async function onDelete(item: AdminContentListItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${item.title}」？删除后前台不再可见（软删除，可在数据库恢复）。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await deleteAdminContent(item.id)
    ElMessage.success('已软删除')
    void load()
  } catch (err: unknown) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function formatDate(v: string): string {
  return new Date(v).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

onMounted(load)
</script>

<template>
  <div class="admin-contents">
    <!-- 筛选栏 -->
    <div class="admin-contents__filters">
      <el-select
        v-model="filters.type"
        placeholder="全部板块"
        clearable
        @change="onFilterChange"
        style="width: 160px"
      >
        <el-option v-for="(label, code) in TYPE_LABELS" :key="code" :value="code" :label="label" />
      </el-select>
      <el-select
        v-model="filters.is_active"
        placeholder="全部状态"
        clearable
        @change="onFilterChange"
        style="width: 140px"
      >
        <el-option :value="true" label="上架" />
        <el-option :value="false" label="下架" />
      </el-select>

      <div class="admin-contents__actions">
        <el-button type="primary" @click="router.push('/admin/contents/new')">新增内容</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table v-if="state === 'ready'" :data="data.items" stripe border style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="type_code" label="板块" width="110">
        <template #default="{ row }">{{ TYPE_LABELS[row.type_code] }}</template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="summary" label="摘要" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.summary ?? '—' }}</template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '上架' : '下架' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="70" />
      <el-table-column prop="updated_at" label="更新时间" width="170">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <RouterLink :to="`/admin/contents/${row.id}/edit`">
            <el-button link type="primary" size="small">编辑</el-button>
          </RouterLink>
          <el-button
            link
            type="danger"
            size="small"
            :disabled="!row.is_active"
            @click="onDelete(row)"
            >软删除</el-button
          >
        </template>
      </el-table-column>
    </el-table>

    <div v-else-if="state === 'loading'" class="admin-contents__empty">加载中...</div>
    <div v-else class="admin-contents__empty">加载失败，请刷新重试</div>

    <!-- 分页 -->
    <div v-if="state === 'ready' && data.total > pageSize" class="admin-contents__pager">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="data.total"
        layout="prev, pager, next, total"
        @current-change="
          (p: number) => {
            page = p
            void load()
          }
        "
      />
    </div>
  </div>
</template>

<style scoped>
.admin-contents__filters {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
}
.admin-contents__actions {
  margin-left: auto;
}
.admin-contents__empty {
  text-align: center;
  padding: 60px;
  color: var(--color-text-muted);
}
.admin-contents__pager {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
