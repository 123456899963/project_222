<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  addAdminTeaImage,
  createAdminTea,
  deleteAdminBrewingGuide,
  deleteAdminTeaImage,
  getAdminTea,
  toggleAdminTea,
  updateAdminBrewingGuide,
  updateAdminTea,
  updateAdminTips,
  uploadAdminImage,
  uploadAdminVideo,
} from '@/api/admin'
import { getTeaImages } from '@/api/teas'
import { buildBrewingDraft } from '@/utils/brewing'
import { CATEGORY_LABELS, TEA_CATEGORIES, TEA_SEASONS } from '@/utils/teaQuery'
import type {
  AdminBrewingGuidePayload,
  AdminTeaPayload,
  AdminTeaCreatePayload,
  Tea,
  TeaCategory,
  TeaMediaItem,
} from '@/types'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const teaId = computed(() => Number(route.params.id))

const FERMENTATION_OPTIONS = ['不发酵', '微发酵', '半发酵', '全发酵', '后发酵']

const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const uploadingVideo = ref(false)
const uploadingGallery = ref(false)
const gallery = ref<TeaMediaItem[]>([])
const formRef = ref<FormInstance>()

const teaForm = reactive({
  name: '',
  category: 'green' as TeaCategory,
  origin: '',
  season: '' as string,
  fermentation: '' as string,
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
  video_url: '',
  video_duration: null as number | null,
  is_active: true,
  tips_history: '',
  tips_suitable: '',
  tips_misconception: '',
  tips_official_note: '',
})

/** 冲泡教程（ADR-0005）：与茶品信息一起保存，留空且已有教程时删除 */
const guide = reactive({
  exists: false,
  intro: '',
  caution: '',
  steps: [] as Array<{ title: string; detail: string; tip: string }>,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入茶名（1-100 字）', trigger: 'blur' }],
  category: [{ required: true, message: '请选择茶类', trigger: 'change' }],
  origin: [{ required: true, message: '请输入产地', trigger: 'blur' }],
  shape_desc: [{ required: true, message: '请填写外形描述', trigger: 'blur' }],
  soup_desc: [{ required: true, message: '请填写汤色描述', trigger: 'blur' }],
  aroma_desc: [{ required: true, message: '请填写香气描述', trigger: 'blur' }],
  taste_desc: [{ required: true, message: '请填写滋味描述', trigger: 'blur' }],
  water_temp: [{ required: true, message: '请填写水温', trigger: 'change' }],
  tea_amount: [{ required: true, message: '请填写投茶量', trigger: 'change' }],
  brew_time: [{ required: true, message: '请填写冲泡时间', trigger: 'change' }],
  main_image_url: [{ required: true, message: '请上传或填写主图地址', trigger: 'blur' }],
}

function nullableText(value: string): string | null {
  const trimmed = value.trim()
  return trimmed || null
}

function fillForm(tea: Tea) {
  teaForm.name = tea.name
  teaForm.category = tea.category
  teaForm.origin = tea.origin
  teaForm.season = tea.season ?? ''
  teaForm.fermentation = tea.fermentation ?? ''
  teaForm.price_range = tea.price_range ?? ''
  teaForm.representative_variety = tea.representative_variety ?? ''
  teaForm.shape_desc = tea.shape_desc
  teaForm.soup_desc = tea.soup_desc
  teaForm.aroma_desc = tea.aroma_desc
  teaForm.taste_desc = tea.taste_desc
  teaForm.water_temp = tea.water_temp ?? 85
  teaForm.tea_amount = tea.tea_amount ?? 3
  teaForm.brew_time = tea.brew_time ?? 90
  teaForm.main_image_url = tea.main_image_url ?? ''
  teaForm.video_url = tea.video_url ?? ''
  teaForm.video_duration = tea.video_duration ?? null
  teaForm.is_active = tea.is_active
  teaForm.tips_history = tea.tips_history ?? ''
  teaForm.tips_suitable = tea.tips_suitable ?? ''
  teaForm.tips_misconception = tea.tips_misconception ?? ''
  teaForm.tips_official_note = tea.tips_official_note ?? ''

  const brewing = tea.brewing_guide
  guide.exists = Boolean(brewing)
  guide.intro = brewing?.intro ?? ''
  guide.caution = brewing?.caution ?? ''
  guide.steps = (brewing?.steps ?? []).map((step) => ({
    title: step.title,
    detail: step.detail,
    tip: step.tip ?? '',
  }))
}

async function loadDetail() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const res = await getAdminTea(teaId.value)
    fillForm(res.data)
    await loadGallery()
  } finally {
    loading.value = false
  }
}

