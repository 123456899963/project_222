<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import CategoryTag from '@/components/CategoryTag.vue'
import { copyShare, getShareView } from '@/api/shares'
import { getHotTeas } from '@/api/teas'
import { buildShareUrl } from '@/utils/favorite'
import { downloadSharePoster } from '@/utils/poster'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import type { CopyResult, ShareViewData, TeaListItem } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

type PageState = 'loading' | 'ready' | 'revoked' | 'notfound' | 'error'

const state = ref<PageState>('loading')
const data = ref<ShareViewData | null>(null)
const errorMessage = ref('')
const hot = ref<TeaListItem[]>([])
const copying = ref(false)
const copyResult = ref<CopyResult | null>(null)
const posterLoading = ref(false)

const items = computed(() => data.value?.items ?? [])
const createdText = computed(() => {
  if (!data.value) return ''
  const date = new Date(data.value.created_at)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
})

onMounted(() => {
  void load()
})

async function load() {
  const raw = route.params.shareId
  const token = Array.isArray(raw) ? raw[0] : raw
  if (!token) {
    state.value = 'notfound'
    return
  }

  state.value = 'loading'
  try {
    const res = await getShareView(token)
    data.value = res.data
    state.value = res.data.revoked ? 'revoked' : 'ready'
    if (res.data.revoked) void loadRecommendations()
  } catch (err) {
    const code = (err as { response?: { data?: { code?: number } } }).response?.data?.code
    if (code === 40410) {
      state.value = 'notfound'
    } else {
      state.value = 'error'
      errorMessage.value = err instanceof Error ? err.message : '分享加载失败'
    }
  }
}

async function loadRecommendations() {
  try {
    const res = await getHotTeas(3)
    hot.value = res.data ?? []
  } catch {
    hot.value = []
  }
}

function goLogin() {
  void router.push({ name: 'login', query: { redirect: route.fullPath } })
}

/** S8：纯前端 canvas 生成分享海报并下载 PNG */
async function downloadPoster() {
  if (!data.value || posterLoading.value) return
  posterLoading.value = true
  try {
    await downloadSharePoster({
      title: data.value.title,
      shareUrl: buildShareUrl(window.location.origin, data.value.token),
      teaNames: items.value.map((item) => item.name),
      teaCount: data.value.tea_count,
      createdAt: createdText.value,
    })
    toast.success('海报已生成，请查看下载')
  } catch {
    toast.error('海报生成失败，请稍后重试')
  } finally {
    posterLoading.value = false
  }
}

async function copyAll() {
  if (!data.value || copying.value) return
  if (!userStore.isLoggedIn) {
    goLogin()
    return
  }
  copying.value = true
  try {
    const res = await copyShare(data.value.token)
    copyResult.value = res.data
    if (res.data.added > 0) {
      toast.success(`已收藏 ${res.data.added} 款茶`)
    } else {
      toast.info('清单中的茶都在你的收藏里了')
    }
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    copying.value = false
  }
}
</script>

