<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import CategoryTag from '@/components/CategoryTag.vue'
import { changePassword } from '@/api/auth'
import { getListDetail, getMyLists } from '@/api/lists'
import { getMyStats, setPresetAvatar, uploadAvatar } from '@/api/me'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import { CATEGORY_LABELS } from '@/utils/teaQuery'
import { clearHistory, getHistory, type ViewHistoryItem } from '@/utils/viewHistory'
import type { ListItem, ListSummary, TeaCategory, UserStats } from '@/types'

/** 预置头像编号（与 backend services/me.py AVATAR_PRESETS 对应） */
const AVATAR_PRESETS = Array.from({ length: 8 }, (_, index) => `tea-0${index + 1}`)
/** 与后端 save_image 上限一致（MAX_UPLOAD_SIZE_MB=5） */
const MAX_AVATAR_BYTES = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

const loading = ref(true)
const stats = ref<UserStats | null>(null)
const lists = ref<ListSummary[]>([])
const preview = ref<ListItem[]>([])
const history = ref<ViewHistoryItem[]>([])
const HISTORY_DISPLAY_LIMIT = 12

const avatarOpen = ref(false)
const uploading = ref(false)
const savingPreset = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

/** 修改密码（API_CONTRACT §4.1.6）：成功后旧会话全部失效，需重新登录 */
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})
const passwordErrors = reactive<{
  old_password?: string
  new_password?: string
  confirm_password?: string
  form?: string
}>({})
const changingPassword = ref(false)

const avatarUrl = computed(() => userStore.user?.avatar_url ?? null)
const initial = computed(() => (userStore.user?.username ?? '').slice(0, 1).toUpperCase())
const roleLabel = computed(() => (userStore.isAdmin ? '管理员' : '注册用户'))

onMounted(() => {
  void load()
})

async function load() {
  loading.value = true
  history.value = getHistory().slice(0, HISTORY_DISPLAY_LIMIT)
  try {
    // 统计 / 清单失败不阻断页面其余部分展示（错误提示由请求拦截器统一处理）
    const [statsRes, listsRes] = await Promise.all([
      getMyStats().catch(() => null),
      getMyLists().catch(() => null),
    ])
    stats.value = statsRes?.data ?? null
    lists.value = listsRes?.data ?? []

    const defaultList = lists.value.find((item) => item.is_default) ?? lists.value[0]
    if (defaultList) {
      const detail = await getListDetail(defaultList.id).catch(() => null)
      preview.value = (detail?.data.items ?? []).slice(0, 6)
    }
  } finally {
    loading.value = false
  }
}

function formatDate(value?: string): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function historyMeta(item: ViewHistoryItem): string {
  const label = CATEGORY_LABELS[item.category as TeaCategory] ?? item.category
  return `${label} · ${formatDate(item.viewed_at)}`
}

function onClearHistory() {
  if (!history.value.length) return
  if (!window.confirm('确定清空最近浏览记录吗？')) return
  clearHistory()
  history.value = []
  toast.info('最近浏览已清空')
}

function pickFile() {
  if (uploading.value) return
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许连续选择同一文件
  if (!file) return

  if (!ALLOWED_TYPES.includes(file.type)) {
    toast.warn('仅支持 JPEG / PNG / WebP 图片')
    return
  }
  if (file.size > MAX_AVATAR_BYTES) {
    toast.warn('图片不能超过 5 MB')
    return
  }

  uploading.value = true
  try {
    const res = await uploadAvatar(file)
    userStore.user = res.data
    avatarOpen.value = false
    toast.success('头像已更新')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    uploading.value = false
  }
}

async function choosePreset(preset: string) {
  if (savingPreset.value) return
  savingPreset.value = preset
  try {
    const res = await setPresetAvatar(preset)
    userStore.user = res.data
    avatarOpen.value = false
    toast.success('头像已更新')
  } catch {
    // 统一错误提示由请求拦截器处理
  } finally {
    savingPreset.value = null
  }
}

async function onLogout() {
  await userStore.logout()
  toast.info('已退出登录')
  router.push('/')
}