/** 图片集（S4）：仅编辑态可管理，新增态需先保存 */
async function loadGallery() {
  if (!isEdit.value) return
  const res = await getTeaImages(teaId.value)
  gallery.value = res.data
}

function buildPayload(): AdminTeaPayload {
  return {
    name: teaForm.name.trim(),
    category: teaForm.category,
    origin: teaForm.origin.trim(),
    season: nullableText(teaForm.season),
    fermentation: nullableText(teaForm.fermentation),
    price_range: nullableText(teaForm.price_range),
    representative_variety: nullableText(teaForm.representative_variety),
    shape_desc: teaForm.shape_desc.trim(),
    soup_desc: teaForm.soup_desc.trim(),
    aroma_desc: teaForm.aroma_desc.trim(),
    taste_desc: teaForm.taste_desc.trim(),
    water_temp: teaForm.water_temp,
    tea_amount: teaForm.tea_amount,
    brew_time: teaForm.brew_time,
    main_image_url: teaForm.main_image_url.trim(),
    video_url: nullableText(teaForm.video_url),
    video_duration: teaForm.video_duration,
  }
}

function buildTips() {
  return {
    tips_history: nullableText(teaForm.tips_history),
    tips_suitable: nullableText(teaForm.tips_suitable),
    tips_misconception: nullableText(teaForm.tips_misconception),
    tips_official_note: nullableText(teaForm.tips_official_note),
  }
}

/** 教程保存前的本地校验：0 步表示删除，1–2 步不合法，3–8 步且标题/说明必填 */
function validateGuide(): string | null {
  const filled = guide.steps.filter(
    (step) => step.title.trim() || step.detail.trim() || step.tip.trim(),
  )
  if (filled.length === 0) return null
  if (filled.length < 3) return '冲泡教程至少需要 3 步，或点击「删除教程」清空'
  if (filled.length > 8) return '冲泡教程最多 8 步'
  if (filled.some((step) => !step.title.trim() || !step.detail.trim())) {
    return '每一步都需要填写步骤标题和动作说明'
  }
  return null
}

function buildGuidePayload(): AdminBrewingGuidePayload {
  return {
    intro: nullableText(guide.intro),
    caution: nullableText(guide.caution),
    steps: guide.steps
      .filter((step) => step.title.trim() && step.detail.trim())
      .map((step) => ({
        title: step.title.trim(),
        detail: step.detail.trim(),
        tip: nullableText(step.tip),
      })),
  }
}

/** 保存教程：空教程时删除已有记录，保证前台退回三格速查卡 */
async function saveGuide(id: number) {
  const payload = buildGuidePayload()
  if (payload.steps.length === 0) {
    if (guide.exists) {
      await deleteAdminBrewingGuide(id)
      guide.exists = false
    }
    return
  }
  await updateAdminBrewingGuide(id, payload)
  guide.exists = true
}

function addGuideStep() {
  if (guide.steps.length >= 8) return
  guide.steps.push({ title: '', detail: '', tip: '' })
}

function removeGuideStep(index: number) {
  if (guide.steps.length <= 3) return
  guide.steps.splice(index, 1)
}

