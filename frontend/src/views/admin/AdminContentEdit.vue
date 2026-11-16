<script setup lang="ts">
/**
 * 管理员内容编辑（批次五 R1–R5）：新增/编辑共用
 */
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { createAdminContent, getAdminContent, updateAdminContent } from '@/api/admin'
import { getContentTypes } from '@/api/contents'
import type {
  AdminContentCreatePayload,
  AdminContentUpdatePayload,
  ContentTypeCode,
  ContentTypeItem,
} from '@/types'

const route = useRoute()
const router = useRouter()

const editId = computed(() => {
  const id = route.params.id
  return id ? Number(id) : null
})
const isEdit = computed(() => editId.value !== null)

interface ContentForm {
  type_code: ContentTypeCode | ''
  title: string
  summary: string
  body: string
  cover_image: string
  meta: Record<string, unknown>
  sort_order: number
  is_active: boolean
}

const types = ref<ContentTypeItem[]>([])
const loading = ref(true)
const saving = ref(false)

// 表单
const form = ref<ContentForm>({
  type_code: '',
  title: '',
  summary: '',
  body: '',
  cover_image: '',
  meta: {},
  sort_order: 0,
  is_active: true,
})

// meta 编辑辅助（按板块动态渲染）
const teawareMeta = ref({ material: '', volume: '', category: '' })
const originMeta = ref({ province: '', region: '' })
const cultureMeta = ref({ era: '', tags: '' })
const brandMeta = ref({ founded: '' as number | string, brand_origin: '', website: '' })
const knowledgeMeta = ref({ subtype: '' as string, difficulty: '' as string })

watch(
  () => form.value.type_code,
  () => {
    // 板块切换时将 meta 同步到对应的 ref 对象（编辑时需要先从 form.value.meta 还原）
  },
)

function syncFormFromMeta() {
  // 将各板块 meta ref → form.value.meta JSON
  if (form.value.type_code === 'teaware') {
    const m = teawareMeta.value
    const meta: Record<string, unknown> = {}
    if (m.material) meta.material = m.material
    if (m.volume) meta.volume = m.volume
    if (m.category) meta.category = m.category
    form.value.meta = meta
  } else if (form.value.type_code === 'origin') {
    const m = originMeta.value
    const meta: Record<string, unknown> = {}
    if (m.province) meta.province = m.province
    if (m.region) meta.region = m.region
    form.value.meta = meta
  } else if (form.value.type_code === 'culture') {
    const m = cultureMeta.value
    const meta: Record<string, unknown> = {}
    if (m.era) meta.era = m.era
    if (m.tags)
      meta.tags = m.tags
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    form.value.meta = meta
  } else if (form.value.type_code === 'brand') {
    const m = brandMeta.value
    const meta: Record<string, unknown> = {}
    if (m.founded) meta.founded = Number(m.founded)
    if (m.brand_origin) meta.brand_origin = m.brand_origin
    if (m.website) meta.website = m.website
    form.value.meta = meta
  } else if (form.value.type_code === 'knowledge') {
    const m = knowledgeMeta.value
    const meta: Record<string, unknown> = {}
    if (m.subtype) meta.subtype = m.subtype
    if (m.difficulty) meta.difficulty = m.difficulty
    form.value.meta = meta
  } else {
    form.value.meta = {}
  }
}

function restoreMetaFromForm() {
  // 将 form.value.meta JSON → 各板块 ref 对象（编辑回填时调用）
  const type = form.value.type_code
  const m = form.value.meta || {}
  if (type === 'teaware') {
    teawareMeta.value.material = String(m.material ?? '')
    teawareMeta.value.volume = String(m.volume ?? '')
    teawareMeta.value.category = String(m.category ?? '')
  } else if (type === 'origin') {
    originMeta.value.province = String(m.province ?? '')
    originMeta.value.region = String(m.region ?? '')
  } else if (type === 'culture') {
    cultureMeta.value.era = String(m.era ?? '')
    const tags = Array.isArray(m.tags) ? (m.tags as string[]).join(',') : String(m.tags ?? '')
    cultureMeta.value.tags = tags
  } else if (type === 'brand') {
    brandMeta.value.founded = (m.founded as number) ?? ''
    brandMeta.value.brand_origin = String(m.brand_origin ?? '')
    brandMeta.value.website = String(m.website ?? '')
  } else if (type === 'knowledge') {
    knowledgeMeta.value.subtype = String(m.subtype ?? '')
    knowledgeMeta.value.difficulty = String(m.difficulty ?? '')
  }
}

async function load() {
  loading.value = true
  try {
    types.value = await getContentTypes()

    if (isEdit.value && editId.value) {
      const res = await getAdminContent(editId.value)
      const item = res.data
      // 回填表单
      form.value.type_code = item.type_code
      form.value.title = item.title
      form.value.summary = item.summary ?? ''
      form.value.body = item.body ?? ''
      form.value.cover_image = item.cover_image ?? ''
      form.value.meta = item.meta ?? {}
      form.value.sort_order = item.sort_order
      form.value.is_active = item.is_active ?? true
      // meta → 各板块 ref 对象
      restoreMetaFromForm()
    }
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!form.value.type_code) {
    ElMessage.warning('请选择板块类型')
    return
  }
  syncFormFromMeta()

  saving.value = true
  try {
    if (isEdit.value && editId.value) {
      const payload: AdminContentUpdatePayload = {
        title: form.value.title.trim(),
        summary: form.value.summary.trim() || null,
        body: form.value.body.trim() || null,
        cover_image: form.value.cover_image.trim() || null,
        meta: form.value.meta,
        sort_order: form.value.sort_order,
        is_active: form.value.is_active,
      }
      await updateAdminContent(editId.value, payload)
      ElMessage.success('已更新')
    } else {
      const payload: AdminContentCreatePayload = {
        type_code: form.value.type_code as ContentTypeCode,
        title: form.value.title.trim(),
        summary: form.value.summary.trim() || null,
        body: form.value.body.trim() || null,
        cover_image: form.value.cover_image.trim() || null,
        meta: form.value.meta,
        sort_order: form.value.sort_order,
      }
      await createAdminContent(payload)
      ElMessage.success('已创建')
    }
    router.push('/admin/contents')
  } catch {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    saving.value = false
  }
}