<template>
  <AppHeader />

  <main class="share-page">
    <div class="container">
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">分享清单</span>
      </nav>

      <!-- 加载 -->
      <section
        v-if="state === 'loading'"
        class="share-hero share-hero--skeleton"
        aria-hidden="true"
      >
        <div class="skeleton skeleton--title"></div>
        <div class="skeleton skeleton--line"></div>
      </section>

      <!-- 正常分享 -->
      <template v-else-if="state === 'ready' && data">
        <section class="share-hero">
          <div class="share-hero__main">
            <div class="share-hero__badges">
              <span class="badge badge--readonly">只读分享</span>
              <span v-if="data.is_owner" class="badge badge--owner">这是你的清单</span>
            </div>
            <h1 class="share-hero__title">{{ data.title }}</h1>
            <p class="share-hero__meta">
              共 {{ data.tea_count }} 款茶
              <template v-if="createdText">
                <span class="share-hero__dot">·</span>
                分享于 {{ createdText }}
              </template>
            </p>
            <p class="share-hero__desc">分享页为只读视图，不包含所有者的品鉴笔记与个人信息。</p>
          </div>

          <div class="share-hero__actions">
            <template v-if="data.is_owner">
              <RouterLink class="btn btn--primary" to="/my">管理我的清单</RouterLink>
            </template>
            <template v-else-if="userStore.isLoggedIn">
              <button type="button" class="btn btn--primary" :disabled="copying" @click="copyAll">
                {{ copying ? '收藏中…' : '一键收藏全部' }}
              </button>
            </template>
            <template v-else>
              <button type="button" class="btn btn--primary" @click="goLogin">
                登录后一键收藏
              </button>
            </template>
            <button
              type="button"
              class="btn btn--secondary"
              :disabled="posterLoading"
              @click="downloadPoster"
            >
              {{ posterLoading ? '海报生成中…' : '下载分享海报' }}
            </button>
            <RouterLink class="btn btn--secondary" to="/teas">继续逛茶</RouterLink>
          </div>
        </section>

        <div v-if="copyResult" class="copy-result">
          <p class="copy-result__text">
            本次新增收藏 <strong>{{ copyResult.added }}</strong> 款，跳过
            <strong>{{ copyResult.skipped }}</strong> 款（共 {{ copyResult.total }} 款）。
            <span v-if="copyResult.skipped > 0" class="copy-result__hint"
              >已收藏或已下架的茶会自动跳过。</span
            >
          </p>
          <RouterLink class="copy-result__link" to="/my">查看我的清单 →</RouterLink>
        </div>

        <div v-if="!items.length" class="page-state">
          <div class="page-state__icon">🍃</div>
          <h2 class="page-state__title">这份清单还是空的</h2>
          <p class="page-state__desc">所有者还没有收藏任何茶品。</p>
          <RouterLink class="btn btn--primary" to="/teas">浏览茶品列表</RouterLink>
        </div>

        <ul v-else class="share-items">
          <li
            v-for="item in items"
            :key="item.tea_id"
            class="share-item"
            :class="{ 'share-item--unavailable': !item.is_available }"
          >
            <RouterLink
              v-if="item.is_available"
              class="share-item__image-link"
              :to="{ name: 'tea-detail', params: { id: item.tea_id } }"
            >
              <img
                v-if="item.main_image_url"
                class="share-item__image"
                :src="item.main_image_url"
                :alt="item.name"
                loading="lazy"
              />
              <span
                v-else
                class="share-item__image share-item__image--placeholder"
                aria-hidden="true"
                >🫖</span
              >
            </RouterLink>
            <div v-else class="share-item__image-link">
              <img
                v-if="item.main_image_url"
                class="share-item__image"
                :src="item.main_image_url"
                :alt="item.name"
                loading="lazy"
              />
              <span
                v-else
                class="share-item__image share-item__image--placeholder"
                aria-hidden="true"
                >🫖</span
              >
              <span class="share-item__offline-badge">已下架</span>
            </div>

            <div class="share-item__body">
              <div class="share-item__title-row">
                <h3 class="share-item__name">{{ item.name }}</h3>
                <CategoryTag :category="item.category" />
              </div>
              <p class="share-item__meta">
                {{ item.origin }}
                <template v-if="item.season"> · {{ item.season }}</template>
                <template v-if="!item.is_available"> · 暂不可用</template>
              </p>
            </div>

            <span class="share-item__fav">♡ {{ item.favorite_count.toLocaleString('zh-CN') }}</span>
          </li>
        </ul>
      </template>

      <!-- 已撤销 -->
      <div v-else-if="state === 'revoked'" class="revoked">
        <div class="revoked__card">
          <div class="revoked__icon">🔒</div>
          <h1 class="revoked__title">这份分享已被撤销</h1>
          <p class="revoked__desc">
            链接已永久失效，无法恢复。你可以继续浏览其他茶品，或让分享者重新生成链接。
          </p>
          <div class="revoked__actions">
            <RouterLink class="btn btn--primary" to="/teas">浏览茶品列表</RouterLink>
            <RouterLink class="btn btn--ghost" to="/">回首页</RouterLink>
          </div>
        </div>

        <section v-if="hot.length" class="hot">
          <h2 class="hot__title">不妨看看这些茶</h2>
          <ul class="hot__grid">
            <li v-for="item in hot" :key="item.id">
              <RouterLink class="hot__card" :to="{ name: 'tea-detail', params: { id: item.id } }">
                <img
                  v-if="item.main_image_url"
                  class="hot__image"
                  :src="item.main_image_url"
                  :alt="item.name"
                  loading="lazy"
                />
                <span v-else class="hot__image hot__image--placeholder" aria-hidden="true">🫖</span>
                <div class="hot__body">
                  <h3 class="hot__name">{{ item.name }}</h3>
                  <p class="hot__origin">{{ item.origin }}</p>
                </div>
              </RouterLink>
            </li>
          </ul>
        </section>
      </div>

      <!-- 不存在 / 加载失败 -->
      <div v-else class="page-state">
        <div class="page-state__icon">🫖</div>
        <h2 class="page-state__title">
          {{ state === 'notfound' ? '分享链接不存在' : '分享加载失败' }}
        </h2>
        <p class="page-state__desc">
          {{ state === 'notfound' ? '链接可能输入有误，或分享已被撤销。' : errorMessage }}
        </p>
        <div class="page-state__actions">
          <button v-if="state === 'error'" type="button" class="btn btn--primary" @click="load">
            重新加载
          </button>
          <RouterLink class="btn btn--secondary" to="/teas">浏览茶品列表</RouterLink>
          <RouterLink class="btn btn--ghost" to="/">回首页</RouterLink>
        </div>
      </div>
    </div>
  </main>

  <AppFooter />
