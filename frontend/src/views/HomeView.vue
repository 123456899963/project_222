<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import HeroBackground from '@/components/HeroBackground.vue'
import TeaCard from '@/components/TeaCard.vue'
import CategoryTag from '@/components/CategoryTag.vue'
import CountUp from '@/components/effects/CountUp.vue'
import RevealText from '@/components/effects/RevealText.vue'
import SpotlightCard from '@/components/effects/SpotlightCard.vue'
import { useTeaStore } from '@/stores/tea'
import { useUserStore } from '@/stores/user'
import {
  getHotTeas,
  getLatestTips,
  getRandomTea,
  getRecommendedTeas,
  getTeaDetail,
  getTeaList,
} from '@/api/teas'
import { CATEGORY_LABELS, TEA_CATEGORIES } from '@/utils/teaQuery'
import type { LatestTipItem, Tea, TeaCategory, TeaListItem } from '@/types'

const router = useRouter()
const teaStore = useTeaStore()
const userStore = useUserStore()

const CATEGORY_EN: Record<TeaCategory, string> = {
  green: 'GREEN TEA',
  white: 'WHITE TEA',
  yellow: 'YELLOW TEA',
  red: 'BLACK TEA',
  oolong: 'OOLONG TEA',
  dark: 'DARK TEA',
  reprocessed: 'REPROCESSED TEA',
}

const hotList = ref<TeaListItem[]>([])
const hotLoading = ref(true)
const hotTrack = ref<HTMLElement | null>(null)
const randomTea = ref<Tea | null>(null)
const randomLoading = ref(true)
const spinning = ref(false)

/* 沉浸式 Hero：背景与内容以不同速率位移形成纵深，减少动态效果下完全静止 */
const heroBgRef = ref<HTMLElement | null>(null)
const heroContentRef = ref<HTMLElement | null>(null)
const heroCueRef = ref<HTMLElement | null>(null)
let heroFrame = 0

function prefersReducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

function updateHeroDepth() {
  heroFrame = 0
  if (prefersReducedMotion()) return
  const hero = heroBgRef.value?.parentElement
  const offset = window.scrollY
  if (!hero || offset > hero.offsetHeight) return
  if (heroBgRef.value) {
    heroBgRef.value.style.transform = `translate3d(0, ${offset * 0.28}px, 0)`
  }
  if (heroContentRef.value) {
    heroContentRef.value.style.transform = `translate3d(0, ${offset * -0.06}px, 0)`
    heroContentRef.value.style.opacity = String(Math.max(0, 1 - offset / 360))
  }
  if (heroCueRef.value) {
    heroCueRef.value.style.opacity = String(Math.max(0, 1 - offset / 160))
  }
}

function onHeroScroll() {
  if (heroFrame) return
  heroFrame = requestAnimationFrame(updateHeroDepth)
}

/** 登录用户展示个性化推荐（S16），游客保持随机发现 */
const randomTitle = computed(() => (userStore.isLoggedIn ? '为你推荐' : '🎲 随机发现'))
const randomDesc = computed(() =>
  userStore.isLoggedIn
    ? '根据你收藏过的茶类，为你挑选一款可能合口味的新茶。每次点击都会换一款。'
    : '不知道喝什么？点下面按钮，让命运为你选一款。每次都不一样，说不定就能遇到你的下一杯心头好。',
)

const latestTips = ref<LatestTipItem[]>([])
const tipsLoading = ref(true)

const keyword = ref('')
const suggestOpen = ref(false)
const suggestLoading = ref(false)
const suggestions = ref<TeaListItem[]>([])
let suggestTimer: ReturnType<typeof setTimeout> | null = null
let suggestSeq = 0

const categoryCards = computed(() => {
  const countMap = new Map(teaStore.categories.map((c) => [c.category, c.count]))
  return TEA_CATEGORIES.map((category) => ({
    category,
    label: CATEGORY_LABELS[category],
    en: CATEGORY_EN[category],
    count: countMap.get(category) ?? 0,
  }))
})

