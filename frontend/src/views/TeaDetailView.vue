<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import CategoryTag from '@/components/CategoryTag.vue'
import TeaCard from '@/components/TeaCard.vue'
import FavoriteButton from '@/components/FavoriteButton.vue'
import CountUp from '@/components/effects/CountUp.vue'
import RevealText from '@/components/effects/RevealText.vue'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import { getHotTeas, getRelatedTeas, getTeaDetail } from '@/api/teas'
import { getFavoriteStatus } from '@/api/favorites'
import { clearPendingAction, loadPendingAction, savePendingAction } from '@/utils/pendingAction'
import { addHistory } from '@/utils/viewHistory'
import { buildTaobaoSearchUrl } from '@/utils/purchase'
import type { Tea, TeaListItem } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

type PageState = 'loading' | 'ready' | 'offline' | 'notfound' | 'error'

const state = ref<PageState>('loading')
const tea = ref<Tea | null>(null)
const related = ref<TeaListItem[]>([])
const fallbackHot = ref<TeaListItem[]>([])
const errorMessage = ref('')
const imageFailed = ref(false)
const videoFailed = ref(false)
const activeImage = ref<string | null>(null)
const favoriteCount = ref(0)

/** 图片集（S4）：主图优先 + 去重；无图集时仅主图 */
const galleryImages = computed(() => {
  const item = tea.value
  if (!item) return []
  const main = item.main_image_url ? [item.main_image_url] : []
  const set = (item.image_set ?? []).filter((url) => !!url)
  return Array.from(new Set([...main, ...set]))
})

const displayImage = computed(() => activeImage.value ?? tea.value?.main_image_url ?? null)
const hasImage = computed(() => !!displayImage.value && !imageFailed.value)

