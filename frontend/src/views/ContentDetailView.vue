<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import { getContentDetail, getContentTypes } from '@/api/contents'
import type { ContentItem, ContentTypeCode, ContentTypeItem } from '@/types'

const route = useRoute()

const typeCode = computed<ContentTypeCode>(
  () => (route.params.code as ContentTypeCode) ?? 'teaware',
)
const itemId = computed(() => Number(route.params.id))

const item = ref<ContentItem | null>(null)
const types = ref<ContentTypeItem[]>([])
const loading = ref(true)
const notFound = ref(false)

function isStr(v: unknown): v is string {
  return typeof v === 'string' && v.length > 0
}

async function load() {
  loading.value = true
  notFound.value = false
  try {
    types.value = await getContentTypes()
    item.value = await getContentDetail(itemId.value)
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err?.response?.status === 404) {
      notFound.value = true
    } else {
      notFound.value = true
    }
  } finally {
    loading.value = false
  }
}

const currentType = computed(() => types.value.find((t) => t.code === typeCode.value) ?? null)

/** 正文按空行切块，「## 」开头渲染为小标题，其余为段落 */
const bodyBlocks = computed(() => {
  const raw = item.value?.body
  if (!raw) return []
  return raw
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) =>
      block.startsWith('## ')
        ? { type: 'heading' as const, text: block.slice(3).trim() }
        : { type: 'paragraph' as const, text: block },
    )
})

onMounted(load)

// 同一路由记录下切换 id（如上一页/下一页、相关推荐）时实例被复用，需重新加载
watch(
  () => route.params.id,
  (id) => {
    if (id) void load()
  },
)
</script>

<template>
  <div class="content-detail-page">
    <AppHeader />

    <main class="content-detail-page__main">
      <!-- 面包屑 -->
      <nav class="breadcrumb">
        <RouterLink to="/">首页</RouterLink>
        <span class="sep">›</span>
        <RouterLink :to="`/contents/${typeCode}`"
          >茶文化 · {{ currentType?.name ?? typeCode }}</RouterLink
        >
        <span class="sep">›</span>
        <span class="current">{{ item?.title ?? '详情' }}</span>
      </nav>

      <!-- 加载中 -->
      <div v-if="loading" class="loading">加载中...</div>

      <!-- 404 -->
      <div v-else-if="notFound || !item" class="not-found">
        <p>内容不存在或已下架</p>
        <RouterLink to="/" class="back-link">返回首页</RouterLink>
      </div>

      <!-- 详情 -->
      <article v-else class="detail">
        <!-- 封面图 -->
        <div v-if="item.cover_image" class="cover">
          <img :src="item.cover_image" :alt="item.title" />
        </div>

        <header class="detail__header">
          <p class="page-kicker">Article</p>
          <h1 class="detail__title">{{ item.title }}</h1>
          <p v-if="item.summary" class="detail__summary">{{ item.summary }}</p>
        </header>

        <!-- 板块特有字段（meta JSON） -->
        <section v-if="item.meta && Object.keys(item.meta).length > 0" class="detail__meta">
          <!-- teaware: material / volume / category -->
          <template v-if="typeCode === 'teaware'">
            <dl v-if="isStr(item.meta.material)" class="meta-row">
              <dt>材质</dt>
              <dd>{{ item.meta.material as string }}</dd>
            </dl>
            <dl v-if="isStr(item.meta.volume)" class="meta-row">
              <dt>容量</dt>
              <dd>{{ item.meta.volume as string }}</dd>
            </dl>
            <dl v-if="isStr(item.meta.category)" class="meta-row">
              <dt>分类</dt>
              <dd>{{ item.meta.category as string }}</dd>
            </dl>
          </template>

          <!-- origin: province / region -->
          <template v-if="typeCode === 'origin'">
            <dl v-if="isStr(item.meta.province)" class="meta-row">
              <dt>省份</dt>
              <dd>{{ item.meta.province as string }}</dd>
            </dl>
            <dl v-if="isStr(item.meta.region)" class="meta-row">
              <dt>产区</dt>
              <dd>{{ item.meta.region as string }}</dd>
            </dl>
          </template>

          <!-- culture: era / tags -->
          <template v-if="typeCode === 'culture'">
            <dl v-if="isStr(item.meta.era)" class="meta-row">
              <dt>时期</dt>
              <dd>{{ item.meta.era as string }}</dd>
            </dl>
            <dl
              v-if="Array.isArray(item.meta.tags) && (item.meta.tags as unknown[]).length"
              class="meta-row"
            >
              <dt>标签</dt>
              <dd>
                <span v-for="tag in item.meta.tags as string[]" :key="tag" class="tag">{{
                  tag
                }}</span>
              </dd>
            </dl>
          </template>

          <!-- brand: founded / brand_origin / website -->
          <template v-if="typeCode === 'brand'">
            <dl v-if="item.meta.founded" class="meta-row">
              <dt>创立年份</dt>
              <dd>{{ item.meta.founded }}</dd>
            </dl>
            <dl v-if="isStr(item.meta.brand_origin)" class="meta-row">
              <dt>产地</dt>
              <dd>{{ item.meta.brand_origin as string }}</dd>
            </dl>
            <dl v-if="isStr(item.meta.website)" class="meta-row">
              <dt>官网</dt>
              <dd>
                <a :href="item.meta.website as string" target="_blank" rel="noopener">{{
                  item.meta.website as string
                }}</a>
              </dd>
            </dl>
          </template>

          <!-- knowledge: subtype / difficulty -->
          <template v-if="typeCode === 'knowledge'">
            <dl v-if="isStr(item.meta.subtype)" class="meta-row">
              <dt>分类</dt>
              <dd>{{ item.meta.subtype === 'standard' ? '茶叶标准' : '冲泡知识' }}</dd>
            </dl>
            <dl v-if="isStr(item.meta.difficulty)" class="meta-row">
              <dt>难度</dt>
              <dd>
                {{
                  item.meta.difficulty === 'beginner'
                    ? '入门'
                    : item.meta.difficulty === 'intermediate'
                      ? '进阶'
                      : '高级'
                }}
              </dd>
            </dl>
          </template>
        </section>

        <!-- 正文 -->
        <section v-if="bodyBlocks.length" class="detail__body">
          <template v-for="(block, index) in bodyBlocks" :key="index">
            <h2 v-if="block.type === 'heading'" class="detail__subheading">{{ block.text }}</h2>
            <p v-else>{{ block.text }}</p>
          </template>
        </section>

        <!-- 返回 -->
        <footer class="detail__footer">
          <RouterLink :to="`/contents/${typeCode}`" class="back-link">
            ← 返回{{ currentType?.name ?? '列表' }}
          </RouterLink>
        </footer>
      </article>
    </main>

    <AppFooter />
  </div>