/** 首页统计带：全部取自已有分类 / 产地数据，不新增接口 */
const totalTeas = computed(() => teaStore.categories.reduce((sum, c) => sum + c.count, 0))
const originCount = computed(() => teaStore.origins.length)

/** 按当前月份给出当季茶，用于引导入口文案与筛选参数 */
const currentSeason = computed(() => {
  const month = new Date().getMonth() + 1
  if (month >= 3 && month <= 5) return '春茶'
  if (month >= 6 && month <= 8) return '夏茶'
  if (month >= 9 && month <= 11) return '秋茶'
  return '冬茶'
})

/** 引导入口：按意图而非品类分流 */
const guideEntries = computed(() => [
  {
    index: '01',
    title: '新手入门',
    desc: '从轻发酵的绿茶、白茶喝起，先建立味觉坐标',
    to: { name: 'tea-list', query: { fermentation: '不发酵,微发酵' } },
  },
  {
    index: '02',
    title: `${currentSeason.value}正当时`,
    desc: '按采摘季节筛选，挑一款当季的茶',
    to: { name: 'tea-list', query: { season: currentSeason.value } },
  },
  {
    index: '03',
    title: '七大茶类对比',
    desc: '把两到三款茶并排看，差异一眼看清',
    to: { name: 'compare' },
  },
])

async function loadHot() {
  hotLoading.value = true
  try {
    const res = await getHotTeas(8)
    hotList.value = res.data ?? []
  } catch {
    hotList.value = []
  } finally {
    hotLoading.value = false
  }
}

async function loadRandom() {
  randomLoading.value = true
  try {
    if (userStore.isLoggedIn) {
      // 个性化推荐返回列表卡片，首页卡片需要冲泡信息，再取一次详情
      const res = await getRecommendedTeas(1, randomTea.value?.id)
      const item = res.data?.[0]
      randomTea.value = item ? (await getTeaDetail(item.id)).data : null
    } else {
      const res = await getRandomTea(randomTea.value?.id)
      randomTea.value = res.data
    }
  } catch {
    randomTea.value = null
  } finally {
    randomLoading.value = false
  }
}

/** 首页最新小贴士（S7） */
async function loadTips() {
  tipsLoading.value = true
  try {
    const res = await getLatestTips(3)
    latestTips.value = res.data ?? []
  } catch {
    latestTips.value = []
  } finally {
    tipsLoading.value = false
  }
}

function scrollHot(delta: number) {
  hotTrack.value?.scrollBy({ left: delta, behavior: 'smooth' })
}

function shuffle() {
  if (spinning.value || randomLoading.value) return
  spinning.value = true
  void loadRandom().finally(() => {
    setTimeout(() => {
      spinning.value = false
    }, 400)
  })
}

onMounted(() => {
  teaStore.fetchCategories().catch(() => {})
  teaStore.fetchOrigins().catch(() => {})
  void loadHot()
  void loadRandom()
  void loadTips()
  document.addEventListener('click', onDocumentClick)
  window.addEventListener('scroll', onHeroScroll, { passive: true })
  updateHeroDepth()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  window.removeEventListener('scroll', onHeroScroll)
  if (heroFrame) cancelAnimationFrame(heroFrame)
  if (suggestTimer) clearTimeout(suggestTimer)
})

// —— Hero 搜索：150ms 防抖 + 真实后端搜索（最多 6 条）——
watch(keyword, (value) => {
  if (suggestTimer) clearTimeout(suggestTimer)
  const q = value.trim()
  if (!q) {
    suggestions.value = []
    suggestOpen.value = false
    suggestLoading.value = false
    return
  }
  suggestTimer = setTimeout(() => {
    void fetchSuggestions(q)
  }, 150)
})

