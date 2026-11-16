<script setup lang="ts">
/**
 * 我的提交记录（S13）：追踪贡献审核状态，查看拒绝理由，删除待审核提交
 */
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import { deleteContribution, getMyContributions } from '@/api/contributions'
import { useToastStore } from '@/stores/toast'
import {
  buildReadMap,
  diffUnread,
  loadReadMap,
  saveReadMap,
  type ContributionReadMap,
} from '@/utils/contributionRead'
import type { ContributionItem, ContributionStatus } from '@/types'

const toast = useToastStore()
const state = ref<'loading' | 'ready' | 'error'>('loading')
const items = ref<ContributionItem[]>([])
const deletingId = ref<number | null>(null)
const readMap = ref<ContributionReadMap>(loadReadMap())

const STATUS_META: Record<ContributionStatus, { label: string; tone: string }> = {
  pending: { label: '待审核', tone: 'warning' },
  approved: { label: '已通过', tone: 'success' },
  rejected: { label: '已拒绝', tone: 'danger' },
}

const pendingCount = computed(() => items.value.filter((item) => item.status === 'pending').length)
const approvedCount = computed(
  () => items.value.filter((item) => item.status === 'approved').length,
)
const rejectedCount = computed(
  () => items.value.filter((item) => item.status === 'rejected').length,
)
const unreadItems = computed(() => diffUnread(items.value, readMap.value))
const unreadIds = computed(() => new Set(unreadItems.value.map((item) => item.id)))

function markAllRead() {
  const next = buildReadMap(items.value)
  saveReadMap(next)
  readMap.value = next
}

function typeLabel(type: ContributionItem['type']) {
  return type === 'new_tea' ? '补充新茶' : '科普投稿'
}