function validatePasswordForm(): boolean {
  passwordErrors.old_password = undefined
  passwordErrors.new_password = undefined
  passwordErrors.confirm_password = undefined
  passwordErrors.form = undefined

  if (!passwordForm.old_password) {
    passwordErrors.old_password = '请输入当前密码'
  }
  if (passwordForm.new_password.length < 6 || passwordForm.new_password.length > 64) {
    passwordErrors.new_password = '新密码需为 6-64 个字符'
  }
  if (passwordForm.confirm_password !== passwordForm.new_password) {
    passwordErrors.confirm_password = '两次输入的新密码不一致'
  }
  return (
    !passwordErrors.old_password && !passwordErrors.new_password && !passwordErrors.confirm_password
  )
}

function clearPasswordError(field: 'old_password' | 'new_password' | 'confirm_password') {
  passwordErrors[field] = undefined
  passwordErrors.form = undefined
}

async function onChangePassword() {
  if (!validatePasswordForm()) return
  changingPassword.value = true
  try {
    await changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    // 后端已递增 session_version 并清除 Cookie，这里同步清空本地登录态
    await userStore.logout()
    toast.success('密码已修改，请重新登录')
    router.push('/login')
  } catch (err) {
    // 旧密码错误返回 40110（拦截器不对该路径做会话过期跳转），在此内联提示
    const response = (err as { response?: { status?: number; data?: { message?: string } } })
      .response
    if (response?.status === 401) {
      passwordErrors.form = response.data?.message || '当前密码不正确'
    }
  } finally {
    changingPassword.value = false
  }
}
</script>