async function fetchSuggestions(q: string) {
  const seq = ++suggestSeq
  suggestLoading.value = true
  suggestOpen.value = true
  try {
    const res = await getTeaList({ keyword: q, page: 1, page_size: 6, sort: 'newest' })
    if (seq !== suggestSeq) return
    suggestions.value = res.data?.items ?? []
  } catch {
    if (seq !== suggestSeq) return
    suggestions.value = []
  } finally {
    if (seq === suggestSeq) {
      suggestLoading.value = false
      suggestOpen.value = true
    }
  }
}

function submitSearch() {
  const q = keyword.value.trim()
  if (!q) return
  suggestOpen.value = false
  router.push({ name: 'tea-list', query: { q } })
}

function pickSuggestion(tea: TeaListItem) {
  suggestOpen.value = false
  keyword.value = tea.name
  router.push({ name: 'tea-list', query: { q: tea.name } })
}

function onDocumentClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (!target?.closest('.hero__search')) {
    suggestOpen.value = false
  }
}

function categoryStyle(category: TeaCategory) {
  return { '--cat-color': `var(--color-tea-${category})` }
}
</script>

<template>
  <AppHeader />

  <main class="home-page">
    <!-- Hero -->
    <section class="hero">
      <!-- 纯装饰滚动背景（ADR-0003 R7）：不承载点击与跳转 -->
      <div ref="heroBgRef" class="hero__bg-layer">
        <HeroBackground />
      </div>
      <div class="hero__scrim" aria-hidden="true"></div>
      <div ref="heroContentRef" class="container hero__content">
        <span class="hero__kicker">七大茶类 · 结构化知识库</span>
        <h1 class="hero__title">
          <RevealText as="span" text="一杯茶的" />
          <RevealText as="span" class="hero__title-accent" text="千种风味" :delay="60" />
        </h1>
        <RevealText
          as="p"
          class="hero__subtitle"
          text="完整图鉴，清晰对比，让每一款茶都有迹可循"
          :delay="55"
        />

        <div class="hero__search">
          <svg
            class="hero__search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            v-model="keyword"
            class="hero__search-input"
            type="search"
            placeholder="搜索茶品名称、产地，如：西湖龙井、福建"
            aria-label="搜索茶品"
            @focus="suggestOpen = !!keyword.trim()"
            @keydown.enter.prevent="submitSearch"
          />

          <div v-if="suggestOpen" class="hero__search-suggest">
            <div v-if="suggestLoading" class="hero__search-hint">搜索中…</div>
            <div v-else-if="!suggestions.length" class="hero__search-hint">没有找到相关茶品</div>
            <template v-else>
              <button
                v-for="tea in suggestions"
                :key="tea.id"
                type="button"
                class="hero__search-suggest-item"
                @click="pickSuggestion(tea)"
              >
                <img
                  v-if="tea.main_image_url"
                  class="hero__search-suggest-item__thumb"
                  :src="tea.main_image_url"
                  :alt="tea.name"
                />
                <span
                  v-else
                  class="hero__search-suggest-item__thumb hero__search-suggest-item__thumb--empty"
                ></span>
                <span class="hero__search-suggest-item__info">
                  <span class="hero__search-suggest-item__name">{{ tea.name }}</span>
                  <span class="hero__search-suggest-item__origin">{{ tea.origin }}</span>
                </span>
              </button>
            </template>
          </div>
        </div>
      </div>

      <div ref="heroCueRef" class="hero__cue" aria-hidden="true">
        <span class="hero__cue-text">向下探索</span>
        <span class="hero__cue-line"></span>
      </div>
    </section>

    <!-- 统计带：图鉴的规模感 -->
    <section class="stats">
      <div class="container stats__inner">
        <div class="stats__item">
          <span class="stats__value"><CountUp :value="totalTeas" /></span>
          <span class="stats__label">款茶品已收录</span>
        </div>
        <span class="stats__divider" aria-hidden="true"></span>
        <div class="stats__item">
          <span class="stats__value">{{ TEA_CATEGORIES.length }}</span>
          <span class="stats__label">大茶类体系</span>
        </div>
        <span class="stats__divider" aria-hidden="true"></span>
        <div class="stats__item">
          <span class="stats__value"><CountUp :value="originCount" /></span>
          <span class="stats__label">个产地覆盖</span>
        </div>
      </div>
    </section>

    <!-- 引导入口：按意图而非品类分流 -->
    <section class="guides container">
      <div class="guides__grid">
        <RouterLink
          v-for="entry in guideEntries"
          :key="entry.index"
          class="guide-card"
          :to="entry.to"
        >
          <span class="guide-card__index">{{ entry.index }}</span>
          <span class="guide-card__title">{{ entry.title }}</span>
          <span class="guide-card__desc">{{ entry.desc }}</span>
          <span class="guide-card__arrow" aria-hidden="true">→</span>
        </RouterLink>
      </div>
    </section>

    <!-- 七大茶类入口 -->
    <section class="categories container">
      <div class="section-heading">
        <span class="section-kicker">SEVEN CATEGORIES</span>
        <RevealText as="h2" class="section-title" text="七大茶类" />
        <p class="section-subtitle">不同工艺，不同风味，点进去探索</p>
      </div>
      <div class="categories__grid">
        <SpotlightCard
          v-for="item in categoryCards"
          :key="item.category"
          class="category-card-host"
          radius="var(--radius-lg)"
        >
          <RouterLink
            class="category-card"
            :style="categoryStyle(item.category)"
            :to="{ name: 'tea-list', query: { category: item.category } }"
          >
            <span class="category-card__swatch" aria-hidden="true"></span>
            <div class="category-card__name">{{ item.label }}</div>
            <div class="category-card__en">{{ item.en }}</div>
            <div class="category-card__count"><CountUp :value="item.count" /> 款已收录</div>
          </RouterLink>
        </SpotlightCard>
      </div>
    </section>

    <!-- 热门推荐 -->
    <section class="section">
      <div class="container">
        <div class="section-header">
          <div class="section-header__main">
            <span class="section-kicker section-kicker--start">POPULAR TEAS</span>
            <RevealText as="h2" class="section-header__title" text="热门推荐" />
          </div>
          <RouterLink class="section-header__action" to="/teas">查看全部 →</RouterLink>
        </div>

        <div v-if="hotLoading" class="hot-loading">热门推荐加载中…</div>
        <div v-else-if="!hotList.length" class="hot-loading">暂无热门茶品</div>
        <div v-else class="hot-scroll">
          <button
            type="button"
            class="hot-scroll__arrow hot-scroll__arrow--left"
            aria-label="向左滚动"
            @click="scrollHot(-440)"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path d="m15 18-6-6 6-6" />
            </svg>
          </button>

          <div ref="hotTrack" class="hot-scroll__track">
            <TeaCard v-for="tea in hotList" :key="tea.id" :tea="tea" class="hot-card" />
          </div>

          <button
            type="button"
            class="hot-scroll__arrow hot-scroll__arrow--right"
            aria-label="向右滚动"
            @click="scrollHot(440)"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path d="m9 18 6-6-6-6" />
            </svg>
          </button>
        </div>
      </div>
    </section>

    <!-- 随机发现 -->
    <section class="section">
      <div class="container">
        <div class="random">
          <div class="random__body">
            <SpotlightCard
              v-if="randomTea"
              class="random-card-host"
              radius="var(--radius-xl)"
              tilt
              :max-tilt="4"
            >
              <RouterLink
                class="card-random"
                :to="{ name: 'tea-detail', params: { id: randomTea.id } }"
              >
                <img
                  v-if="randomTea.main_image_url"
                  class="card-random__img"
                  :src="randomTea.main_image_url"
                  :alt="randomTea.name"
                />
                <div
                  v-else
                  class="card-random__img card-random__img--placeholder"
                  aria-hidden="true"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path
                      d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19.2 2.5c1 1.66.6 6-2 9-2 2.4-6.2 3-6.2 3zM2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"
                    />
                  </svg>
                </div>
                <div class="card-random__body">
                  <h3 class="card-random__name">{{ randomTea.name }}</h3>
                  <div class="card-random__tags">
                    <CategoryTag :category="randomTea.category" />
                    <span class="card-random__fav"
                      >♡ {{ randomTea.favorite_count.toLocaleString('zh-CN') }}</span
                    >
                  </div>
                  <div class="card-random__brew">
                    <span v-if="randomTea.water_temp">🌡️ {{ randomTea.water_temp }}℃</span>
                    <span v-if="randomTea.tea_amount">🫖 {{ randomTea.tea_amount }}g</span>
                    <span v-if="randomTea.brew_time">⏱ {{ randomTea.brew_time }}秒</span>
                  </div>
                </div>
              </RouterLink>
            </SpotlightCard>
            <div v-else class="card-random card-random--empty">
              {{ randomLoading ? '随机茶品加载中…' : '暂时没有可推荐的茶品' }}
            </div>

            <div class="random__desc">
              <h3>{{ randomTitle }}</h3>
              <p>{{ randomDesc }}</p>
              <button
                type="button"
                class="random__shuffle-btn"
                :class="{ spinning }"
                :disabled="randomLoading"
                @click="shuffle"
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
                  <path d="M21 3v5h-5" />
                  <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
                  <path d="M3 21v-5h5" />
                </svg>
                <span>{{ randomLoading ? '加载中…' : '换一批' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
    <!-- 茶知识 · 小贴士（S7） -->
    <section v-if="tipsLoading || latestTips.length" class="section">
      <div class="container">
        <div class="section-header">
          <div class="section-header__main">
            <span class="section-kicker section-kicker--start">TEA NOTES</span>
            <RevealText as="h2" class="section-header__title" text="茶知识 · 小贴士" />
          </div>
          <RouterLink class="section-header__action" to="/teas">探索更多 →</RouterLink>
        </div>

        <div v-if="tipsLoading" class="hot-loading">小贴士加载中…</div>
        <div v-else class="tips-grid">
          <SpotlightCard
            v-for="tip in latestTips"
            :key="tip.tea_id"
            class="tip-host"
            radius="var(--radius-lg)"
          >
            <RouterLink
              class="tip-preview"
              :to="{ name: 'tea-detail', params: { id: tip.tea_id } }"
            >
              <div class="tip-preview__head">
                <span class="tip-preview__tea">{{ tip.tea_name }}</span>
                <CategoryTag :category="tip.category" />
              </div>
              <p class="tip-preview__summary">{{ tip.summary }}</p>
              <span class="tip-preview__more">了解详情 ›</span>
            </RouterLink>
          </SpotlightCard>
        </div>
      </div>
    </section>
  </main>

  <AppFooter />
</template>

<style scoped>
.home-page {
  /* 首页 Hero 顶到视口顶部，页头以透明态浮在背景之上（AppHeader 负责滚动后转实底） */
  padding-top: 0;
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
  .container {
    padding: 0 16px;
  }
}

/* Hero：沉浸式首屏，背景下沉 + 内容上浮形成纵深 */
.hero {
  position: relative;
  min-height: calc(100vh - 64px);
  min-height: max(560px, calc(100vh - 64px));
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 120px 0 96px;
  text-align: center;
  overflow: hidden;
  background: var(--color-bg-hero);
  isolation: isolate;
}

.hero__bg-layer {
  position: absolute;
  top: -20%;
  left: 0;
  right: 0;
  height: 140%;
  z-index: -1;
  will-change: transform;
}

/* 暗色压边：顶部压暗保证页头可读，中段留亮保持照片清晰，底部压暗托住标题 */
.hero__scrim {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(
    180deg,
    rgba(32, 26, 20, 0.62) 0%,
    rgba(32, 26, 20, 0.18) 34%,
    rgba(32, 26, 20, 0.52) 72%,
    rgba(32, 26, 20, 0.86) 100%
  );
  pointer-events: none;
}

.hero__content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hero::before {
  content: '';
  position: absolute;
  top: -100px;
  left: -100px;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(139, 115, 85, 0.12) 0%, transparent 70%);
  pointer-events: none;
}

.hero::after {
  content: '';
  position: absolute;
  bottom: -120px;
  right: -80px;
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(92, 184, 92, 0.08) 0%, transparent 70%);
  pointer-events: none;
  /* 背景图铺满时不再叠加装饰光斑，避免出现可见色块 */
  display: none;
}

