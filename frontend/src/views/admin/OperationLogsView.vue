<script setup lang="ts">
/**
 * 管理员操作日志查询（API_CONTRACT §4.6.12）
 * 只读页：动作 / 目标类型 / 管理员 ID / 起止日期筛选 + 分页表格。
 */
import { onMounted, reactive, ref } from 'vue'
import { getAdminOperationLogs } from '@/api/admin'
import type { AdminOperationLogItem, AdminOperationLogListData } from '@/types'

const loading = ref(false)
const data = ref<AdminOperationLogListData>({ items: [], total: 0, page: 1, page_size: 20 })
const page = ref(1)
const pageSize = ref(20)

const filters = reactive<{
  action: string
  target_type: string
  admin_id: number | undefined
  range: [string, string] | null
}>({
  action: '',
  target_type: '',
  admin_id: undefined,
  range: null,
})

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

async function load() {
  loading.value = true
  try {
    const res = await getAdminOperationLogs({
      action: filters.action.trim() || undefined,
      target_type: filters.target_type.trim() || undefined,
      admin_id: filters.admin_id || undefined,
      start_date: filters.range?.[0] || undefined,
      end_date: filters.range?.[1] || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    data.value = res.data
  } catch {
    // 错误提示由 axios 响应拦截器统一处理
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  void load()
}

function reset() {
  filters.action = ''
  filters.target_type = ''
  filters.admin_id = undefined
  filters.range = null
  search()
}

function actionTagType(action: string): 'success' | 'warning' | 'danger' | 'info' {
  if (action.startsWith('create')) return 'success'
  if (action.startsWith('delete')) return 'danger'
  if (action.startsWith('update') || action.startsWith('toggle')) return 'warning'
  return 'info'
}

function rowKey(row: AdminOperationLogItem): number {
  return row.id
}

onMounted(load)
</script>

<template>
  <section class="oplog-admin">
    <header class="oplog-admin__head">
      <div>
        <h1 class="oplog-admin__title">操作日志</h1>
        <p class="text-small text-muted">
          记录管理员写操作，按时间倒序；可按动作、类型、操作人与日期检索。
        </p>
      </div>
    </header>

    <div class="oplog-admin__filters">
      <el-input
        v-model="filters.action"
        class="oplog-admin__input"
        size="small"
        clearable
        placeholder="动作，如 create_tea"
        @keyup.enter="search"
      />
      <el-input
        v-model="filters.target_type"
        class="oplog-admin__input"
        size="small"
        clearable
        placeholder="目标类型，如 tea"
        @keyup.enter="search"
      />
      <el-input-number
        v-model="filters.admin_id"
        class="oplog-admin__input"
        size="small"
        :min="1"
        :controls="false"
        placeholder="管理员 ID"
      />
      <el-date-picker
        v-model="filters.range"
        size="small"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
      />
      <el-button size="small" type="primary" @click="search">查询</el-button>
      <el-button size="small" @click="reset">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="data.items" :row-key="rowKey" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="操作人" width="160">
        <template #default="{ row }">
          <span v-if="row.admin_username">{{ row.admin_username }}</span>
          <span v-else class="text-muted">已删除账号</span>
          <span v-if="row.admin_id" class="text-small text-muted">（#{{ row.admin_id }}）</span>
        </template>
      </el-table-column>
      <el-table-column label="动作" width="150">
        <template #default="{ row }">
          <el-tag size="small" :type="actionTagType(row.action)">{{ row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_type" label="目标类型" width="110" />
      <el-table-column label="目标 ID" width="90">
        <template #default="{ row }">{{ row.target_id ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="详情" min-width="220">
        <template #default="{ row }">{{ row.detail || '—' }}</template>
      </el-table-column>
      <el-table-column label="IP" width="130">
        <template #default="{ row }">{{ row.ip_address || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <template #empty>
        <div class="oplog-admin__empty">当前筛选下暂无日志</div>
      </template>
    </el-table>

    <div class="oplog-admin__pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="data.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="load"
        @size-change="search"
      />
    </div>
  </section>
</template>

<style scoped>
.oplog-admin {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.oplog-admin__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}
.oplog-admin__title {
  font-size: var(--text-h2);
  color: var(--color-primary-dark);
}
.oplog-admin__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.oplog-admin__input {
  width: 170px;
}
.oplog-admin__pager {
  display: flex;
  justify-content: flex-end;
}
.oplog-admin__empty {
  padding: 24px;
  color: var(--color-text-muted);
}
</style>
