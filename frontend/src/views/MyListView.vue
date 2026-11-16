<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import CategoryTag from '@/components/CategoryTag.vue'
import NoteEditor from '@/components/NoteEditor.vue'
import SharePanel from '@/components/SharePanel.vue'
import { createList, deleteList, getListDetail, getMyLists, updateListTitle } from '@/api/lists'
import { getMyStats } from '@/api/me'
import { removeFavorite } from '@/api/favorites'
import { isValidListTitle } from '@/utils/list'
import { CATEGORY_LABELS } from '@/utils/teaQuery'
import { buildExportFilename, downloadTextFile, toCsv } from '@/utils/export'
import { useToastStore } from '@/stores/toast'
import type { ListData, ListItem, ListShareBrief, ListSummary, UserStats } from '@/types'

const MAX_LISTS = 10

const CSV_COLUMNS = [
  { key: 'name', label: '茶名' },
  { key: 'category', label: '茶类' },
  { key: 'origin', label: '产地' },
  { key: 'season', label: '季节' },
  { key: 'favorited_at', label: '收藏时间' },
]

const route = useRoute()
const toast = useToastStore()

type PageState = 'loading' | 'ready' | 'error'

const state = ref<PageState>('loading')
const lists = ref<ListSummary[]>([])
const list = ref<ListData | null>(null)
const activeListId = ref<number | null>(null)
const stats = ref<UserStats | null>(null)
const errorMessage = ref('')
const detailLoading = ref(false)

const editingTitle = ref(false)
const titleDraft = ref('')
const savingTitle = ref(false)

const creating = ref(false)
const newTitle = ref('')
const creatingPending = ref(false)
const deleting = ref(false)

const noteOpen = ref(false)
const noteTarget = ref<ListItem | null>(null)
const shareOpen = ref(false)
const removingId = ref<number | null>(null)
const exportPanel = ref<HTMLDetailsElement | null>(null)

const items = computed(() => list.value?.items ?? [])
const noteCount = computed(() => items.value.filter((item) => !!item.tasting_note).length)
const unavailableCount = computed(() => items.value.filter((item) => !item.is_available).length)
const isDefaultList = computed(() => !!list.value?.is_default)
const canCreate = computed(() => lists.value.length < MAX_LISTS)

onMounted(() => {
  void load()
})

async function load() {
  state.value = 'loading'
  errorMessage.value = ''
  try {
    // 等级统计失败不阻断清单展示（统计仅为展示增强）
    const [listsRes, statsRes] = await Promise.all([getMyLists(), getMyStats().catch(() => null)])
    lists.value = listsRes.data
    stats.value = statsRes?.data ?? null

    const requested = Number(route.query.list)
    const initial =
      lists.value.find((item) => item.id === requested)?.id ?? lists.value[0]?.id ?? null
    await loadDetail(initial)
    state.value = 'ready'
    await applyQueryActions()
  } catch (err) {
    state.value = 'error'
    errorMessage.value = err instanceof Error ? err.message : '清单加载失败'
  }
}

async function loadDetail(listId: number | null) {
  if (listId === null) {
    list.value = null
    activeListId.value = null
    return
  }
  detailLoading.value = true
  try {
    const res = await getListDetail(listId)
    list.value = res.data
    activeListId.value = res.data.id
  } finally {
    detailLoading.value = false
  }
}

async function selectList(listId: number) {
  if (listId === activeListId.value || detailLoading.value) return
  editingTitle.value = false
  creating.value = false
  try {
    await loadDetail(listId)
  } catch {
    // 统一错误提示由请求拦截器处理
  }
}

async function refreshSummaries() {
  const res = await getMyLists()
  lists.value = res.data
}