.hero__kicker {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
  font-size: var(--text-caption);
  letter-spacing: 0.24em;
  color: rgba(255, 255, 255, 0.82);
}

.hero__kicker::before,
.hero__kicker::after {
  content: '';
  width: 28px;
  height: 1px;
  background: rgba(255, 255, 255, 0.4);
}

.hero__title {
  font-family: var(--font-display);
  font-size: var(--text-display);
  font-weight: 700;
  line-height: 1.2;
  color: var(--color-text-inverse);
  margin: 0 0 18px;
  text-shadow: 0 2px 24px rgba(24, 18, 12, 0.45);
}

/* 两行式标题：第二行落暖金，形成"一白一金"的双色层次 */
.hero__title .reveal-text {
  display: block;
}

.hero__title-accent {
  color: var(--color-tea-yellow);
}

.hero__subtitle {
  font-size: var(--text-h3);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  opacity: 1;
  margin: 0 auto 40px;
  max-width: 600px;
  text-shadow: 0 1px 12px rgba(24, 18, 12, 0.55);
}

/* 滚动提示：细线呼吸，减少动态效果时静止 */
.hero__cue {
  position: absolute;
  left: 50%;
  bottom: 32px;
  z-index: 1;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  font-size: var(--text-caption);
  letter-spacing: 0.18em;
  color: rgba(255, 255, 255, 0.78);
  text-shadow: 0 1px 8px rgba(24, 18, 12, 0.6);
}