function summary(item: ContributionItem): string {
  if (item.type === 'new_tea') {
    const name = item.payload?.name
    return typeof name === 'string' ? name : '未命名茶品'
  }
  const title = item.payload?.title
  return (typeof title === 'string' && title.trim()) || item.target_tea_name || '科普投稿'
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

async function load() {
  state.value = 'loading'
  try {
    const res = await getMyContributions()
    items.value = res.data ?? []
    state.value = 'ready'
  } catch {
    state.value = 'error'
  }
}

async function remove(item: ContributionItem) {
  if (!window.confirm(`确定删除「${summary(item)}」这条待审核提交吗？`)) return
  deletingId.value = item.id
  try {
    await deleteContribution(item.id)
    toast.success('提交已删除')
    items.value = items.value.filter((row) => row.id !== item.id)
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <AppHeader />

  <main class="my-contrib-page">
    <div class="container">
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <RouterLink to="/my">我的清单</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">我的提交</span>
      </nav>

      <header class="page-head">
        <div>
          <p class="page-kicker">My Contributions</p>
          <h1 class="page-head__title">我的提交</h1>
          <p class="page-head__desc">共 {{ items.length }} 条记录</p>
        </div>
        <RouterLink class="btn btn--primary" :to="{ name: 'contribute' }">＋ 新建投稿</RouterLink>
      </header>

      <div v-if="state === 'ready'" class="contrib-stats" aria-label="投稿审核统计">
        <div class="contrib-stat">
          <span class="contrib-stat__label">待审核</span>
          <strong class="contrib-stat__value">{{ pendingCount }}</strong>
        </div>
        <div class="contrib-stat contrib-stat--success">
          <span class="contrib-stat__label">已通过</span>
          <strong class="contrib-stat__value">{{ approvedCount }}</strong>
        </div>
        <div class="contrib-stat contrib-stat--danger">
          <span class="contrib-stat__label">未通过</span>
          <strong class="contrib-stat__value">{{ rejectedCount }}</strong>
        </div>
      </div>

      <div v-if="unreadItems.length" class="read-notice" role="status">
        <span class="read-notice__text">有 {{ unreadItems.length }} 条投稿有新结果</span>
        <button type="button" class="read-notice__action" @click="markAllRead">标记已读</button>
      </div>

      <div v-if="state === 'loading'" class="page-state">
        <p class="page-state__desc">加载中…</p>
      </div>

      <div v-else-if="state === 'error'" class="page-state">
        <h2 class="page-state__title">加载失败</h2>
        <button type="button" class="btn btn--primary" @click="load">重新加载</button>
      </div>

      <div v-else-if="items.length === 0" class="page-state">
        <div class="page-state__icon">📝</div>
        <h2 class="page-state__title">还没有提交记录</h2>
        <p class="page-state__desc">补充一款尚未收录的茶，或为已有茶品撰写科普。</p>
        <RouterLink class="btn btn--primary" :to="{ name: 'contribute' }">去投稿</RouterLink>
      </div>

      <ul v-else class="contrib-list">
        <li v-for="item in items" :key="item.id" class="contrib-card">
          <div class="contrib-card__head">
            <div class="contrib-card__title">
              <span class="contrib-card__type">{{ typeLabel(item.type) }}</span>
              <strong class="contrib-card__name">{{ summary(item) }}</strong>
            </div>
            <div class="contrib-card__tags">
              <span v-if="unreadIds.has(item.id)" class="contrib-card__new">新结果</span>
              <span class="status-tag" :class="`status-tag--${STATUS_META[item.status].tone}`">
                {{ STATUS_META[item.status].label }}
              </span>
            </div>
          </div>

          <p class="contrib-card__meta">
            提交于 {{ formatDate(item.created_at) }}
            <template v-if="item.target_tea_name">
              · 目标茶品：{{ item.target_tea_name }}
            </template>
          </p>

          <p v-if="item.status === 'rejected' && item.reject_reason" class="contrib-card__reason">
            拒绝理由：{{ item.reject_reason }}
          </p>
          <p v-else-if="item.status === 'approved'" class="contrib-card__approved">
            审核已通过，内容已公开展示。
          </p>

          <div class="contrib-card__actions">
            <button
              v-if="item.status === 'pending'"
              type="button"
              class="btn btn--danger-text"
              :disabled="deletingId === item.id"
              @click="remove(item)"
            >
              {{ deletingId === item.id ? '删除中…' : '删除提交' }}
            </button>
            <RouterLink
              v-if="item.type === 'article' && item.target_tea_id"
              class="btn btn--ghost"
              :to="{ name: 'tea-detail', params: { id: item.target_tea_id } }"
            >
              查看茶品
            </RouterLink>
          </div>
        </li>
      </ul>
    </div>
  </main>

  <AppFooter />
</template>

<style scoped>
.my-contrib-page {
  padding: 88px 0 64px;
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
  .my-contrib-page {
    padding: 76px 0 48px;
  }
  .container {
    padding: 0 16px;
  }
}
.page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}
.page-head__title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  font-weight: 600;
  color: var(--color-primary-dark);
  margin: 0;
}
.page-head__desc {
  margin-top: 6px;
  color: var(--color-text-secondary);
}
.contrib-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.contrib-stat {
  display: flex;
  flex: 1 1 120px;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}
.contrib-stat__label {
  font-size: var(--text-caption);
  color: var(--color-text-secondary);
}
.contrib-stat__value {
  font-size: var(--text-h2);
  color: var(--color-text-primary);
}
.contrib-stat--success .contrib-stat__value {
  color: var(--color-success);
}
.contrib-stat--danger .contrib-stat__value {
  color: var(--color-error);
}
.read-notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 16px;
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
}
.read-notice__text {
  font-size: var(--text-small);
  color: var(--color-text-primary);
}
.read-notice__action {
  padding: 4px 12px;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-full);
  background: var(--color-bg-surface);
  color: var(--color-primary);
  font-size: var(--text-caption);
  cursor: pointer;
}
.read-notice__action:hover {
  border-color: var(--color-primary);
}
.contrib-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.contrib-card {
  padding: 20px 24px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}
.contrib-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.contrib-card__title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.contrib-card__tags {
  display: flex;
  align-items: center;
  gap: 8px;
}
.contrib-card__new {
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  color: var(--color-primary);
  font-size: var(--text-caption);
}
.contrib-card__type {
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-size: var(--text-caption);
}
.contrib-card__name {
  font-size: var(--text-body);
  color: var(--color-text-primary);
}
.contrib-card__meta {
  margin-top: 8px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
}
.contrib-card__reason {
  margin-top: 12px;
  padding: 10px 14px;
  border-left: 3px solid var(--color-error);
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
  color: var(--color-error);
  font-size: var(--text-small);
}
.contrib-card__approved {
  margin-top: 12px;
  color: var(--color-success);
  font-size: var(--text-small);
}
.contrib-card__actions {
  display: flex;
  gap: 12px;
  margin-top: 14px;
}
.status-tag {
  padding: 2px 12px;
  border-radius: var(--radius-full);
  font-size: var(--text-caption);
}
.status-tag--warning {
  background: var(--color-bg-muted);
  color: var(--color-warning);
}
.status-tag--success {
  background: var(--color-bg-muted);
  color: var(--color-success);
}
.status-tag--danger {
  background: var(--color-bg-muted);
  color: var(--color-error);
}
</style>