</template>

<style scoped>
.share-page {
  padding-top: 88px;
  padding-bottom: 48px;
  min-height: 100svh;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 32px;
}

@media (max-width: 767px) {
  .share-page {
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
.share-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.share-hero--skeleton {
  display: block;
  min-height: 150px;
}

.share-hero__badges {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.badge {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-caption);
  letter-spacing: 0.04em;
}

.badge--readonly {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.badge--owner {
  background: rgba(139, 115, 85, 0.12);
  color: var(--color-primary-dark);
}

.share-hero__title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  color: var(--color-text-primary);
  margin: 0 0 8px;
}

.share-hero__meta {
  margin: 0;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}

.share-hero__dot {
  margin: 0 6px;
  color: var(--color-border-dark);
}

.share-hero__desc {
  margin: 10px 0 0;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.share-hero__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 复制结果 */
.copy-result {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  margin-bottom: 20px;
  background: rgba(46, 125, 50, 0.08);
  border: 1px solid rgba(46, 125, 50, 0.25);
  border-radius: var(--radius-md);
}

.copy-result__text {
  margin: 0;
  font-size: var(--text-small);
  color: var(--color-text-primary);
}

.copy-result__hint {
  color: var(--color-text-muted);
}

.copy-result__link {
  font-size: var(--text-small);
  color: var(--color-primary-dark);
  white-space: nowrap;
}

/* 条目 */
.share-items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.share-item {
  display: grid;
  grid-template-columns: 120px 1fr auto;
  gap: 20px;
  align-items: center;
  padding: 16px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.share-item--unavailable {
  background: var(--color-bg-muted);
}

.share-item--unavailable .share-item__image {
  filter: grayscale(1);
  opacity: 0.55;
}

.share-item__image-link {
  position: relative;
  display: block;
  width: 120px;
  height: 90px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-bg-muted);
}

.share-item__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.share-item__image--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--color-text-muted);
}

.share-item__offline-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: rgba(44, 36, 24, 0.75);
  color: var(--color-text-inverse);
  font-size: var(--text-caption);
}

.share-item__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.share-item__name {
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.share-item__meta {
  margin: 4px 0 0;
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.share-item__fav {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  white-space: nowrap;
}

/* 撤销态 */
.revoked__card {
  text-align: center;
  padding: 56px 24px;
  background: var(--color-bg-surface);
  border: 1px dashed var(--color-border-dark);
  border-radius: var(--radius-lg);
}

.revoked__icon {
  font-size: 52px;
  margin-bottom: 12px;
  opacity: 0.7;
}

.revoked__title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  color: var(--color-text-secondary);
  margin: 0 0 8px;
}

.revoked__desc {
  max-width: 460px;
  margin: 0 auto 24px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  line-height: 1.7;
}

.revoked__actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hot {
  margin-top: 40px;
}

.hot__title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  color: var(--color-text-primary);
  margin: 0 0 16px;
}

.hot__grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.hot__card {
  display: block;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.hot__card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
}

.hot__image {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  background: var(--color-bg-muted);
}

.hot__image--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--color-text-muted);
}

.hot__body {
  padding: 12px 14px;
}

.hot__name {
  font-size: var(--text-h3);
  color: var(--color-text-primary);
  margin: 0 0 2px;
}

.hot__origin {
  margin: 0;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

/* 通用状态 */
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

.page-state__actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
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
    border-color 0.2s;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

.btn--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn--secondary {
  background: transparent;
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn--secondary:hover {
  background: var(--color-bg-muted);
}

.btn--ghost {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
}

.btn--ghost:hover {
  background: var(--color-bg-muted);
}

/* 骨架 */
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
  width: 46%;
  height: 34px;
  margin-bottom: 12px;
}

.skeleton--line {
  width: 64%;
  height: 18px;
}

@media (max-width: 767px) {
  .share-hero {
    flex-direction: column;
    align-items: flex-start;
    padding: 20px;
  }

  .share-item {
    grid-template-columns: 88px 1fr;
    gap: 14px;
  }

  .share-item__image-link {
    width: 88px;
    height: 72px;
  }

  .share-item__fav {
    grid-column: 1 / -1;
  }

  .hot__grid {
    grid-template-columns: 1fr;
  }
}
</style>