.hero__cue-line {
  width: 1px;
  height: 44px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.7), transparent);
  transform-origin: top;
  animation: hero-cue 2.4s var(--motion-ease) infinite;
}

@keyframes hero-cue {
  0%,
  100% {
    opacity: 0.35;
    transform: scaleY(0.7);
  }
  50% {
    opacity: 1;
    transform: scaleY(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero__cue-line {
    animation: none;
  }
}

.hero__search {
  position: relative;
  width: 100%;
  max-width: 560px;
  margin: 0 auto;
}

/* ≥768px 由页头搜索框承担搜索入口，避免同屏出现两个搜索框；
   <768px 页头搜索被隐藏，Hero 搜索保留 */
@media (min-width: 768px) {
  .hero__search {
    display: none;
  }
}

.hero__search-input {
  width: 100%;
  height: 56px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  padding: 0 24px 0 56px;
  font-size: var(--text-body);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-hero);
  outline: none;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.hero__search-input:focus {
  border-color: var(--color-primary);
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.12),
    0 0 0 3px rgba(139, 115, 85, 0.12);
}

.hero__search-icon {
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.hero__search-suggest {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 8px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-dropdown);
  overflow: hidden;
  z-index: 20;
  text-align: left;
}

.hero__search-hint {
  padding: 16px 20px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-small);
}