function moveGuideStep(index: number, offset: number) {
  const target = index + offset
  if (target < 0 || target >= guide.steps.length) return
  const [step] = guide.steps.splice(index, 1)
  guide.steps.splice(target, 0, step)
}

/** 按茶类 + 本茶参数生成 6 步草稿，管理员再逐条润色 */
function applyDraftTemplate() {
  const draft = buildBrewingDraft({
    category: teaForm.category,
    water_temp: teaForm.water_temp,
    tea_amount: teaForm.tea_amount,
    brew_time: teaForm.brew_time,
  })
  guide.intro = draft.intro ?? ''
  guide.caution = draft.caution ?? ''
  guide.steps = draft.steps.map((step) => ({
    title: step.title,
    detail: step.detail,
    tip: step.tip ?? '',
  }))
  ElMessage.info('已套用茶类模板，请检查后保存')
}

async function clearGuide() {
  if (!isEdit.value) {
    guide.intro = ''
    guide.caution = ''
    guide.steps = []
    return
  }
  try {
    await ElMessageBox.confirm('删除后前台将只显示三格冲泡参数，确定删除教程吗？', '删除教程', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await deleteAdminBrewingGuide(teaId.value)
  guide.exists = false
  guide.intro = ''
  guide.caution = ''
  guide.steps = []
  ElMessage.success('教程已删除')
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const guideError = validateGuide()
  if (guideError) {
    ElMessage.error(guideError)
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await updateAdminTea(teaId.value, buildPayload())
      await updateAdminTips(teaId.value, buildTips())
      await saveGuide(teaId.value)
      ElMessage.success('茶品信息、小贴士与冲泡教程已保存')
      await loadDetail()
    } else {
      const payload: AdminTeaCreatePayload = { ...buildPayload(), ...buildTips() }
      const created = await createAdminTea(payload)
      if (buildGuidePayload().steps.length > 0) {
        await saveGuide(created.data.id)
      }
      ElMessage.success('新增茶品成功')
      router.push({ name: 'admin-teas' })
    }
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function handleToggle() {
  const direction = teaForm.is_active ? '下架' : '上架'
  try {
    await ElMessageBox.confirm(
      `确定要${direction}该茶品吗？${teaForm.is_active ? '下架后前台不再展示，收藏与分享记录保留。' : '上架后前台立即可见。'}`,
      `${direction}确认`,
      { type: 'warning', confirmButtonText: `确认${direction}`, cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const res = await toggleAdminTea(teaId.value)
  teaForm.is_active = res.data.is_active
  ElMessage.success(`已${teaForm.is_active ? '上架' : '下架'}`)
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('仅支持 JPEG / PNG / WebP 图片')
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 5 MB')
    input.value = ''
    return
  }

  uploading.value = true
  try {
    const res = await uploadAdminImage(file)
    teaForm.main_image_url = res.data.url
    ElMessage.success('图片上传成功')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function triggerFileInput() {
  document.getElementById('tea-image-input')?.click()
}

/** 视频上传（S5）：MP4/MOV ≤ 50MB、≤ 3 分钟，时长由服务端校验并回填 */
async function onVideoFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!['video/mp4', 'video/quicktime'].includes(file.type)) {
    ElMessage.error('仅支持 MP4 / MOV 视频')
    input.value = ''
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('视频大小不能超过 50 MB')
    input.value = ''
    return
  }

  uploadingVideo.value = true
  try {
    const res = await uploadAdminVideo(file)
    teaForm.video_url = res.data.url
    teaForm.video_duration = res.data.duration
    ElMessage.success('视频上传成功，保存后生效')
  } finally {
    uploadingVideo.value = false
    input.value = ''
  }
}

function triggerVideoInput() {
  document.getElementById('tea-video-input')?.click()
}

function clearVideo() {
  teaForm.video_url = ''
  teaForm.video_duration = null
}

/** 图片集追加（S4）：先走图片上传拿 URL，再关联到茶品 */
async function onGalleryFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('仅支持 JPEG / PNG / WebP 图片')
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 5 MB')
    input.value = ''
    return
  }
  if (gallery.value.length >= 9) {
    ElMessage.warning('图片集最多 9 张')
    input.value = ''
    return
  }

  uploadingGallery.value = true
  try {
    const uploaded = await uploadAdminImage(file)
    const created = await addAdminTeaImage(teaId.value, uploaded.data.url)
    gallery.value = [...gallery.value, created.data]
    ElMessage.success('已加入图片集')
  } finally {
    uploadingGallery.value = false
    input.value = ''
  }
}

function triggerGalleryInput() {
  document.getElementById('tea-gallery-input')?.click()
}

async function removeGalleryItem(item: TeaMediaItem) {
  await deleteAdminTeaImage(teaId.value, item.id)
  gallery.value = gallery.value.filter((row) => row.id !== item.id)
  ElMessage.success('已删除该图片')
}

onMounted(loadDetail)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2 class="text-h2">{{ isEdit ? '编辑茶品' : '新增茶品' }}</h2>
        <p class="text-small text-secondary">
          {{ isEdit ? 'PUT 全量保存；小贴士留空表示清空，不做审核流程。' : '保存后立即上架生效。' }}
        </p>
      </div>
      <div class="head-actions">
        <el-tag v-if="isEdit" :type="teaForm.is_active ? 'success' : 'info'">
          {{ teaForm.is_active ? '已上架' : '已下架' }}
        </el-tag>
        <el-button v-if="isEdit" type="warning" plain @click="handleToggle">
          {{ teaForm.is_active ? '下架' : '上架' }}
        </el-button>
        <el-button @click="router.push({ name: 'admin-teas' })">返回列表</el-button>
      </div>
    </div>

    <el-form ref="formRef" :model="teaForm" :rules="rules" label-width="96px" class="tea-form">
      <section class="form-section">
        <h3 class="text-h3 section-title">基本信息</h3>
        <div class="form-grid">
          <el-form-item label="茶名" prop="name">
            <el-input v-model="teaForm.name" maxlength="100" show-word-limit />
          </el-form-item>
          <el-form-item label="茶类" prop="category">
            <el-select v-model="teaForm.category" class="full-width">
              <el-option
                v-for="category in TEA_CATEGORIES"
                :key="category"
                :label="CATEGORY_LABELS[category]"
                :value="category"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="产地" prop="origin">
            <el-input
              v-model="teaForm.origin"
              maxlength="200"
              placeholder="如：浙江 杭州 西湖狮峰"
            />
          </el-form-item>
          <el-form-item label="季节">
            <el-select v-model="teaForm.season" clearable placeholder="可不填" class="full-width">
              <el-option
                v-for="season in TEA_SEASONS"
                :key="season"
                :label="season"
                :value="season"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="发酵程度">
            <el-select
              v-model="teaForm.fermentation"
              clearable
              placeholder="可不填"
              class="full-width"
            >
              <el-option
                v-for="item in FERMENTATION_OPTIONS"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="价格档位">
            <el-input
              v-model="teaForm.price_range"
              maxlength="32"
              placeholder="如：100-300元/50g"
            />
          </el-form-item>
          <el-form-item label="代表品种">
            <el-input v-model="teaForm.representative_variety" maxlength="100" />
          </el-form-item>
          <el-form-item label="主图" prop="main_image_url">
            <div class="image-field">
              <el-input
                v-model="teaForm.main_image_url"
                maxlength="500"
                placeholder="图片地址，如 /uploads/ 开头或 https 链接"
              />
              <el-button :loading="uploading" @click="triggerFileInput">上传图片</el-button>
              <input
                id="tea-image-input"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                class="file-input"
                @change="onFileChange"
              />
            </div>
            <div v-if="teaForm.main_image_url" class="image-preview">
              <img :src="teaForm.main_image_url" alt="主图预览" />
            </div>
          </el-form-item>
          <el-form-item label="视频介绍">
            <div class="image-field">
              <el-input
                v-model="teaForm.video_url"
                maxlength="500"
                placeholder="留空表示无视频；只能填本站 /uploads/ 路径"
              />
              <el-button :loading="uploadingVideo" @click="triggerVideoInput">上传视频</el-button>
              <el-button v-if="teaForm.video_url" @click="clearVideo">清除</el-button>
              <input
                id="tea-video-input"
                type="file"
                accept="video/mp4,video/quicktime"
                class="file-input"
                @change="onVideoFileChange"
              />
            </div>
            <p class="text-small text-secondary">
              MP4 / MOV，≤ 50 MB，时长 ≤ 3 分钟（服务端校验）。
              <span v-if="teaForm.video_duration">当前：{{ teaForm.video_duration }} 秒</span>
            </p>
            <div v-if="teaForm.video_url" class="video-preview">
              <video :src="teaForm.video_url" controls preload="metadata" />
            </div>
          </el-form-item>
        </div>
      </section>

      <section v-if="isEdit" class="form-section">
        <h3 class="text-h3 section-title">图片集（最多 9 张）</h3>
        <p class="text-small text-secondary">
          按添加顺序展示；删除仅解除关联，不物理删除磁盘文件。
        </p>
        <div class="gallery-grid">
          <div v-for="item in gallery" :key="item.id" class="gallery-item">
            <img :src="item.image_url" alt="图片集预览" loading="lazy" />
            <el-button type="danger" link @click="removeGalleryItem(item)">删除</el-button>
          </div>
          <div v-if="gallery.length < 9" class="gallery-add">
            <el-button :loading="uploadingGallery" @click="triggerGalleryInput"
              >+ 添加图片</el-button
            >
            <input
              id="tea-gallery-input"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              class="file-input"
              @change="onGalleryFileChange"
            />
          </div>
        </div>
      </section>

      <section class="form-section">
        <h3 class="text-h3 section-title">感官描述</h3>
        <div class="form-grid">
          <el-form-item label="外形" prop="shape_desc">
            <el-input v-model="teaForm.shape_desc" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="汤色" prop="soup_desc">
            <el-input v-model="teaForm.soup_desc" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="香气" prop="aroma_desc">
            <el-input v-model="teaForm.aroma_desc" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="滋味" prop="taste_desc">
            <el-input v-model="teaForm.taste_desc" type="textarea" :rows="3" />
          </el-form-item>
        </div>
      </section>

      <section class="form-section">
        <h3 class="text-h3 section-title">冲泡参考</h3>
        <div class="form-grid three">
          <el-form-item label="水温（℃）" prop="water_temp">
            <el-input-number
              v-model="teaForm.water_temp"
              :min="70"
              :max="100"
              :step="0.1"
              :precision="1"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="投茶量（g）" prop="tea_amount">
            <el-input-number
              v-model="teaForm.tea_amount"
              :min="0.1"
              :max="999.9"
              :step="0.1"
              :precision="1"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="时间（秒）" prop="brew_time">
            <el-input-number
              v-model="teaForm.brew_time"
              :min="0.1"
              :max="999.9"
              :step="0.1"
              :precision="1"
              class="full-width"
            />
          </el-form-item>
        </div>
      </section>

      <section class="form-section">
        <h3 class="text-h3 section-title">官方小贴士</h3>
        <p class="text-small text-secondary section-hint">
          选填；留空保存后该区块清空，不会影响茶品信息。
        </p>
        <div class="form-grid">
          <el-form-item label="历史典故">
            <el-input v-model="teaForm.tips_history" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="适合人群">
            <el-input v-model="teaForm.tips_suitable" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="冲泡误区">
            <el-input v-model="teaForm.tips_misconception" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="官方品鉴">
            <el-input v-model="teaForm.tips_official_note" type="textarea" :rows="3" />
          </el-form-item>
        </div>
      </section>

      <section class="form-section">
        <h3 class="text-h3 section-title">冲泡教程</h3>
        <p class="text-small text-secondary section-hint">
          逐茶维护，3–8 步；前台默认展示前 3 步并可展开。全部留空并删除后，只显示三格冲泡参数。
        </p>
        <el-form-item label="教程总览">
          <el-input
            v-model="guide.intro"
            maxlength="200"
            show-word-limit
            placeholder="一句话说明这款茶怎么泡，如：水温 85℃，快出汤不闷盖"
          />
        </el-form-item>

        <div class="guide-steps">
          <div v-for="(step, index) in guide.steps" :key="index" class="guide-step">
            <div class="guide-step__head">
              <span class="guide-step__label">第 {{ index + 1 }} 步</span>
              <div class="guide-step__ops">
                <el-button link :disabled="index === 0" @click="moveGuideStep(index, -1)"
                  >上移</el-button
                >
                <el-button
                  link
                  :disabled="index === guide.steps.length - 1"
                  @click="moveGuideStep(index, 1)"
                  >下移</el-button
                >
                <el-button
                  link
                  type="danger"
                  :disabled="guide.steps.length <= 3"
                  @click="removeGuideStep(index)"
                  >删除</el-button
                >
              </div>
            </div>
            <el-input
              v-model="step.title"
              maxlength="30"
              show-word-limit
              placeholder="步骤标题，如：温杯洁具"
            />
            <el-input
              v-model="step.detail"
              type="textarea"
              :rows="2"
              maxlength="200"
              show-word-limit
              placeholder="这一小步具体怎么做"
            />
            <el-input
              v-model="step.tip"
              maxlength="100"
              show-word-limit
              placeholder="小提示（可选）"
            />
          </div>
        </div>

        <div class="guide-actions">
          <el-button :disabled="guide.steps.length >= 8" @click="addGuideStep"
            >+ 添加步骤</el-button
          >
          <el-button @click="applyDraftTemplate">按茶类生成草稿</el-button>
          <el-button v-if="guide.exists" type="danger" plain @click="clearGuide"
            >删除教程</el-button
          >
          <span class="text-small text-secondary">
            当前 {{ guide.steps.length }} / 8 步（最少 3 步）
          </span>
        </div>

        <el-form-item label="注意事项">
          <el-input
            v-model="guide.caution"
            type="textarea"
            :rows="2"
            maxlength="500"
            show-word-limit
            placeholder="新手最容易踩的坑，如水温过高、久闷"
          />
        </el-form-item>
      </section>

      <div class="form-actions">
        <el-button @click="router.push({ name: 'admin-teas' })">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">
          {{ isEdit ? '保存修改' : '创建茶品' }}
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}
.page-head h2 {
  margin: 0 0 4px;
}
.page-head p {
  margin: 0;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tea-form {
  max-width: 1100px;
}
.form-section {
  margin-bottom: 18px;
  padding: 20px 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
}
.section-title {
  margin: 0 0 16px;
}
.section-hint {
  margin: -8px 0 14px;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 24px;
}
.form-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.full-width {
  width: 100%;
}
.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
}
.guide-step {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
}
.guide-step__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.guide-step__label {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-text-secondary);
}
.guide-step__ops {
  display: flex;
  gap: 4px;
}
.guide-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.image-field {
  display: flex;
  gap: 8px;
  width: 100%;
}
.file-input {
  display: none;
}
.image-preview {
  margin-top: 10px;
}
.image-preview img {
  max-width: 220px;
  max-height: 150px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  object-fit: cover;
}
.video-preview {
  margin-top: 10px;
}
.video-preview video {
  max-width: 360px;
  width: 100%;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}
.gallery-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}
.gallery-item {
  width: 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.gallery-item img {
  width: 140px;
  height: 105px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}
.gallery-add {
  width: 140px;
  height: 105px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 4px 0 24px;
}
</style>