<template>
  <AppHeader />

  <main class="profile-page">
    <div class="container">
      <nav class="breadcrumb" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span class="breadcrumb__sep">›</span>
        <span class="breadcrumb__current">个人中心</span>
      </nav>

      <!-- 个人信息 -->
      <section class="profile-hero">
        <div class="profile-hero__avatar-wrap">
          <img
            v-if="avatarUrl"
            class="profile-hero__avatar"
            :src="avatarUrl"
            :alt="`${userStore.user?.username} 的头像`"
          />
          <span
            v-else
            class="profile-hero__avatar profile-hero__avatar--placeholder"
            aria-hidden="true"
          >
            {{ initial }}
          </span>
          <button class="profile-hero__avatar-btn" type="button" @click="avatarOpen = !avatarOpen">
            {{ avatarOpen ? '收起' : '更换头像' }}
          </button>
        </div>

        <div class="profile-hero__info">
          <p class="page-kicker">Profile</p>
          <div class="profile-hero__title-row">
            <h1 class="profile-hero__name">{{ userStore.user?.username }}</h1>
            <span class="role-tag" :class="{ 'role-tag--admin': userStore.isAdmin }">
              {{ roleLabel }}
            </span>
          </div>
          <p class="profile-hero__meta">加入于 {{ formatDate(userStore.user?.created_at) }}</p>

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

        <div class="profile-hero__stats">
          <RouterLink class="stat" :to="{ name: 'my-list' }">
            <span class="stat__num">{{ stats?.favorite_count ?? 0 }}</span>
            <span class="stat__label">收藏茶品</span>
          </RouterLink>
          <div class="stat">
            <span class="stat__num">{{ stats?.note_count ?? 0 }}</span>
            <span class="stat__label">品鉴笔记</span>
          </div>
          <div class="stat">
            <span class="stat__num">{{ stats?.share_count ?? 0 }}</span>
            <span class="stat__label">分享清单</span>
          </div>
        </div>
      </section>

      <!-- 更换头像面板 -->
      <section v-if="avatarOpen" class="avatar-panel">
        <header class="avatar-panel__head">
          <h2 class="avatar-panel__title">更换头像</h2>
          <button
            type="button"
            class="avatar-panel__close"
            aria-label="收起"
            @click="avatarOpen = false"
          >
            ✕
          </button>
        </header>

        <div class="avatar-panel__body">
          <div class="avatar-panel__upload">
            <h3 class="avatar-panel__subtitle">上传本地图片</h3>
            <p class="avatar-panel__hint">支持 JPEG / PNG / WebP，不超过 5 MB</p>
            <input
              ref="fileInput"
              class="avatar-panel__file"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              @change="onFileChange"
            />
            <button type="button" class="btn btn--primary" :disabled="uploading" @click="pickFile">
              {{ uploading ? '上传中…' : '选择图片上传' }}
            </button>
          </div>

          <div class="avatar-panel__presets">
            <h3 class="avatar-panel__subtitle">选择预置头像</h3>
            <p class="avatar-panel__hint">点击即可立即生效</p>
            <ul class="preset-grid">
              <li v-for="preset in AVATAR_PRESETS" :key="preset">
                <button
                  type="button"
                  class="preset"
                  :class="{ 'preset--active': avatarUrl === `/avatars/${preset}.svg` }"
                  :disabled="!!savingPreset"
                  :title="`选择预置头像 ${preset}`"
                  @click="choosePreset(preset)"
                >
                  <img :src="`/avatars/${preset}.svg`" :alt="`预置头像 ${preset}`" />
                </button>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 账号安全：自助修改密码 -->
      <section class="security">
        <header class="section-head">
          <h2 class="section-head__title">账号安全</h2>
        </header>
        <p class="security__hint">修改密码后，所有已登录设备将立即退出，需要重新登录。</p>

        <form class="password-form" novalidate @submit.prevent="onChangePassword">
          <div class="password-field">
            <label class="password-label" for="password-old">当前密码</label>
            <input
              id="password-old"
              v-model="passwordForm.old_password"
              type="password"
              class="password-input"
              :class="{ 'password-input--error': passwordErrors.old_password }"
              autocomplete="current-password"
              placeholder="请输入当前密码"
              @input="clearPasswordError('old_password')"
            />
            <div v-if="passwordErrors.old_password" class="password-hint password-hint--error">
              {{ passwordErrors.old_password }}
            </div>
          </div>

          <div class="password-field">
            <label class="password-label" for="password-new">新密码</label>
            <input
              id="password-new"
              v-model="passwordForm.new_password"
              type="password"
              class="password-input"
              :class="{ 'password-input--error': passwordErrors.new_password }"
              autocomplete="new-password"
              placeholder="6-64 个字符"
              @input="clearPasswordError('new_password')"
            />
            <div v-if="passwordErrors.new_password" class="password-hint password-hint--error">
              {{ passwordErrors.new_password }}
            </div>
          </div>

          <div class="password-field">
            <label class="password-label" for="password-confirm">确认新密码</label>
            <input
              id="password-confirm"
              v-model="passwordForm.confirm_password"
              type="password"
              class="password-input"
              :class="{ 'password-input--error': passwordErrors.confirm_password }"
              autocomplete="new-password"
              placeholder="请再次输入新密码"
              @input="clearPasswordError('confirm_password')"
            />
            <div v-if="passwordErrors.confirm_password" class="password-hint password-hint--error">
              {{ passwordErrors.confirm_password }}
            </div>
          </div>

          <div v-if="passwordErrors.form" class="password-error-bar">{{ passwordErrors.form }}</div>

          <button type="submit" class="btn btn--primary" :disabled="changingPassword">
            {{ changingPassword ? '提交中…' : '修改密码' }}
          </button>
        </form>
      </section>

      <!-- 我的收藏预览 -->
      <section class="favorites">
        <header class="section-head">
          <h2 class="section-head__title">我的收藏</h2>
          <RouterLink class="section-head__more" :to="{ name: 'my-list' }"
            >查看全部清单 →</RouterLink
          >
        </header>

        <div v-if="loading" class="favorites__skeleton" aria-hidden="true"></div>

        <ul v-else-if="preview.length" class="favorite-grid">
          <li v-for="item in preview" :key="item.tea_id" class="favorite-card">
            <RouterLink
              class="favorite-card__link"
              :to="{ name: 'tea-detail', params: { id: item.tea_id } }"
            >
              <img
                v-if="item.main_image_url"
                class="favorite-card__image"
                :src="item.main_image_url"
                :alt="item.name"
                loading="lazy"
              />
              <span
                v-else
                class="favorite-card__image favorite-card__image--placeholder"
                aria-hidden="true"
              >
                🫖
              </span>
              <span class="favorite-card__body">
                <span class="favorite-card__name">{{ item.name }}</span>
                <span class="favorite-card__meta">{{ item.origin }}</span>
              </span>
              <CategoryTag :category="item.category" />
            </RouterLink>
          </li>
        </ul>

        <div v-else class="favorites__empty">
          <p class="favorites__empty-text">还没有收藏的茶品，去发现一盏好茶吧。</p>
          <RouterLink class="btn btn--primary" to="/teas">浏览茶品列表</RouterLink>
        </div>

        <p v-if="!loading && lists.length" class="favorites__summary">
          共 {{ lists.length }} 个清单 · {{ stats?.favorite_count ?? 0 }} 款茶
        </p>
      </section>

      <!-- 最近浏览（本地记录，最多 12 条；无数据时整块隐藏） -->
      <section v-if="history.length" class="history">
        <header class="section-head">
          <h2 class="section-head__title">最近浏览</h2>
          <button type="button" class="section-head__clear" @click="onClearHistory">清空</button>
        </header>
        <ul class="history-grid">
          <li v-for="item in history" :key="item.tea_id">
            <RouterLink
              class="history-card"
              :to="{ name: 'tea-detail', params: { id: item.tea_id } }"
            >
              <img
                v-if="item.cover_image"
                class="history-card__image"
                :src="item.cover_image"
                :alt="item.name"
                loading="lazy"
              />
              <span
                v-else
                class="history-card__image history-card__image--placeholder"
                aria-hidden="true"
              >
                🫖
              </span>
              <span class="history-card__body">
                <span class="history-card__name">{{ item.name }}</span>
                <span class="history-card__meta">{{ historyMeta(item) }}</span>
              </span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- 快捷入口 -->
      <section class="quick-links">
        <RouterLink class="quick" :to="{ name: 'my-list' }">📚 我的清单</RouterLink>
        <RouterLink class="quick" :to="{ name: 'contribute' }">✍️ 投稿新茶 / 科普</RouterLink>
        <RouterLink class="quick" :to="{ name: 'my-contributions' }">📮 我的提交</RouterLink>
        <RouterLink v-if="userStore.isAdmin" class="quick" :to="{ name: 'admin-dashboard' }">
          ⚙️ 管理后台
        </RouterLink>
        <button type="button" class="quick quick--danger" @click="onLogout">退出登录</button>
      </section>
    </div>
  </main>

  <AppFooter />