/** 视频（S5）：无 video_url 或加载失败时整块隐藏，不留空播放器 */
const hasVideo = computed(() => !!tea.value?.video_url && !videoFailed.value)
const videoDurationText = computed(() => {
  const seconds = tea.value?.video_duration
  if (!seconds || seconds <= 0) return ''
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}:${String(rest).padStart(2, '0')}`
})

const tips = computed(() => {
  const item = tea.value
  if (!item) return []
  return [
    { icon: '📜', title: '历史文化', text: item.tips_history },
    { icon: '👥', title: '适合人群', text: item.tips_suitable },
    { icon: '⚠️', title: '常见误区', text: item.tips_misconception },
    { icon: '✨', title: '官方备注', text: item.tips_official_note },
  ].filter((tip) => !!tip.text && tip.text.trim())
})

/** 茶友科普投稿（S11 / S12）：仅审核通过项，空则隐藏 */
const contributedArticles = computed(() => tea.value?.contributed_articles ?? [])

function formatArticleDate(value: string): string {
  return new Date(value).toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

const brewItems = computed(() => {
  const item = tea.value
  if (!item) return []
  return [
    { icon: '🌡️', label: '水温', value: item.water_temp != null ? `${item.water_temp}℃` : '—' },
    { icon: '🫖', label: '投茶量', value: item.tea_amount != null ? `${item.tea_amount}g` : '—' },
    { icon: '⏱️', label: '浸泡时间', value: item.brew_time != null ? `${item.brew_time}秒` : '—' },
  ]
})

const hasBrew = computed(
  () =>
    tea.value != null &&
    (tea.value.water_temp != null || tea.value.tea_amount != null || tea.value.brew_time != null),
)

/** 分步冲泡教程（ADR-0005）：逐茶维护，null 时退回三格速查卡；默认只露速查条，步骤全部收起 */
const brewingGuide = computed(() => tea.value?.brewing_guide ?? null)
const guideExpanded = ref(false)
const canExpandGuide = computed(() => (brewingGuide.value?.steps.length ?? 0) > 0)

/** 折叠动画时长，需与 .brew-card__collapse 的 transition 时长一致 */
const GUIDE_ANIM_MS = 320

/** 展开前的滚动位置：收起时同步折叠与回位动画，做到「像没动过一样」 */
let scrollBeforeExpand = 0
let guideAnimating = false
let guideRafId = 0

function easeInOutCubic(progress: number) {
  return progress < 0.5 ? 4 * progress ** 3 : 1 - (-2 * progress + 2) ** 3 / 2
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function stopGuideAnimation() {
  if (guideRafId) {
    cancelAnimationFrame(guideRafId)
    guideRafId = 0
  }
  guideAnimating = false
}

function toggleGuide() {
  if (guideAnimating) return

  if (!guideExpanded.value) {
    scrollBeforeExpand = window.scrollY
    guideExpanded.value = true
    return
  }

  const from = window.scrollY
  const to = scrollBeforeExpand
  guideExpanded.value = false
  if (from === to || prefersReducedMotion()) return

  // 折叠高度与滚动回位用同一时长、同一缓动逐帧推进，避免「内容瞬间塌掉 + 长距离滚动」的割裂
  guideAnimating = true
  const startedAt = performance.now()

  const step = (now: number) => {
    const progress = Math.min((now - startedAt) / GUIDE_ANIM_MS, 1)
    window.scrollTo(0, from + (to - from) * easeInOutCubic(progress))
    if (progress < 1) {
      guideRafId = requestAnimationFrame(step)
      return
    }
    guideRafId = 0
    guideAnimating = false
    window.scrollTo(0, to)
  }

  guideRafId = requestAnimationFrame(step)
}

/** 购买入口：仅按茶名跳转淘宝搜索，不接入交易（茶名为空时不渲染） */
const purchaseUrl = computed(() => (tea.value ? buildTaobaoSearchUrl(tea.value.name) : null))

watch(
  () => route.params.id,
  () => {
    stopGuideAnimation()
    guideExpanded.value = false
    void load()
  },
  { immediate: true },
)

onMounted(() => {
  void replayPendingAction()
})

function getErrorCode(err: unknown): number | undefined {
  return (err as { response?: { data?: { code?: number } } }).response?.data?.code
}

async function load() {
  const raw = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const id = Number.parseInt(raw ?? '', 10)

  tea.value = null
  related.value = []
  fallbackHot.value = []
  errorMessage.value = ''
  imageFailed.value = false
  videoFailed.value = false
  activeImage.value = null

  if (!Number.isFinite(id) || id < 1) {
    state.value = 'notfound'
    void loadFallbackHot()
    return
  }

  state.value = 'loading'
  try {
    const res = await getTeaDetail(id)
    tea.value = res.data
    if (!tea.value) {
      state.value = 'notfound'
      void loadFallbackHot()
      return
    }
    favoriteCount.value = res.data.favorite_count
    state.value = 'ready'
    addHistory({
      tea_id: res.data.id,
      name: res.data.name,
      category: res.data.category,
      cover_image: res.data.main_image_url ?? null,
      viewed_at: new Date().toISOString(),
    })
    void loadRelated(tea.value.id)
  } catch (err) {
    const code = getErrorCode(err)
    if (code === 40401) {
      // 下架茶品：API 不返回茶类，无法给出同类推荐，改用热门推荐引导（见 build-log 口径）
      state.value = 'offline'
    } else if (code === 40400) {
      state.value = 'notfound'
    } else {
      state.value = 'error'
      errorMessage.value = err instanceof Error ? err.message : '加载失败'
    }
    void loadFallbackHot()
  }
}

async function loadRelated(id: number) {
  try {
    const res = await getRelatedTeas(id, 4)
    related.value = res.data ?? []
  } catch {
    related.value = []
  }
}

async function loadFallbackHot() {
  if (fallbackHot.value.length) return
  try {
    const res = await getHotTeas(3)
    fallbackHot.value = res.data ?? []
  } catch {
    fallbackHot.value = []
  }
}

/** 写笔记：必须已收藏，否则后端 40430；前端只做体验提示 */
async function openNoteEditor(teaId: number) {
  try {
    const res = await getFavoriteStatus(teaId)
    if (!res.data.is_favorited) {
      toast.info('请先收藏该茶品，再写品鉴笔记')
      return
    }
    void router.push({ name: 'my-list', query: { note: String(teaId) } })
  } catch {
    // 错误提示已由请求拦截器统一处理
  }
}

async function onNoteAction() {
  if (!tea.value) return
  if (!userStore.isLoggedIn) {
    savePendingAction({ type: 'note', teaId: tea.value.id, path: route.fullPath })
    void router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  await openNoteEditor(tea.value.id)
}

/** 分享入口在我的清单页 */
function onShareAction() {
  if (!userStore.isLoggedIn) {
    if (tea.value) {
      savePendingAction({ type: 'share', teaId: tea.value.id, path: route.fullPath })
    }
    void router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  void router.push({ name: 'my-list', query: { share: '1' } })
}

/** 登录后回到本页时，继续执行登录前被中断的笔记/分享动作 */
async function replayPendingAction() {
  const pending = loadPendingAction()
  if (!pending || !userStore.isLoggedIn || pending.path !== route.fullPath) return
  clearPendingAction()
  if (pending.type === 'note') {
    await openNoteEditor(pending.teaId)
    return
  }
  void router.push({ name: 'my-list', query: { share: '1' } })
}

function retry() {
  void load()
}
</script>

<template>
  <AppHeader />

  <main class="detail-page">
    <div class="container">
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <RouterLink to="/teas">茶品列表</RouterLink>
        <template v-if="tea">
          <span class="breadcrumb__sep">›</span>
          <span class="breadcrumb__current">{{ tea.name }}</span>
        </template>
      </nav>

      <!-- 骨架屏 -->
      <div v-if="state === 'loading'" class="detail-skeleton" aria-hidden="true">
        <div class="skeleton detail-skeleton__image"></div>
        <div class="detail-skeleton__right">
          <div class="skeleton skeleton__line skeleton__line--title"></div>
          <div class="skeleton skeleton__line"></div>
          <div class="skeleton skeleton__line" style="width: 40%"></div>
        </div>
      </div>

      <!-- 正文 -->
      <article v-else-if="state === 'ready' && tea" class="detail-content">
        <section class="detail-header">
          <div class="detail-header__image-wrap">
            <img
              v-if="hasImage"
              class="detail-header__image"
              :src="displayImage as string"
              :alt="tea.name"
              @error="imageFailed = true"
            />
            <div
              v-else
              class="detail-header__image detail-header__image--placeholder"
              aria-hidden="true"
            >
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path
                  d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19.2 2.5c1 1.66.6 6-2 9-2 2.4-6.2 3-6.2 3zM2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"
                />
              </svg>
            </div>
            <CategoryTag class="detail-header__category-tag" :category="tea.category" clickable />
            <!-- 图片集缩略图（S4）：仅 2 张以上才展示，避免单图冗余 -->
            <div v-if="galleryImages.length > 1" class="detail-gallery">
              <button
                v-for="url in galleryImages"
                :key="url"
                type="button"
                class="detail-gallery__thumb"
                :class="{ 'detail-gallery__thumb--active': url === displayImage }"
                @click="((activeImage = url), (imageFailed = false))"
              >
                <img :src="url" :alt="`${tea.name} 图片`" loading="lazy" />
              </button>
            </div>
          </div>

          <div class="detail-header__info">
            <p class="page-kicker">Tea Detail</p>
            <div class="detail-header__meta-top">
              <span v-if="tea.season">{{ tea.season }}</span>
              <span>♡ <CountUp :value="favoriteCount" /> 人收藏</span>
            </div>
            <div class="detail-header__title-row">
              <RevealText as="h1" class="detail-header__name" :text="tea.name" />

              <!-- 购买入口：茶名右侧 -->
              <div v-if="purchaseUrl" class="purchase-entry">
                <a
                  class="btn btn--primary"
                  :href="purchaseUrl as string"
                  target="_blank"
                  rel="noopener noreferrer"
                  :title="`在淘宝搜索「${tea.name}」`"
                >
                  <span aria-hidden="true">🛒</span>
                  去淘宝搜索同款
                </a>
                <span class="purchase-entry__hint">跳转第三方平台，本站不参与交易</span>
              </div>
            </div>

            <p class="detail-header__origin">{{ tea.origin }}</p>

            <div v-if="hasBrew || brewingGuide" class="brew-card">
              <h3 class="brew-card__title">
                {{ brewingGuide ? '冲泡教程' : '冲泡参考' }}
              </h3>
              <p v-if="brewingGuide?.intro" class="brew-card__intro">{{ brewingGuide.intro }}</p>

              <div v-if="hasBrew" class="brew-card__grid">
                <div v-for="item in brewItems" :key="item.label" class="brew-card__item">
                  <span class="brew-card__icon">{{ item.icon }}</span>
                  <span class="brew-card__label">{{ item.label }}</span>
                  <span class="brew-card__value">{{ item.value }}</span>
                </div>
              </div>

              <div
                v-if="brewingGuide"
                class="brew-card__collapse"
                :class="{ 'brew-card__collapse--open': guideExpanded }"
                :aria-hidden="!guideExpanded"
              >
                <div class="brew-card__collapse-inner">
                  <ol class="brew-steps">
                    <li v-for="(step, index) in brewingGuide.steps" :key="index" class="brew-step">
                      <span class="brew-step__index">{{ index + 1 }}</span>
                      <div class="brew-step__body">
                        <h4 class="brew-step__title">{{ step.title }}</h4>
                        <p class="brew-step__detail">{{ step.detail }}</p>
                        <p v-if="step.tip" class="brew-step__tip">小提示：{{ step.tip }}</p>
                      </div>
                    </li>
                  </ol>

                  <p v-if="brewingGuide.caution" class="brew-card__caution">
                    ⚠️ {{ brewingGuide.caution }}
                  </p>
                </div>
              </div>

              <button
                v-if="canExpandGuide"
                type="button"
                class="brew-card__toggle"
                :aria-expanded="guideExpanded"
                @click="toggleGuide"
              >
                <span>
                  {{
                    guideExpanded
                      ? '收起教程'
                      : `展开冲泡教程（共 ${brewingGuide?.steps.length} 步）`
                  }}
                </span>
                <svg
                  class="brew-card__chevron"
                  :class="{ 'brew-card__chevron--up': guideExpanded }"
                  viewBox="0 0 12 12"
                  width="10"
                  height="10"
                  aria-hidden="true"
                >
                  <path
                    d="M2 4l4 4 4-4"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
            </div>

            <div class="detail-header__actions">
              <FavoriteButton
                variant="primary"
                :tea-id="tea.id"
                :count="favoriteCount"
                @change="favoriteCount = $event"
              />
              <button type="button" class="btn btn--secondary" @click="onNoteAction">
                ✏️ 写品鉴笔记
              </button>
              <button type="button" class="btn btn--ghost" @click="onShareAction">
                ↗️ 分享清单
              </button>
              <RouterLink
                class="btn btn--ghost"
                :to="{ name: 'contribute', query: { type: 'article', tea_id: String(tea.id) } }"
              >
                📝 投稿科普
              </RouterLink>
            </div>
          </div>
        </section>

        <!-- 视频介绍（S5）：无视频或加载失败整块隐藏 -->
        <section v-if="hasVideo" class="detail-section">
          <h2 class="detail-section__title">
            视频介绍
            <span v-if="videoDurationText" class="detail-section__hint">{{
              videoDurationText
            }}</span>
          </h2>
          <video
            class="detail-video"
            controls
            preload="metadata"
            playsinline
            :src="tea.video_url as string"
            :poster="tea.main_image_url ?? undefined"
            @error="videoFailed = true"
          >
            你的浏览器不支持视频播放。
          </video>
        </section>

        <!-- 四大感官 -->
        <section class="detail-section">
          <h2 class="detail-section__title">品鉴特征</h2>
          <div class="detail-senses">
            <div class="sense-card">
              <div class="sense-card__icon">🫛</div>
              <h4 class="sense-card__label">外形</h4>
              <p class="sense-card__text">{{ tea.shape_desc }}</p>
            </div>
            <div class="sense-card">
              <div class="sense-card__icon">🍶</div>
              <h4 class="sense-card__label">汤色</h4>
              <p class="sense-card__text">{{ tea.soup_desc }}</p>
            </div>
            <div class="sense-card">
              <div class="sense-card__icon">🌿</div>
              <h4 class="sense-card__label">香气</h4>
              <p class="sense-card__text">{{ tea.aroma_desc }}</p>
            </div>
            <div class="sense-card">
              <div class="sense-card__icon">👅</div>
              <h4 class="sense-card__label">滋味</h4>
              <p class="sense-card__text">{{ tea.taste_desc }}</p>
            </div>
          </div>
        </section>

        <!-- 小贴士（空内容整块隐藏；全部为空则整段隐藏） -->
        <section v-if="tips.length" class="detail-section">
          <h2 class="detail-section__title">茶小知识</h2>
          <div class="detail-tips">
            <div v-for="tip in tips" :key="tip.title" class="tip-card">
              <div class="tip-card__icon">{{ tip.icon }}</div>
              <div class="tip-card__body">
                <h4 class="tip-card__title">{{ tip.title }}</h4>
                <p class="tip-card__text">{{ tip.text }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- 茶友科普投稿（S11 / S12）：仅展示审核通过内容 -->
        <section v-if="contributedArticles.length" class="detail-section">
          <h2 class="detail-section__title">茶友科普</h2>
          <div class="article-list">
            <article v-for="article in contributedArticles" :key="article.id" class="article-card">
              <h4 class="article-card__title">{{ article.title || '茶友分享' }}</h4>
              <p class="article-card__content">{{ article.content }}</p>
              <footer class="article-card__meta">
                — {{ article.contributor }} · {{ formatArticleDate(article.created_at) }}
              </footer>
            </article>
          </div>
        </section>

        <!-- 同类推荐 -->
        <section v-if="related.length" class="detail-section">
          <h2 class="detail-section__title">同属一类 · 你可能也喜欢</h2>
          <div class="related-grid">
            <TeaCard v-for="item in related" :key="item.id" :tea="item" />
          </div>
        </section>
      </article>

      <!-- 下架 / 不存在 / 加载失败 -->
      <div v-else class="detail-state">
        <div class="detail-state__icon">🫖</div>
        <h2 class="detail-state__title">
          <template v-if="state === 'offline'">这款茶已下架</template>
          <template v-else-if="state === 'notfound'">这款茶暂时找不到了</template>
          <template v-else>加载失败</template>
        </h2>
        <p class="detail-state__desc">
          <template v-if="state === 'offline'">它可能已下架，暂时无法查看详情</template>
          <template v-else-if="state === 'notfound'">它可能已下架，或者页面链接有误</template>
          <template v-else>{{ errorMessage }}</template>
        </p>
        <div class="detail-state__actions">
          <button v-if="state === 'error'" type="button" class="btn btn--secondary" @click="retry">
            重新加载
          </button>
          <RouterLink class="btn btn--secondary" to="/teas">浏览茶品列表</RouterLink>
          <RouterLink class="btn btn--ghost" to="/">回首页</RouterLink>
        </div>

        <div v-if="fallbackHot.length && state !== 'error'" class="detail-state__suggest">
          <TeaCard v-for="item in fallbackHot" :key="item.id" :tea="item" compact />
        </div>
      </div>
    </div>
  </main>

  <AppFooter />
</template>

<style scoped>
.detail-page {
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
  .detail-page {
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

/* 骨架屏 */
.detail-skeleton {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  padding-top: 20px;
}

@media (max-width: 767px) {
  .detail-skeleton {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}

.detail-skeleton__image {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-lg);
}

.detail-skeleton__right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 20px;
}

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
  animation: skeleton-shimmer 1.5s infinite;
}

@keyframes skeleton-shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.skeleton__line {
  height: 24px;
  border-radius: var(--radius-sm);
}

.skeleton__line--title {
  height: 36px;
  width: 60%;
}

/* 头部 */
.detail-header {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 48px;
  padding: 20px 0 48px;
}

@media (max-width: 767px) {
  .detail-header {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}

.detail-header__image-wrap {
  position: relative;
}

.detail-header__image {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-lg);
  object-fit: cover;
  background: var(--color-bg-muted);
}

.detail-header__image--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.detail-header__image--placeholder svg {
  width: 48px;
  height: 48px;
  opacity: 0.5;
}

.detail-header__category-tag {
  position: absolute;
  top: 16px;
  left: 16px;
  backdrop-filter: blur(4px);
}

/* 图片集缩略图（S4） */
.detail-gallery {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.detail-gallery__thumb {
  flex: 0 0 72px;
  width: 72px;
  height: 56px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: var(--radius-sm);
  overflow: hidden;
  cursor: pointer;
  background: var(--color-bg-muted);
  transition: border-color 0.2s ease;
}

.detail-gallery__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.detail-gallery__thumb--active,
.detail-gallery__thumb:hover {
  border-color: var(--color-primary);
}

.detail-gallery__thumb:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* 视频介绍（S5） */
.detail-video {
  width: 100%;
  max-height: 520px;
  border-radius: var(--radius-lg);
  background: var(--color-bg-muted);
  display: block;
}

.detail-section__hint {
  margin-left: 8px;
  font-family: var(--font-body);
  font-size: var(--text-small);
  font-weight: 400;
  color: var(--color-text-muted);
}

.detail-header__info {
  display: flex;
  flex-direction: column;
}

.detail-header__meta-top {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin-bottom: 12px;
}

.detail-header__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
}

.detail-header__name {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.3;
}

.detail-header__origin {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  margin: 0 0 24px;
}

/* 冲泡参考 */
.brew-card {
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  margin-bottom: 24px;
}

/* 折叠容器：用 grid 行高过渡，展开/收起是连续高度动画而非瞬间塌陷 */
.brew-card__collapse {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 320ms cubic-bezier(0.65, 0, 0.35, 1);
}

.brew-card__collapse--open {
  grid-template-rows: 1fr;
}

.brew-card__collapse-inner {
  min-height: 0;
  overflow: hidden;
}

.brew-card__title {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 16px;
}

.brew-card__intro {
  margin: -8px 0 16px;
  font-size: var(--text-small);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.brew-card__caution {
  margin: 16px 0 0;
  padding: 10px 14px;
  border-left: 3px solid var(--color-warning);
  border-radius: var(--radius-sm);
  background: var(--color-bg-surface);
  font-size: var(--text-caption);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.brew-card__toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  margin-top: 14px;
  padding: 9px 12px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: var(--text-caption);
  color: var(--color-primary);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.brew-card__toggle:hover {
  background: var(--color-bg-muted);
}

.brew-card__chevron {
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.brew-card__chevron--up {
  transform: rotate(180deg);
}

.brew-steps {
  list-style: none;
  margin: 18px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.brew-step {
  display: flex;
  gap: 12px;
}

.brew-step__index {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--text-caption);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brew-step__body {
  min-width: 0;
}

.brew-step__title {
  margin: 0 0 4px;
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-text-primary);
}

.brew-step__detail {
  margin: 0;
  font-size: var(--text-small);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.brew-step__tip {
  margin: 4px 0 0;
  font-size: var(--text-caption);
  line-height: 1.6;
  color: var(--color-text-muted);
}

.brew-card__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 480px) {
  .brew-card__grid {
    grid-template-columns: 1fr;
  }
}

.brew-card__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.brew-card__icon {
  font-size: 20px;
}

.brew-card__label {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.brew-card__value {
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-primary-dark);
  font-variant-numeric: tabular-nums;
}

.detail-header__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 购买入口：茶名右侧 */
.purchase-entry {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.purchase-entry__hint {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

@media (max-width: 767px) {
  .purchase-entry {
    align-items: flex-start;
  }
  .purchase-entry .btn {
    width: 100%;
  }
}

/* 通用 section */
.detail-section {
  padding: 32px 0;
  border-top: 1px solid var(--color-border);
}

.detail-section__title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 24px;
}

/* 四大感官 */
.detail-senses {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1023px) {
  .detail-senses {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .detail-senses {
    grid-template-columns: 1fr;
  }
}

.sense-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
}

.sense-card__icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.sense-card__label {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 8px;
}

.sense-card__text {
  font-size: var(--text-body);
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.7;
}

/* 小贴士 */
.detail-tips {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 639px) {
  .detail-tips {
    grid-template-columns: 1fr;
  }
}

.tip-card {
  display: flex;
  gap: 16px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
}

.tip-card__icon {
  font-size: 24px;
  flex-shrink: 0;
}

.tip-card__body {
  flex: 1;
}

.tip-card__title {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-primary-dark);
  margin: 0 0 8px;
}

.tip-card__text {
  font-size: var(--text-body);
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.7;
}

/* 茶友科普投稿 */
.article-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.article-card {
  padding: 20px 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
}

.article-card__title {
  margin: 0 0 10px;
  font-size: var(--text-h3);
  color: var(--color-primary-dark);
}

.article-card__content {
  margin: 0;
  color: var(--color-text-primary);
  line-height: 1.8;
  white-space: pre-wrap;
}

.article-card__meta {
  margin-top: 12px;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  text-align: right;
}

/* 同类推荐 */
.related-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1023px) {
  .related-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 639px) {
  .related-grid {
    grid-template-columns: 1fr;
  }
}

/* 下架 / 不存在 */
.detail-state {
  text-align: center;
  padding: 64px 24px;
}

.detail-state__icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.detail-state__title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  color: var(--color-text-secondary);
  margin: 0 0 8px;
}

.detail-state__desc {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin: 0 0 24px;
}

.detail-state__actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 12px;
}

.detail-state__suggest {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 560px;
  margin: 40px auto 0;
}

@media (max-width: 639px) {
  .detail-state__suggest {
    grid-template-columns: 1fr;
  }
}

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  padding: 0 24px;
  border-radius: var(--radius-full);
  font-size: var(--text-body);
  font-weight: 500;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
  white-space: nowrap;
}

.btn--primary {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn--primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.btn--secondary {
  background: transparent;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}

.btn--secondary:hover {
  background: var(--color-bg-muted);
}

.btn--ghost {
  height: 36px;
  padding: 0 16px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  font-weight: 400;
}

.btn--ghost:hover {
  background: var(--color-bg-muted);
}
</style>
