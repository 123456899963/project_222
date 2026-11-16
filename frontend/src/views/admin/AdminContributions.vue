<script setup lang="ts">
/**
 * 管理员审核后台（S12）：提交队列 + 详情预览 + 通过 / 拒绝（预设理由）
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approveContribution, getAdminContributions, rejectContribution } from '@/api/admin'
import type {
  ContributionItem,
  ContributionListData,
  ContributionStatus,
  ContributionType,
} from '@/types'

const REJECT_PRESETS = ['信息不完整', '茶类矛盾', '重复提交', '疑似广告', '其他原因']

const state = ref<'loading' | 'ready' | 'error'>('loading')
const data = ref<ContributionListData>({ items: [], total: 0, page: 1, page_size: 10 })
const filters = reactive<{ status: ContributionStatus; type: ContributionType | '' }>({
  status: 'pending',
  type: '',
})
const page = ref(1)
const pageSize = ref(10)
const acting = ref(false)

const detailVisible = ref(false)
const activeItem = ref<ContributionItem | null>(null)

const rejectVisible = ref(false)
const rejectTarget = ref<ContributionItem | null>(null)
const rejectForm = reactive({ preset: REJECT_PRESETS[0], custom: '' })

const rejectReason = computed(() =>
  rejectForm.preset === '其他原因' ? rejectForm.custom.trim() : rejectForm.preset,
)

const summary = computed(() => (activeItem.value ? rowSummary(activeItem.value) : ''))

function payloadEntries(item: ContributionItem | null): { key: string; value: string }[] {
  if (!item) return []
  return Object.entries(item.payload ?? {})
    .filter(([, value]) => value !== null && value !== '')
    .map(([key, value]) => ({ key, value: String(value) }))
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

function rowSummary(item: ContributionItem): string {
  if (item.type === 'new_tea') {
    const name = item.payload?.name
    return typeof name === 'string' ? name : '未命名茶品'
  }
  const title = item.payload?.title
  return (typeof title === 'string' && title.trim()) || item.target_tea_name || '科普投稿'
}

async function load() {
  state.value = 'loading'
  try {
    const res = await getAdminContributions({
      status: filters.status,
      type: filters.type || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    data.value = res.data
    state.value = 'ready'
  } catch {
    state.value = 'error'
  }
}

function resetAndLoad() {
  page.value = 1
  void load()
}

function openDetail(row: ContributionItem) {
  activeItem.value = row
  detailVisible.value = true
}

async function approve(row: ContributionItem) {
  await ElMessageBox.confirm(`确认通过「${rowSummary(row)}」？`, '审核通过', {
    confirmButtonText: '通过',
    cancelButtonText: '取消',
    type: 'success',
  })
  acting.value = true
  try {
    await approveContribution(row.id)
    ElMessage.success('已通过审核')
    void load()
  } finally {
    acting.value = false
  }
}

function approveActive() {
  if (activeItem.value) void approve(activeItem.value)
}

function rejectActive() {
  if (activeItem.value) openReject(activeItem.value)
}

function openReject(row: ContributionItem) {
  rejectTarget.value = row
  rejectForm.preset = REJECT_PRESETS[0]
  rejectForm.custom = ''
  rejectVisible.value = true
}

async function submitReject() {
  if (!rejectTarget.value) return
  if (!rejectReason.value) {
    ElMessage.warning('请填写拒绝理由')
    return
  }
  acting.value = true
  try {
    await rejectContribution(rejectTarget.value.id, rejectReason.value)
    ElMessage.success('已拒绝该提交')
    rejectVisible.value = false
    void load()
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="contrib-admin">
    <header class="contrib-admin__head">
      <div>
        <h1 class="contrib-admin__title">投稿审核</h1>
        <p class="text-small text-muted">用户提交的新茶与科普先经系统校验，再由管理员人工审核。</p>
      </div>
      <div class="contrib-admin__filters">
        <el-select v-model="filters.status" size="small" @change="resetAndLoad">
          <el-option label="待审核" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已拒绝" value="rejected" />
        </el-select>
        <el-select
          v-model="filters.type"
          size="small"
          clearable
          placeholder="全部类型"
          @change="resetAndLoad"
        >
          <el-option label="补充新茶" value="new_tea" />
          <el-option label="科普投稿" value="article" />
        </el-select>
      </div>
    </header>

    <el-table v-loading="state === 'loading'" :data="data.items" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">
          {{ row.type === 'new_tea' ? '补充新茶' : '科普投稿' }}
        </template>
      </el-table-column>
      <el-table-column prop="username" label="提交人" width="140" />
      <el-table-column label="摘要" min-width="200">
        <template #default="{ row }">
          {{ rowSummary(row) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="
              row.status === 'pending'
                ? 'warning'
                : row.status === 'approved'
                  ? 'success'
                  : 'danger'
            "
          >
            {{
              row.status === 'pending' ? '待审核' : row.status === 'approved' ? '已通过' : '已拒绝'
            }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openDetail(row)">详情</el-button>
          <template v-if="row.status === 'pending'">
            <el-button size="small" type="success" :disabled="acting" @click="approve(row)">
              通过
            </el-button>
            <el-button size="small" type="danger" :disabled="acting" @click="openReject(row)">
              拒绝
            </el-button>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <div class="contrib-admin__empty">
          {{ state === 'error' ? '加载失败，请刷新重试' : '当前筛选下暂无提交' }}
        </div>
      </template>
    </el-table>

    <div class="contrib-admin__pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="data.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="load"
        @size-change="resetAndLoad"
      />
    </div>

    <!-- 详情预览 -->
    <el-dialog v-model="detailVisible" title="提交详情" width="720px">
      <template v-if="activeItem">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="提交人">{{ activeItem.username }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            {{ activeItem.type === 'new_tea' ? '补充新茶' : '科普投稿' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">{{ activeItem.status }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">
            {{ formatDate(activeItem.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="activeItem.target_tea_name" label="目标茶品">
            {{ activeItem.target_tea_name }}
          </el-descriptions-item>
          <el-descriptions-item v-if="activeItem.reject_reason" label="拒绝理由">
            {{ activeItem.reject_reason }}
          </el-descriptions-item>
        </el-descriptions>

        <h3 class="detail-title">{{ summary }}</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item
            v-for="entry in payloadEntries(activeItem)"
            :key="entry.key"
            :label="entry.key"
          >
            {{ entry.value }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <template v-if="activeItem?.status === 'pending'">
          <el-button type="danger" :disabled="acting" @click="rejectActive">拒绝</el-button>
          <el-button type="success" :disabled="acting" @click="approveActive">通过</el-button>
        </template>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 拒绝理由 -->
    <el-dialog v-model="rejectVisible" title="拒绝提交" width="480px">
      <el-form label-width="90px">
        <el-form-item label="拒绝理由">
          <el-select v-model="rejectForm.preset">
            <el-option v-for="item in REJECT_PRESETS" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="rejectForm.preset === '其他原因'" label="自定义">
          <el-input v-model="rejectForm.custom" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" :loading="acting" @click="submitReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.contrib-admin {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.contrib-admin__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}
.contrib-admin__title {
  font-size: var(--text-h2);
  color: var(--color-primary-dark);
}
.contrib-admin__filters {
  display: flex;
  gap: 12px;
}
.contrib-admin__pager {
  display: flex;
  justify-content: flex-end;
}
.contrib-admin__empty {
  padding: 24px;
  color: var(--color-text-muted);
}
.detail-title {
  margin: 20px 0 12px;
  font-size: var(--text-h3);
  color: var(--color-primary-dark);
}
</style>