function onCancel() {
  ElMessageBox.confirm('未保存的修改将丢失，确认返回？', '提示', {
    confirmButtonText: '返回',
    cancelButtonText: '继续编辑',
    type: 'warning',
  })
    .then(() => router.push('/admin/contents'))
    .catch(() => {})
}

onMounted(load)
</script>

<template>
  <div class="admin-content-edit">
    <h3 class="admin-content-edit__title">{{ isEdit ? '编辑内容' : '新增内容' }}</h3>

    <el-form v-if="!loading" :model="form" label-width="100px" style="max-width: 720px">
      <el-form-item label="板块类型" required>
        <el-select v-model="form.type_code" placeholder="请选择板块" :disabled="isEdit">
          <el-option
            v-for="t in types"
            :key="t.code"
            :value="t.code"
            :label="`${t.icon ?? ''} ${t.name}`"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="200" show-word-limit />
      </el-form-item>

      <el-form-item label="摘要">
        <el-input
          v-model="form.summary"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="封面图 URL">
        <el-input v-model="form.cover_image" placeholder="http(s):// 或 /uploads/ 路径" />
      </el-form-item>

      <!-- meta 特有字段（按板块渲染） -->
      <template v-if="form.type_code === 'teaware'">
        <el-divider content-position="left">茶具特有字段</el-divider>
        <el-form-item label="材质">
          <el-input v-model="teawareMeta.material" placeholder="如：紫砂 / 白瓷 / 玻璃" />
        </el-form-item>
        <el-form-item label="容量">
          <el-input v-model="teawareMeta.volume" placeholder="如：200ml" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input
            v-model="teawareMeta.category"
            placeholder="如：盖碗 / 茶壶 / 品茗杯 / 公道杯"
          />
        </el-form-item>
      </template>

      <template v-else-if="form.type_code === 'origin'">
        <el-divider content-position="left">产地特有字段</el-divider>
        <el-form-item label="省份">
          <el-input v-model="originMeta.province" placeholder="如：浙江" />
        </el-form-item>
        <el-form-item label="产区">
          <el-input v-model="originMeta.region" placeholder="如：杭州西湖" />
        </el-form-item>
      </template>

      <template v-else-if="form.type_code === 'culture'">
        <el-divider content-position="left">文化特有字段</el-divider>
        <el-form-item label="时期">
          <el-input v-model="cultureMeta.era" placeholder="如：唐代 / 宋代" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="cultureMeta.tags" placeholder="逗号分隔，如：陆羽,茶经,茶道" />
        </el-form-item>
      </template>

      <template v-else-if="form.type_code === 'brand'">
        <el-divider content-position="left">品牌特有字段</el-divider>
        <el-form-item label="创立年份">
          <el-input-number
            v-model="brandMeta.founded"
            :min="0"
            :max="2100"
            placeholder="如：1915"
          />
        </el-form-item>
        <el-form-item label="产地">
          <el-input v-model="brandMeta.brand_origin" placeholder="如：福建安溪" />
        </el-form-item>
        <el-form-item label="官网">
          <el-input v-model="brandMeta.website" placeholder="https://..." />
        </el-form-item>
      </template>

      <template v-else-if="form.type_code === 'knowledge'">
        <el-divider content-position="left">知识特有字段</el-divider>
        <el-form-item label="分类">
          <el-select v-model="knowledgeMeta.subtype" placeholder="请选择">
            <el-option value="standard" label="茶叶标准" />
            <el-option value="brewing" label="冲泡知识" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="knowledgeMeta.difficulty" placeholder="请选择">
            <el-option value="beginner" label="入门" />
            <el-option value="intermediate" label="进阶" />
            <el-option value="advanced" label="高级" />
          </el-select>
        </el-form-item>
      </template>

      <el-form-item label="正文">
        <el-input
          v-model="form.body"
          type="textarea"
          :rows="10"
          maxlength="20000"
          show-word-limit
          placeholder="纯文本正文，段落间空行自动保留。MVP 暂不支持富文本。"
        />
      </el-form-item>

      <el-form-item label="排序">
        <el-input-number v-model="form.sort_order" :step="1" />
        <span style="margin-left: 12px; font-size: 12px; color: var(--color-text-muted)">
          同板块内数字越小越靠前
        </span>
      </el-form-item>

      <el-form-item label="状态">
        <el-switch v-model="form.is_active" active-text="上架" inactive-text="下架" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="onSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
        <el-button @click="onCancel">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.admin-content-edit__title {
  font-size: var(--text-h2);
  margin: 0 0 24px;
  color: var(--color-primary-dark);
}
</style>