</template>

<style scoped>
.profile-page {
  padding-top: 88px;
  padding-bottom: 48px;
  min-height: 100svh;
}

.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 32px;
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

/* —— 个人信息 —— */
.profile-hero {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 28px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.profile-hero__avatar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.profile-hero__avatar {
  width: 96px;
  height: 96px;
  border-radius: var(--radius-full);
  object-fit: cover;
  background: var(--color-bg-muted);
  border: 2px solid var(--color-border);
}

.profile-hero__avatar--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: var(--text-h1);
  color: var(--color-primary-dark);
}

.profile-hero__avatar-btn {
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-full);
  background: transparent;
  padding: 4px 12px;
  font-family: inherit;
  font-size: var(--text-caption);
  color: var(--color-text-secondary);
  cursor: pointer;
  white-space: nowrap;
}

.profile-hero__avatar-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.profile-hero__info {
  flex: 1;
  min-width: 0;
}

.profile-hero__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.profile-hero__name {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-h1);
  color: var(--color-text-primary);
}

.role-tag {
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-size: var(--text-caption);
}

.role-tag--admin {
  background: rgba(139, 115, 85, 0.14);
  color: var(--color-primary-dark);
  font-weight: 600;
}

.profile-hero__meta {
  margin: 6px 0 0;
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.level {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
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

.profile-hero__stats {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 76px;
  padding: 10px 8px;
  border-radius: var(--radius-md);
}

.stat:hover {
  background: var(--color-bg-muted);
}

.stat__num {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-primary-dark);
}

.stat__label {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

/* —— 头像面板 —— */
.avatar-panel {
  padding: 20px 24px 24px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.avatar-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.avatar-panel__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-h3);
  color: var(--color-text-primary);
}

.avatar-panel__close {
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-small);
  cursor: pointer;
}

.avatar-panel__close:hover {
  color: var(--color-primary);
}

.avatar-panel__body {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 32px;
}