</template>

<style scoped>
.content-detail-page__main {
  max-width: 720px;
  margin: 88px auto 0;
  padding: 0 32px 80px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  margin-bottom: 32px;
}
.breadcrumb a {
  color: var(--color-text-secondary);
}
.breadcrumb a:hover {
  color: var(--color-primary);
}
.breadcrumb .sep {
  color: var(--color-border);
}
.breadcrumb .current {
  color: var(--color-text-primary);
}

.loading,
.not-found {
  text-align: center;
  padding: 80px 0;
  color: var(--color-text-muted);
}
.not-found p {
  margin-bottom: 16px;
}
.back-link {
  color: var(--color-primary);
  font-size: var(--text-small);
}

.cover {
  margin-bottom: 40px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-bg-muted);
}
.cover img {
  width: 100%;
  display: block;
  max-height: 400px;
  object-fit: cover;
}

.detail__header {
  border-bottom: 1px solid var(--color-border-light);
  padding-bottom: 24px;
  margin-bottom: 32px;
}
.detail__title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  color: var(--color-primary-dark);
  margin: 0 0 12px;
  line-height: 1.3;
}
.detail__summary {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin: 0;
}

.detail__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 40px;
  margin-bottom: 40px;
}
.meta-row {
  display: flex;
  gap: 12px;
  margin: 0;
  font-size: var(--text-body);
}
.meta-row dt {
  color: var(--color-text-muted);
  min-width: 70px;
}
.meta-row dd {
  color: var(--color-text-primary);
  margin: 0;
}
.meta-row .tag {
  display: inline-block;
  padding: 2px 10px;
  margin-right: 6px;
  background: var(--color-bg-muted);
  border-radius: var(--radius-full);
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}

.detail__body {
  font-size: var(--text-body);
  line-height: 2;
  color: var(--color-text-primary);
}
.detail__body p {
  margin: 0 0 20px;
  white-space: pre-wrap;
}
.detail__subheading {
  font-family: var(--font-display);
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-primary-dark);
  line-height: 1.6;
  margin: 36px 0 12px;
}
.detail__subheading:first-child {
  margin-top: 0;
}

.detail__footer {
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border-light);
}

@media (max-width: 767px) {
  .content-detail-page__main {
    padding: 0 16px 40px;
    margin-top: 76px;
  }
  .detail__title {
    font-size: var(--text-h2);
  }
  .detail__meta {
    flex-direction: column;
    gap: 8px;
  }
}
</style>