async function applyQueryActions() {
  const noteRaw = route.query.note
  const noteId = Number(Array.isArray(noteRaw) ? noteRaw[0] : noteRaw)
  if (Number.isFinite(noteId) && noteId > 0) {
    let target = items.value.find((item) => item.tea_id === noteId)
    if (!target) {
      // 茶品可能位于其它清单：逐个小清单查找（最多 10 个）
      for (const summary of lists.value) {
        if (summary.id === activeListId.value) continue
        try {
          const res = await getListDetail(summary.id)
          const found = res.data.items.find((item) => item.tea_id === noteId)
          if (found) {
            list.value = res.data
            activeListId.value = res.data.id
            target = found
            break
          }
        } catch {
          // 忽略单个清单加载失败
        }
      }
    }
    if (target) openNote(target)
  }
  if (route.query.share === '1') shareOpen.value = true
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

/** 导出用行数据：列字段取自页面已有接口数据 */
function exportRows() {
  return items.value.map((item) => ({
    tea_id: item.tea_id,
    name: item.name,
    category: CATEGORY_LABELS[item.category],
    origin: item.origin,
    season: item.season ?? '',
    favorited_at: formatDate(item.favorited_at),
  }))
}

function closeExportMenu() {
  if (exportPanel.value) exportPanel.value.open = false
}

function exportCsv() {
  if (!list.value || !items.value.length) return
  const csv = toCsv(exportRows(), CSV_COLUMNS)
  downloadTextFile(buildExportFilename(list.value.title, 'csv'), csv, 'text/csv;charset=utf-8')
  closeExportMenu()
  toast.success('CSV 已导出')
}

function exportJson() {
  if (!list.value || !items.value.length) return
  const payload = {
    list: { name: list.value.title, description: null },
    items: items.value.map((item) => ({
      tea_id: item.tea_id,
      name: item.name,
      category: CATEGORY_LABELS[item.category],
      origin: item.origin,
      season: item.season ?? null,
      favorited_at: item.favorited_at,
      tasting_note: item.tasting_note ?? null,
      is_available: item.is_available,
    })),
  }
  downloadTextFile(
    buildExportFilename(list.value.title, 'json'),
    JSON.stringify(payload, null, 2),
    'application/json;charset=utf-8',
  )
  closeExportMenu()
  toast.success('JSON 已导出')
}

function startEditTitle() {
  if (!list.value) return
  titleDraft.value = list.value.title
  editingTitle.value = true
}

function cancelEditTitle() {
  editingTitle.value = false
  titleDraft.value = ''
}

async function saveTitle() {
  if (!list.value || savingTitle.value) return
  const normalized = titleDraft.value.trim()
  if (!isValidListTitle(normalized)) {
    toast.warn('清单标题需为 2–20 个字符')
    return
  }
  savingTitle.value = true
  try {
    const res = await updateListTitle(list.value.id, normalized)
    list.value.title = res.data.title
    list.value.updated_at = res.data.updated_at
    const summary = lists.value.find((item) => item.id === list.value?.id)
    if (summary) summary.title = res.data.title
    editingTitle.value = false
    toast.success('清单标题已更新')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    savingTitle.value = false
  }
}

async function submitCreate() {
  const normalized = newTitle.value.trim()
  if (!isValidListTitle(normalized)) {
    toast.warn('清单标题需为 2–20 个字符')
    return
  }
  if (!canCreate.value || creatingPending.value) return
  creatingPending.value = true
  try {
    const res = await createList(normalized)
    newTitle.value = ''
    creating.value = false
    await refreshSummaries()
    await loadDetail(res.data.id)
    toast.success('清单已创建')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    creatingPending.value = false
  }
}

async function removeCurrentList() {
  if (!list.value || isDefaultList.value || deleting.value) return
  const confirmed = window.confirm(
    `确定删除“${list.value.title}”吗？清单中的茶品会迁移到“我的收藏”，笔记不会丢失。`,
  )
  if (!confirmed) return

  deleting.value = true
  try {
    await deleteList(list.value.id)
    await refreshSummaries()
    await loadDetail(lists.value[0]?.id ?? null)
    toast.success('清单已删除，条目已迁移到我的收藏')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    deleting.value = false
  }
}

function openNote(item: ListItem) {
  noteTarget.value = item
  noteOpen.value = true
}

function onNoteSaved(note: string | null) {
  const target = noteTarget.value
  if (!target || !list.value) return
  const item = list.value.items.find((row) => row.tea_id === target.tea_id)
  if (item) item.tasting_note = note
}

async function removeItem(item: ListItem) {
  if (!list.value || removingId.value !== null) return
  const confirmed = window.confirm(`确定将“${item.name}”移出“${list.value.title}”吗？`)
  if (!confirmed) return

  const listId = list.value.id
  removingId.value = item.tea_id
  try {
    await removeFavorite(item.tea_id, listId)
    if (list.value) {
      list.value.items = list.value.items.filter((row) => row.tea_id !== item.tea_id)
      list.value.tea_count = list.value.items.length
    }
    const summary = lists.value.find((row) => row.id === listId)
    if (summary) summary.tea_count = Math.max(0, summary.tea_count - 1)
    if (noteTarget.value?.tea_id === item.tea_id) {
      noteOpen.value = false
      noteTarget.value = null
    }
    toast.success('已移出当前清单')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    removingId.value = null
  }
}

function onShareUpdate(share: ListShareBrief | null) {
  if (!list.value) return
  list.value.share = share
  const summary = lists.value.find((item) => item.id === list.value?.id)
  if (summary) summary.share = share
}
</script>

<template>
  <AppHeader />

  <main class="my-page">
    <div class="container">
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">我的清单</span>
      </nav>

      <!-- 头部 -->
      <section v-if="state === 'loading'" class="list-hero list-hero--skeleton" aria-hidden="true">
        <div class="skeleton skeleton--title"></div>
        <div class="skeleton skeleton--line"></div>
      </section>

      <section v-else-if="state === 'ready' && list" class="list-hero">
        <div class="list-hero__main">
          <p class="list-hero__eyebrow">
            我的清单<span v-if="isDefaultList" class="list-hero__default-tag">默认</span>
          </p>

          <div v-if="!editingTitle" class="list-hero__title-row">
            <h1 class="list-hero__title">{{ list.title }}</h1>
            <button type="button" class="icon-btn" title="编辑标题" @click="startEditTitle">
              ✏️
            </button>
          </div>

          <form v-else class="title-form" @submit.prevent="saveTitle">
            <input
              v-model="titleDraft"
              class="title-form__input"
              maxlength="20"
              aria-label="清单标题"
              placeholder="2–20 个字符"
            />
            <button type="submit" class="btn btn--primary" :disabled="savingTitle">
              {{ savingTitle ? '保存中…' : '保存' }}
            </button>
            <button type="button" class="btn btn--ghost" @click="cancelEditTitle">取消</button>
          </form>

          <p class="list-hero__stats">
            共 {{ list.tea_count }} 款茶
            <span class="list-hero__dot">·</span>
            {{ noteCount }} 条私密笔记
            <template v-if="unavailableCount">
              <span class="list-hero__dot">·</span>
              {{ unavailableCount }} 款已下架
            </template>
          </p>

          <!-- 等级徽章（S15）：按收藏数实时计算 -->
          <div v-if="stats" class="level" :data-level="stats.level.index">
            <span class="level__badge">🏅 {{ stats.level.name }}</span>
            <span class="level__hint">
              <template v-if="stats.level.next_name">
                再收藏 {{ stats.level.remaining }} 款，升为{{ stats.level.next_name }}
              </template>
              <template v-else>已达最高等级</template>
            </span>
          </div>
        </div>

        <div class="list-hero__actions">
          <button type="button" class="btn btn--primary" @click="shareOpen = true">
            ↗️ 分享清单
          </button>
          <details v-if="items.length" ref="exportPanel" class="export">
            <summary class="export__toggle">⬇️ 导出</summary>
            <div class="export__menu">
              <button type="button" class="export__item" @click="exportCsv">导出 CSV</button>
              <button type="button" class="export__item" @click="exportJson">导出 JSON</button>
            </div>
          </details>
          <RouterLink class="btn btn--secondary" :to="{ name: 'contribute' }">
            ✍️ 投稿新茶 / 科普
          </RouterLink>
          <RouterLink class="btn btn--ghost" :to="{ name: 'my-contributions' }">
            我的提交
          </RouterLink>
          <button
            v-if="!isDefaultList"
            type="button"
            class="btn btn--danger-text"
            :disabled="deleting"
            @click="removeCurrentList"
          >
            {{ deleting ? '删除中…' : '删除清单' }}
          </button>
          <RouterLink class="btn btn--secondary" to="/teas">去发现好茶</RouterLink>
        </div>
      </section>

      <!-- 错误 -->
      <div v-else-if="state === 'error'" class="page-state">
        <div class="page-state__icon">🫖</div>
        <h2 class="page-state__title">清单加载失败</h2>
        <p class="page-state__desc">{{ errorMessage || '请稍后重试' }}</p>
        <button type="button" class="btn btn--primary" @click="load">重新加载</button>
      </div>

      <!-- 侧栏 + 条目区 -->
      <div v-if="state === 'ready'" class="list-layout">
        <aside class="list-side" aria-label="我的清单列表">
          <div class="list-side__header">
            <span>全部清单</span>
            <span class="list-side__count">{{ lists.length }}/{{ MAX_LISTS }}</span>
          </div>

          <ul class="side-lists">
            <li v-for="summary in lists" :key="summary.id">
              <button
                type="button"
                class="side-lists__item"
                :class="{ 'side-lists__item--active': summary.id === activeListId }"
                @click="selectList(summary.id)"
              >
                <span class="side-lists__title">{{ summary.title }}</span>
                <span class="side-lists__num">{{ summary.tea_count }}</span>
              </button>
            </li>
          </ul>

          <form v-if="creating" class="side-create" @submit.prevent="submitCreate">
            <input
              v-model="newTitle"
              class="side-create__input"
              maxlength="20"
              placeholder="清单名称（2–20 字）"
              aria-label="新清单名称"
            />
            <div class="side-create__actions">
              <button type="submit" class="btn btn--tiny" :disabled="creatingPending">
                {{ creatingPending ? '创建中…' : '创建' }}
              </button>
              <button type="button" class="btn btn--tiny btn--ghost" @click="creating = false">
                取消
              </button>
            </div>
          </form>
          <button
            v-else
            type="button"
            class="btn btn--tiny side-create-btn"
            :disabled="!canCreate"
            @click="creating = true"
          >
            ＋ 新建清单
          </button>
          <p v-if="!canCreate" class="side-hint">每个账号最多 10 个清单</p>
        </aside>

        <section class="list-main" :aria-busy="detailLoading">
          <!-- 空状态 -->
          <div v-if="!items.length" class="page-state">
            <div class="page-state__icon">🍃</div>
            <h2 class="page-state__title">清单还是空的</h2>
            <p class="page-state__desc">去茶品列表逛逛，收藏喜欢的茶，开启你的品鉴记录。</p>
            <RouterLink class="btn btn--primary" to="/teas">浏览茶品列表</RouterLink>
          </div>

          <!-- 条目 -->
          <ul v-else class="list-items">
            <li
              v-for="item in items"
              :key="item.tea_id"
              class="list-item"
              :class="{ 'list-item--unavailable': !item.is_available }"
            >
              <RouterLink
                v-if="item.is_available"
                class="list-item__image-link"
                :to="{ name: 'tea-detail', params: { id: item.tea_id } }"
              >
                <img
                  v-if="item.main_image_url"
                  class="list-item__image"
                  :src="item.main_image_url"
                  :alt="item.name"
                  loading="lazy"
                />
                <span
                  v-else
                  class="list-item__image list-item__image--placeholder"
                  aria-hidden="true"
                  >🫖</span
                >
              </RouterLink>
              <div v-else class="list-item__image-link">
                <img
                  v-if="item.main_image_url"
                  class="list-item__image"
                  :src="item.main_image_url"
                  :alt="item.name"
                  loading="lazy"
                />
                <span
                  v-else
                  class="list-item__image list-item__image--placeholder"
                  aria-hidden="true"
                  >🫖</span
                >
                <span class="list-item__offline-badge">已下架</span>
              </div>

              <div class="list-item__body">
                <div class="list-item__title-row">
                  <h3 class="list-item__name">{{ item.name }}</h3>
                  <CategoryTag :category="item.category" />
                </div>
                <p class="list-item__meta">
                  {{ item.origin }}
                  <template v-if="item.season"> · {{ item.season }}</template>
                  <template v-if="!item.is_available"> · 暂不可用</template>
                </p>

                <p v-if="item.tasting_note" class="list-item__note">
                  <span class="list-item__note-label">私密笔记</span>
                  {{ item.tasting_note }}
                </p>
                <p v-else class="list-item__note list-item__note--empty">还没有品鉴笔记</p>
              </div>

              <div class="list-item__side">
                <span class="list-item__date">收藏于 {{ formatDate(item.favorited_at) }}</span>
                <div class="list-item__actions">
                  <button type="button" class="btn btn--tiny" @click="openNote(item)">
                    {{ item.tasting_note ? '编辑笔记' : '写笔记' }}
                  </button>
                  <button
                    type="button"
                    class="btn btn--tiny btn--danger-text"
                    :disabled="removingId === item.tea_id"
                    @click="removeItem(item)"
                  >
                    {{ removingId === item.tea_id ? '移除中…' : '移除' }}
                  </button>
                </div>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </main>

  <AppFooter />

  <NoteEditor
    v-model="noteOpen"
    :list-id="activeListId ?? 0"
    :tea-id="noteTarget?.tea_id ?? 0"
    :tea-name="noteTarget?.name ?? ''"
    :initial-note="noteTarget?.tasting_note ?? null"
    @saved="onNoteSaved"
  />

  <SharePanel
    v-model="shareOpen"
    :share="list?.share ?? null"
    :list-id="activeListId"
    :title="list?.title ?? '我的茶单'"
    :tea-names="items.map((item) => item.name)"
    :tea-count="list?.tea_count ?? 0"
    :created-at="list ? formatDate(list.created_at) : ''"
    @update:share="onShareUpdate"
  />
</template>

<style scoped>
.my-page {
  padding-top: 88px;
  padding-bottom: 48px;
  min-height: 100svh;
}

.container {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 32px;
}

@media (max-width: 767px) {
  .my-page {
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
  padding: 8px 0 20px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.breadcrumb__sep {
  color: var(--color-border-dark);
}

.breadcrumb__current {
  color: var(--color-text-primary);
}

/* 头部 */
.list-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 28px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
}

.list-hero--skeleton {
  display: block;
  min-height: 140px;
}

.list-hero__eyebrow {
  margin: 0 0 6px;
  font-size: var(--text-caption);
  letter-spacing: 0.18em;
  color: var(--color-text-muted);
}

.list-hero__default-tag {
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  color: var(--color-primary-dark);
  letter-spacing: 0;
}

.list-hero__title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 等级徽章（S15） */
.level {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.level__badge {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 12px;
  border-radius: var(--radius-full);
  background: rgba(139, 115, 85, 0.12);
  color: var(--color-primary-dark);
  font-size: var(--text-caption);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.level__hint {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.list-hero__title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  color: var(--color-text-primary);
  margin: 0;
}

.list-hero__stats {
  margin: 10px 0 0;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}

.list-hero__dot {
  margin: 0 6px;
  color: var(--color-border-dark);
}

.list-hero__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 导出下拉（原生 details，不依赖 Element Plus） */
.export {
  position: relative;
}

.export__toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 42px;
  padding: 0 20px;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-small);
  font-weight: 500;
  white-space: nowrap;
  list-style: none;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
}

.export__toggle::-webkit-details-marker {
  display: none;
}

.export__toggle:hover,
.export[open] .export__toggle {
  background: var(--color-bg-muted);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.export__menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 20;
  min-width: 132px;
  padding: 6px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.export__item {
  display: block;
  width: 100%;
  padding: 9px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: var(--text-small);
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
}

.export__item:hover {
  background: var(--color-bg-muted);
  color: var(--color-primary-dark);
}

.icon-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background: transparent;
  cursor: pointer;
  font-size: 13px;
}

.icon-btn:hover {
  background: var(--color-bg-muted);
}

.title-form {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.title-form__input {
  height: 42px;
  min-width: 240px;
  padding: 0 14px;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  font-family: inherit;
  font-size: var(--text-body);
}

.title-form__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* 侧栏 + 条目区 */
.list-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 20px;
  align-items: start;
}

.list-side {
  position: sticky;
  top: 84px;
  padding: 16px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.list-side__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.list-side__count {
  font-weight: 400;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.side-lists {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.side-lists__item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: var(--text-small);
  text-align: left;
  cursor: pointer;
}

.side-lists__item:hover {
  background: var(--color-bg-muted);
}

.side-lists__item--active {
  background: var(--color-bg-muted);
  border-color: var(--color-border-dark);
  color: var(--color-primary-dark);
  font-weight: 600;
}

.side-lists__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-lists__num {
  flex-shrink: 0;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.side-create {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.side-create__input {
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  font-family: inherit;
  font-size: var(--text-small);
}

.side-create__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.side-create__actions {
  display: flex;
  gap: 8px;
}

.side-create-btn {
  width: 100%;
}

.side-hint {
  margin: 8px 0 0;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.list-main {
  min-width: 0;
}

/* 状态 */
.page-state {
  text-align: center;
  padding: 72px 24px;
  background: var(--color-bg-surface);
  border: 1px dashed var(--color-border-dark);
  border-radius: var(--radius-lg);
}

.page-state__icon {
  font-size: 56px;
  opacity: 0.6;
  margin-bottom: 12px;
}

.page-state__title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  color: var(--color-text-secondary);
  margin: 0 0 8px;
}

.page-state__desc {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin: 0 0 24px;
}

/* 条目 */
.list-items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-item {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 20px;
  padding: 16px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.list-item:hover {
  border-color: var(--color-border-dark);
  box-shadow: var(--shadow-card);
}

.list-item--unavailable {
  background: var(--color-bg-muted);
}

.list-item--unavailable .list-item__image {
  filter: grayscale(1);
  opacity: 0.55;
}

.list-item--unavailable .list-item__name {
  color: var(--color-text-muted);
}

.list-item__image-link {
  position: relative;
  display: block;
  width: 120px;
  height: 90px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-bg-muted);
}

.list-item__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.list-item__image--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--color-text-muted);
}

.list-item__offline-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: rgba(44, 36, 24, 0.75);
  color: var(--color-text-inverse);
  font-size: var(--text-caption);
}

.list-item__body {
  min-width: 0;
}

.list-item__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.list-item__name {
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.list-item__meta {
  margin: 4px 0 10px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.list-item__note {
  margin: 0;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.list-item__note--empty {
  color: var(--color-text-muted);
  font-style: italic;
}

.list-item__note-label {
  display: inline-block;
  margin-right: 8px;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  color: var(--color-primary-dark);
  font-size: var(--text-caption);
  font-style: normal;
}

.list-item__side {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 4px;
  border-top: 1px dashed var(--color-border);
}

.list-item__date {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.list-item__actions {
  display: flex;
  gap: 8px;
}

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 42px;
  padding: 0 20px;
  border-radius: var(--radius-full);
  font-size: var(--text-small);
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.btn--secondary {
  background: transparent;
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn--secondary:hover:not(:disabled) {
  background: var(--color-bg-muted);
}

.btn--ghost {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
}

.btn--ghost:hover:not(:disabled) {
  background: var(--color-bg-muted);
}

.btn--tiny {
  height: 32px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  border-color: var(--color-border-dark);
  background: transparent;
  color: var(--color-text-secondary);
}

.btn--tiny:hover:not(:disabled) {
  background: var(--color-bg-muted);
}

.btn--danger-text {
  color: var(--color-error);
  border-color: var(--color-error);
}

/* 骨架屏 */
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
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.skeleton--title {
  width: 42%;
  height: 34px;
  margin-bottom: 12px;
}

.skeleton--line {
  width: 60%;
  height: 18px;
}

@media (max-width: 900px) {
  .list-layout {
    grid-template-columns: 1fr;
  }

  .list-side {
    position: static;
  }

  .side-lists {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .side-lists__item {
    width: auto;
  }
}

@media (max-width: 767px) {
  .list-hero {
    flex-direction: column;
    align-items: flex-start;
    padding: 20px;
  }

  .list-item {
    grid-template-columns: 88px 1fr;
    gap: 14px;
  }

  .list-item__image-link {
    width: 88px;
    height: 72px;
  }
}
</style>