.hero__search-suggest-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 20px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.hero__search-suggest-item:hover {
  background: var(--color-bg-muted);
}

.hero__search-suggest-item__thumb {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  flex-shrink: 0;
  background: var(--color-bg-muted);
}

.hero__search-suggest-item__thumb--empty {
  display: block;
}

.hero__search-suggest-item__info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.hero__search-suggest-item__name {
  font-size: var(--text-small);
  font-weight: 500;
  color: var(--color-text-primary);
}

.hero__search-suggest-item__origin {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

/* 统计带 */
.stats {
  padding: 28px 0 4px;
}

.stats__inner {
  display: flex;
  align-items: baseline;
  justify-content: center;
  flex-wrap: wrap;
  gap: 32px;
}

.stats__item {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
}

.stats__value {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  line-height: 1.2;
  color: var(--color-primary-dark);
}

.stats__label {
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.stats__divider {
  width: 1px;
  height: 16px;
  background: var(--color-border-dark);
  align-self: center;
}

@media (max-width: 639px) {
  .stats__inner {
    gap: 20px;
  }
  .stats__divider {
    display: none;
  }
  .stats__value {
    font-size: var(--text-h3);
  }
}

/* 引导入口 */
.guides {
  padding: 36px 0 0;
}

.guides__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.guide-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px 20px 28px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: transparent;
  transition:
    border-color 0.2s,
    background-color 0.2s;
}

.guide-card:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-surface);
}

