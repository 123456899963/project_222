<script setup lang="ts">
/**
 * 投稿页（S10 补充新茶 / S11 投稿科普）
 * —— 提交后进入待审核状态，审核结果在「我的提交」查看
 * —— 不提供富文本与图片上传（X7）；主图仅接受已有 URL / 上传路径
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import { submitContribution } from '@/api/contributions'
import { getTeaList } from '@/api/teas'
import { useToastStore } from '@/stores/toast'
import { CATEGORY_LABELS, TEA_CATEGORIES, TEA_FERMENTATIONS, TEA_SEASONS } from '@/utils/teaQuery'
import type { ContributionCreatePayload, ContributionType, TeaCategory, TeaListItem } from '@/types'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const tab = ref<ContributionType>(route.query.type === 'article' ? 'article' : 'new_tea')
const submitting = ref(false)

const teaForm = reactive({
  name: '',
  category: 'green' as TeaCategory,
  origin: '',
  season: '',
  fermentation: '',
  price_range: '',
  representative_variety: '',
  shape_desc: '',
  soup_desc: '',
  aroma_desc: '',
  taste_desc: '',
  water_temp: 85,
  tea_amount: 3,
  brew_time: 90,
  main_image_url: '',
  tips_history: '',
  tips_suitable: '',
  tips_misconception: '',
  tips_official_note: '',
})

const articleForm = reactive({
  target_tea_id: route.query.tea_id ? Number(route.query.tea_id) : (null as number | null),
  title: '',
  content: '',
})

const teaOptions = ref<TeaListItem[]>([])

const contentCount = computed(() => articleForm.content.trim().length)
const canSubmitArticle = computed(
  () => !!articleForm.target_tea_id && contentCount.value >= 3 && contentCount.value <= 500,
)

function textOrNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function numberOrNull(value: number | string): number | null {
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

function validateTeaForm(): string | null {
  if (!teaForm.name.trim()) return '请填写茶品名称'
  if (!teaForm.origin.trim()) return '请填写产地'
  for (const [key, label] of [
    ['shape_desc', '外形描述'],
    ['soup_desc', '汤色描述'],
    ['aroma_desc', '香气描述'],
    ['taste_desc', '滋味描述'],
  ] as const) {
    if (!teaForm[key].trim()) return `请填写${label}`
  }
  if (!(teaForm.water_temp >= 70 && teaForm.water_temp <= 100)) return '水温需在 70–100℃'
  if (!(teaForm.tea_amount > 0)) return '投茶量需大于 0'
  if (!(teaForm.brew_time > 0)) return '浸泡时间需大于 0'
  return null
}

async function submitTea() {
  const error = validateTeaForm()
  if (error) {
    toast.warn(error)
    return
  }
  const payload: ContributionCreatePayload = {
    type: 'new_tea',
    tea: {
      name: teaForm.name.trim(),
      category: teaForm.category,
      origin: teaForm.origin.trim(),
      season: textOrNull(teaForm.season),
      fermentation: textOrNull(teaForm.fermentation),
      price_range: textOrNull(teaForm.price_range),
      representative_variety: textOrNull(teaForm.representative_variety),
      shape_desc: teaForm.shape_desc.trim(),
      soup_desc: teaForm.soup_desc.trim(),
      aroma_desc: teaForm.aroma_desc.trim(),
      taste_desc: teaForm.taste_desc.trim(),
      water_temp: numberOrNull(teaForm.water_temp) as number,
      tea_amount: numberOrNull(teaForm.tea_amount) as number,
      brew_time: numberOrNull(teaForm.brew_time) as number,
      main_image_url: textOrNull(teaForm.main_image_url),
      tips_history: textOrNull(teaForm.tips_history),
      tips_suitable: textOrNull(teaForm.tips_suitable),
      tips_misconception: textOrNull(teaForm.tips_misconception),
      tips_official_note: textOrNull(teaForm.tips_official_note),
    },
  }
  await doSubmit(payload)
}

async function submitArticle() {
  if (!articleForm.target_tea_id) {
    toast.warn('请选择要补充科普的茶品')
    return
  }
  if (contentCount.value < 3 || contentCount.value > 500) {
    toast.warn('科普内容需为 3–500 字')
    return
  }
  await doSubmit({
    type: 'article',
    target_tea_id: articleForm.target_tea_id,
    title: textOrNull(articleForm.title),
    content: articleForm.content.trim(),
  })
}

async function doSubmit(payload: ContributionCreatePayload) {
  submitting.value = true
  try {
    await submitContribution(payload)
    toast.success('提交成功，等待管理员审核')
    router.push({ name: 'my-contributions' })
  } finally {
    submitting.value = false
  }
}

async function loadTeaOptions() {
  const res = await getTeaList({ page_size: 50 })
  teaOptions.value = res.data?.items ?? []
}

watch(tab, (value) => {
  if (value === 'article' && teaOptions.value.length === 0) void loadTeaOptions()
})

onMounted(() => {
  if (tab.value === 'article') void loadTeaOptions()
})
</script>

<template>
  <AppHeader />

  <main class="contribute-page">
    <div class="container">
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">投稿</span>
      </nav>

      <header class="contribute-hero">
        <div class="contribute-hero__main">
          <p class="page-kicker">Contribute</p>
          <h1 class="contribute-hero__title">让图鉴更丰富</h1>
          <p class="contribute-hero__desc">
            补充一款尚未收录的茶，或为已有茶品撰写科普。提交后由管理员审核，通过即公开展示。
          </p>
        </div>
        <RouterLink class="btn btn--ghost" :to="{ name: 'my-contributions' }">
          查看我的提交
        </RouterLink>
      </header>

      <div class="tabs" role="tablist">
        <button
          type="button"
          class="tabs__item"
          :class="{ 'tabs__item--active': tab === 'new_tea' }"
          role="tab"
          :aria-selected="tab === 'new_tea'"
          @click="tab = 'new_tea'"
        >
          补充新茶
        </button>
        <button
          type="button"
          class="tabs__item"
          :class="{ 'tabs__item--active': tab === 'article' }"
          role="tab"
          :aria-selected="tab === 'article'"
          @click="tab = 'article'"
        >
          投稿科普
        </button>
      </div>

      <!-- 补充新茶 -->
      <form v-if="tab === 'new_tea'" class="fcard" @submit.prevent="submitTea">
        <h2 class="fcard__title">基础信息</h2>
        <div class="grid grid--3">
          <label class="field">
            <span class="field__label">茶品名称 *</span>
            <input v-model="teaForm.name" class="field__input" maxlength="100" required />
          </label>
          <label class="field">
            <span class="field__label">七大茶类 *</span>
            <select v-model="teaForm.category" class="field__input">
              <option v-for="category in TEA_CATEGORIES" :key="category" :value="category">
                {{ CATEGORY_LABELS[category] }}
              </option>
            </select>
          </label>
          <label class="field">
            <span class="field__label">产地 *</span>
            <input
              v-model="teaForm.origin"
              class="field__input"
              maxlength="200"
              placeholder="如：浙江 杭州 西湖"
              required
            />
          </label>
        </div>

        <div class="grid grid--3">
          <label class="field">
            <span class="field__label">采摘季节</span>
            <select v-model="teaForm.season" class="field__input">
              <option value="">不填</option>
              <option v-for="season in TEA_SEASONS" :key="season" :value="season">
                {{ season }}
              </option>
            </select>
          </label>
          <label class="field">
            <span class="field__label">发酵程度</span>
            <select v-model="teaForm.fermentation" class="field__input">
              <option value="">不填</option>
              <option v-for="item in TEA_FERMENTATIONS" :key="item" :value="item">
                {{ item }}
              </option>
            </select>
          </label>
          <label class="field">
            <span class="field__label">价格区间</span>
            <input
              v-model="teaForm.price_range"
              class="field__input"
              maxlength="32"
              placeholder="如：300-800元/斤"
            />
          </label>
        </div>

        <label class="field">
          <span class="field__label">代表品类</span>
          <input v-model="teaForm.representative_variety" class="field__input" maxlength="100" />
        </label>

        <h2 class="fcard__title">感官特征</h2>
        <div class="grid grid--2">
          <label class="field">
            <span class="field__label">外形描述 *</span>
            <textarea
              v-model="teaForm.shape_desc"
              class="field__input"
              rows="3"
              required
            ></textarea>
          </label>
          <label class="field">
            <span class="field__label">汤色描述 *</span>
            <textarea v-model="teaForm.soup_desc" class="field__input" rows="3" required></textarea>
          </label>
          <label class="field">
            <span class="field__label">香气描述 *</span>
            <textarea
              v-model="teaForm.aroma_desc"
              class="field__input"
              rows="3"
              required
            ></textarea>
          </label>
          <label class="field">
            <span class="field__label">滋味描述 *</span>
            <textarea
              v-model="teaForm.taste_desc"
              class="field__input"
              rows="3"
              required
            ></textarea>
          </label>
        </div>

        <h2 class="fcard__title">冲泡参考</h2>
        <div class="grid grid--3">
          <label class="field">
            <span class="field__label">水温（℃）*</span>
            <input
              v-model.number="teaForm.water_temp"
              class="field__input"
              type="number"
              min="70"
              max="100"
              step="0.1"
              required
            />
          </label>
          <label class="field">
            <span class="field__label">投茶量（g）*</span>
            <input
              v-model.number="teaForm.tea_amount"
              class="field__input"
              type="number"
              min="0.1"
              step="0.1"
              required
            />
          </label>
          <label class="field">
            <span class="field__label">浸泡时间（s）*</span>
            <input
              v-model.number="teaForm.brew_time"
              class="field__input"
              type="number"
              min="1"
              step="1"
              required
            />
          </label>
        </div>

        <label class="field">
          <span class="field__label">主图 URL（选填）</span>
          <input
            v-model="teaForm.main_image_url"
            class="field__input"
            maxlength="500"
            placeholder="https://… 或 /uploads/…；不开放图片上传"
          />
        </label>

        <h2 class="fcard__title">茶小知识（选填）</h2>
        <div class="grid grid--2">
          <label class="field">
            <span class="field__label">历史文化</span>
            <textarea v-model="teaForm.tips_history" class="field__input" rows="2"></textarea>
          </label>
          <label class="field">
            <span class="field__label">适合人群</span>
            <textarea v-model="teaForm.tips_suitable" class="field__input" rows="2"></textarea>
          </label>
          <label class="field">
            <span class="field__label">常见误区</span>
            <textarea v-model="teaForm.tips_misconception" class="field__input" rows="2"></textarea>
          </label>
          <label class="field">
            <span class="field__label">备注</span>
            <textarea v-model="teaForm.tips_official_note" class="field__input" rows="2"></textarea>
          </label>
        </div>

        <p class="fcard__hint">名称与茶类会先经名品映射校验；与已有茶品名称过于相似会被拦截。</p>
        <div class="fcard__actions">
          <button type="submit" class="btn btn--primary" :disabled="submitting">
            {{ submitting ? '提交中…' : '提交审核' }}
          </button>
          <RouterLink class="btn btn--ghost" :to="{ name: 'my-contributions' }">取消</RouterLink>
        </div>
      </form>

      <!-- 投稿科普 -->
      <form v-else class="fcard" @submit.prevent="submitArticle">
        <h2 class="fcard__title">科普投稿</h2>
        <label class="field">
          <span class="field__label">目标茶品 *</span>
          <select v-model.number="articleForm.target_tea_id" class="field__input" required>
            <option :value="null" disabled>请选择茶品</option>
            <option v-for="item in teaOptions" :key="item.id" :value="item.id">
              {{ item.name }}（{{ CATEGORY_LABELS[item.category] }}）
            </option>
          </select>
        </label>
        <label class="field">
          <span class="field__label">标题（选填）</span>
          <input v-model="articleForm.title" class="field__input" maxlength="50" />
        </label>
        <label class="field">
          <span class="field__label">正文 *（3–500 字）</span>
          <textarea v-model="articleForm.content" class="field__input" rows="8" required></textarea>
          <span class="field__counter">{{ contentCount }} / 500</span>
        </label>
        <p class="fcard__hint">仅支持纯文本；图片与富文本将在后续版本开放。</p>
        <div class="fcard__actions">
          <button
            type="submit"
            class="btn btn--primary"
            :disabled="submitting || !canSubmitArticle"
          >
            {{ submitting ? '提交中…' : '提交审核' }}
          </button>
          <RouterLink class="btn btn--ghost" :to="{ name: 'my-contributions' }">取消</RouterLink>
        </div>
      </form>
    </div>
  </main>

  <AppFooter />
</template>

<style scoped>
.contribute-page {
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
  .contribute-page {
    padding: 76px 0 48px;
  }
  .container {
    padding: 0 16px;
  }
}
.contribute-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}
.contribute-hero__main {
  min-width: 0;
}
.contribute-hero__title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  font-weight: 600;
  color: var(--color-primary-dark);
  margin: 0;
}
.contribute-hero__desc {
  max-width: 640px;
  margin-top: 8px;
  color: var(--color-text-secondary);
  line-height: 1.8;
}
.tabs {
  display: inline-flex;
  padding: 4px;
  margin-bottom: 20px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
}
.tabs__item {
  padding: 8px 20px;
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.tabs__item--active {
  background: var(--color-bg-surface);
  color: var(--color-primary-dark);
  box-shadow: var(--shadow-card);
}
.fcard {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 28px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}
.fcard__title {
  margin-top: 8px;
  font-size: var(--text-h3);
  color: var(--color-primary-dark);
}
.fcard__hint {
  color: var(--color-text-muted);
  font-size: var(--text-small);
}
.fcard__actions {
  display: flex;
  gap: 12px;
}
.grid {
  display: grid;
  gap: 16px;
}
.grid--2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.grid--3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}
.field__input {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  font: inherit;
  resize: vertical;
}
.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.field__counter {
  align-self: flex-end;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}
@media (max-width: 900px) {
  .grid--2,
  .grid--3 {
    grid-template-columns: 1fr;
  }
}
</style>