.avatar-panel__subtitle {
  margin: 0 0 4px;
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.avatar-panel__hint {
  margin: 0 0 14px;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.avatar-panel__file {
  display: none;
}

.preset-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 10px;
}

.preset {
  width: 100%;
  aspect-ratio: 1;
  padding: 0;
  border: 2px solid transparent;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  cursor: pointer;
  overflow: hidden;
  transition:
    border-color 0.15s,
    transform 0.15s;
}

.preset:hover:not(:disabled) {
  transform: translateY(-2px);
  border-color: var(--color-border-dark);
}

.preset--active {
  border-color: var(--color-primary);
}

.preset:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.preset img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* —— 账号安全 —— */
.security {
  padding: 24px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.security__hint {
  margin: -4px 0 18px;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 380px;
}

.password-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.password-label {
  font-size: var(--text-small);
  font-weight: 500;
  color: var(--color-text-secondary);
}

.password-input {
  width: 100%;
  padding: 10px 14px;
  font-family: inherit;
  font-size: var(--text-body);
  color: var(--color-text-primary);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-sm);
  outline: none;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.password-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(139, 115, 85, 0.12);
}

.password-input--error {
  border-color: var(--color-error);
}

.password-hint {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.password-hint--error {
  color: var(--color-error);
}

.password-error-bar {
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
  color: var(--color-error);
  font-size: var(--text-caption);
}

.password-form .btn {
  align-self: flex-start;
}

/* —— 我的收藏 —— */
.favorites {
  padding: 24px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.section-head__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-h3);
  color: var(--color-text-primary);
}

.section-head__more {
  font-size: var(--text-small);
  color: var(--color-primary);
  white-space: nowrap;
}

.section-head__clear {
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: var(--text-small);
  color: var(--color-text-muted);
  cursor: pointer;
}

.section-head__clear:hover {
  color: var(--color-primary);
}

.favorites__skeleton {
  height: 180px;
  border-radius: var(--radius-md);
  background: var(--color-bg-muted);
}

.favorite-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.favorite-card__link {
  display: grid;
  grid-template-columns: 64px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.favorite-card__link:hover {
  border-color: var(--color-border-dark);
  box-shadow: var(--shadow-card);
}

.favorite-card__image {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  background: var(--color-bg-muted);
}

.favorite-card__image--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--color-text-muted);
}

.favorite-card__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.favorite-card__name {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.favorite-card__meta {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.favorites__empty {
  text-align: center;
  padding: 40px 16px;
  border: 1px dashed var(--color-border-dark);
  border-radius: var(--radius-md);
}

.favorites__empty-text {
  margin: 0 0 16px;
  font-size: var(--text-small);
  color: var(--color-text-muted);
}

.favorites__summary {
  margin: 16px 0 0;
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

/* —— 最近浏览 —— */
.history {
  padding: 24px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.history-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.history-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.history-card:hover {
  border-color: var(--color-border-dark);
  box-shadow: var(--shadow-card);
}

.history-card__image {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  object-fit: cover;
  background: var(--color-bg-muted);
}

.history-card__image--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: var(--color-text-muted);
}

.history-card__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.history-card__name {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-card__meta {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* —— 快捷入口 —— */
.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.quick {
  display: inline-flex;
  align-items: center;
  height: 40px;
  padding: 0 18px;
  border: 1px solid var(--color-border-dark);
  border-radius: var(--radius-full);
  background: var(--color-bg-surface);
  font-family: inherit;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.quick:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.quick--danger {
  color: var(--color-error);
}

.quick--danger:hover {
  border-color: var(--color-error);
  color: var(--color-error);
}

/* —— 按钮 —— */
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
  white-space: nowrap;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
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

@media (max-width: 900px) {
  .favorite-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .history-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .preset-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 767px) {
  .profile-page {
    padding-top: 76px;
  }

  .container {
    padding: 0 16px;
  }

  .profile-hero {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
    padding: 20px;
  }

  .profile-hero__stats {
    width: 100%;
    justify-content: space-between;
  }

  .stat {
    min-width: 0;
    flex: 1;
  }

  .avatar-panel__body {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .favorite-grid {
    grid-template-columns: 1fr;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }
}
</style>