.guide-card__index {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
}

.guide-card__title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--color-text-primary);
}

.guide-card__desc {
  font-size: var(--text-small);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.guide-card__arrow {
  position: absolute;
  right: 20px;
  bottom: 20px;
  color: var(--color-primary);
  opacity: 0;
  transform: translateX(-4px);
  transition:
    opacity 0.2s,
    transform 0.2s;
}

.guide-card:hover .guide-card__arrow {
  opacity: 1;
  transform: translateX(0);
}

@media (max-width: 767px) {
  .guides {
    padding-top: 24px;
  }
  .guides__grid {
    grid-template-columns: 1fr;
  }
}

/* 七大茶类 */
.categories {
  padding: 48px 0;
}

.section-title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: center;
  margin: 0 0 8px;
}

/* 区块小标：宽字距英文 + 两侧发丝线，替代原来的 emoji 前缀 */
.section-kicker {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 12px;
  font-size: var(--text-caption);
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.section-kicker::before,
.section-kicker::after {
  content: '';
  width: 32px;
  height: 1px;
  background: var(--color-border-dark);
}

.section-kicker--start {
  justify-content: flex-start;
  margin-bottom: 6px;
}

.section-kicker--start::before,
.section-kicker--start::after {
  display: none;
}

.section-subtitle {
  font-size: var(--text-small);
  color: var(--color-text-muted);
  text-align: center;
  margin: 0 0 32px;
}

.categories__grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 16px;
}

.category-card-host {
  display: flex;
}

.category-card {
  position: relative;
  flex: 1;
  padding: 28px 16px;
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  text-align: center;
  transition:
    transform 0.2s,
    box-shadow 0.2s,
    border-color 0.2s;
  overflow: hidden;
}

.category-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--cat-color, var(--color-primary));
  opacity: 0;
  transition: opacity 0.2s;
}

.category-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-card);
  border-color: var(--cat-color, var(--color-primary));
}

.category-card:hover::before {
  opacity: 1;
}

.category-card__swatch {
  display: block;
  width: 40px;
  height: 40px;
  margin: 0 auto 14px;
  border-radius: var(--radius-full);
  background: var(--cat-color, var(--color-primary));
  box-shadow: inset 0 0 0 1px var(--color-border);
  transition:
    transform 0.2s,
    opacity 0.2s;
}

.category-card:hover .category-card__swatch {
  transform: scale(1.12);
}

.category-card__en {
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.category-card__name {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.category-card__count {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

/* 通用区块 */
.section {
  padding: 56px 0;
}

.section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 24px;
}

.section-header__main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.section-header__title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.section-header__action {
  font-size: var(--text-small);
  color: var(--color-primary);
}

.hot-loading {
  padding: 32px 0;
  color: var(--color-text-muted);
  font-size: var(--text-small);
}

/* 茶知识 · 小贴士（S7） */
.tips-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.tip-host {
  display: flex;
}

.tip-preview {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  padding: 24px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition:
    transform 0.2s,
    box-shadow 0.2s,
    border-color 0.2s;
}

.tip-preview:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-card);
  border-color: var(--color-primary);
}

.tip-preview__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tip-preview__tea {
  font-family: var(--font-display);
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-text-primary);
}

.tip-preview__summary {
  flex: 1;
  margin: 0;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.tip-preview__more {
  font-size: var(--text-caption);
  color: var(--color-primary);
}

@media (max-width: 767px) {
  .tips-grid {
    grid-template-columns: 1fr;
  }
}

/* 热门轨道 */
.hot-scroll {
  position: relative;
}

.hot-scroll__track {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  scroll-behavior: smooth;
  padding-bottom: 8px;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-dark) transparent;
}

.hot-scroll__track::-webkit-scrollbar {
  height: 6px;
}

.hot-scroll__track::-webkit-scrollbar-thumb {
  background: var(--color-border-dark);
  border-radius: var(--radius-full);
}

.hot-scroll__track::-webkit-scrollbar-track {
  background: transparent;
}

:deep(.hot-card) {
  flex: 0 0 200px;
}

.hot-scroll__arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  transition:
    background 0.2s,
    color 0.2s;
  z-index: 5;
}

.hot-scroll__arrow:hover {
  background: var(--color-bg-muted);
  color: var(--color-primary);
}

.hot-scroll__arrow--left {
  left: -8px;
}

.hot-scroll__arrow--right {
  right: -8px;
}

/* 随机发现 */
.random {
  background: var(--color-bg-muted);
  border-radius: var(--radius-xl);
  padding: 40px;
}

.random__body {
  display: flex;
  align-items: center;
  gap: 40px;
}

.random-card-host {
  flex: 0 0 320px;
}

.card-random {
  position: relative;
  display: block;
  width: 100%;
  background: var(--color-bg-surface);
  border-radius: var(--radius-xl);
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.card-random:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.card-random--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 260px;
  color: var(--color-text-muted);
  font-size: var(--text-small);
  padding: 24px;
}

.card-random__img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block;
  background: var(--color-bg-muted);
}

.card-random__img--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.card-random__img--placeholder svg {
  width: 40px;
  height: 40px;
  opacity: 0.5;
}

.card-random__body {
  padding: 20px;
}

.card-random__name {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 8px;
}

.card-random__tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.card-random__fav {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.card-random__brew {
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.card-random__brew span {
  display: inline-block;
  margin-right: 12px;
}

.random__desc {
  flex: 1;
}

.random__desc h3 {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  color: var(--color-text-primary);
  margin: 0 0 8px;
}

.random__desc p {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  margin: 0 0 20px;
  line-height: 1.7;
}

.random__shuffle-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border-radius: var(--radius-full);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  font-size: var(--text-body);
  font-weight: 500;
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s;
}

.random__shuffle-btn:hover:not(:disabled) {
  background: var(--color-primary);
  color: var(--color-bg-surface);
}

.random__shuffle-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.random__shuffle-btn svg {
  transition: transform 0.4s ease;
}

.random__shuffle-btn.spinning svg {
  transform: rotate(180deg);
}

@media (max-width: 1199px) {
  .categories__grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 767px) {
  .categories__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 767px) {
  .hero {
    padding: 60px 0;
  }
  .hero__title {
    font-size: 28px;
  }
  .hero__subtitle {
    font-size: var(--text-body);
  }
  .hero__search-input {
    height: 48px;
  }
  .random__body {
    flex-direction: column;
    gap: 24px;
  }
  .random-card-host {
    flex: 1;
    width: 100%;
  }
  .card-random {
    width: 100%;
  }
}

@media (max-width: 639px) {
  .categories__grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .hot-scroll__arrow {
    display: none;
  }
  :deep(.hot-card) {
    flex: 0 0 160px;
  }
  .random {
    padding: 24px;
  }
}
</style>
