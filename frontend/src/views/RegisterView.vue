<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { resolveLoginRedirect } from '@/utils/redirect'
import { checkUsernameAvailability } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

const errors = reactive<{
  username?: string
  password?: string
  confirmPassword?: string
  form?: string
}>({})

const submitting = ref(false)
const checkingUsername = ref(false)
const usernameAvailable = ref<boolean | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onPasswordInput() {
  errors.password = undefined
  errors.form = undefined
}

// 用户名 3-20 字符，中文/英文/数字
const USERNAME_RE = /^[A-Za-z0-9\u4e00-\u9fa5]{3,20}$/

function validateUsernameFormat(value: string): boolean {
  return USERNAME_RE.test(value)
}

async function checkUsername() {
  const val = form.username.trim()
  errors.username = undefined
  usernameAvailable.value = null

  if (!val) return
  if (!validateUsernameFormat(val)) {
    errors.username = '用户名需 3-20 字符，仅支持中文/英文/数字'
    return
  }

  checkingUsername.value = true
  try {
    const res = await checkUsernameAvailability(val)
    usernameAvailable.value = res.data?.available ?? false
    if (!usernameAvailable.value) {
      errors.username = '该用户名已被占用'
    }
  } catch {
    // 网络错误不阻塞注册，提交时后端会再校验
  } finally {
    checkingUsername.value = false
  }
}

function onUsernameInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(checkUsername, 400)
}

function validate(): boolean {
  errors.username = undefined
  errors.password = undefined
  errors.confirmPassword = undefined
  errors.form = undefined

  if (!form.username.trim()) {
    errors.username = '请输入用户名'
  } else if (!validateUsernameFormat(form.username.trim())) {
    errors.username = '用户名需 3-20 字符，仅支持中文/英文/数字'
  }

  if (!form.password) {
    errors.password = '请输入密码'
  } else if (form.password.length < 6 || form.password.length > 64) {
    errors.password = '密码长度需 6-64 字符'
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = '请再次输入密码'
  } else if (form.confirmPassword !== form.password) {
    errors.confirmPassword = '两次输入的密码不一致'
  }

  return !errors.username && !errors.password && !errors.confirmPassword
}

async function onSubmit() {
  if (!validate()) return
  if (usernameAvailable.value === false) {
    errors.username = '该用户名已被占用'
    return
  }
  submitting.value = true
  try {
    await userStore.register({
      username: form.username.trim(),
      password: form.password,
    })
    // 注册成功后端自动登录，跳回来源页或首页
    const redirect = resolveLoginRedirect(route.query.redirect)
    router.push(redirect)
  } catch {
    errors.form = '注册失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

function goLogin() {
  router.push({
    path: '/login',
    query: route.query.redirect ? { redirect: route.query.redirect as string } : {},
  })
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-card__brand">🫖 茶·图鉴</div>
      <h1 class="auth-card__title">注册</h1>
      <p class="auth-card__desc">创建账号，开启品茶之旅</p>

      <form class="auth-form" @submit.prevent="onSubmit" novalidate>
        <div class="form-group">
          <label class="form-label" for="reg-username">用户名</label>
          <input
            id="reg-username"
            v-model.trim="form.username"
            type="text"
            class="form-input"
            :class="{ 'form-input--error': errors.username }"
            placeholder="3-20 字符，中文/英文/数字"
            autocomplete="username"
            @input="onUsernameInput"
          />
          <div v-if="checkingUsername" class="form-hint">检查中…</div>
          <div v-else-if="errors.username" class="form-hint form-hint--error">
            {{ errors.username }}
          </div>
          <div v-else-if="usernameAvailable === true" class="form-hint form-hint--success">
            用户名可用
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-password">密码</label>
          <input
            id="reg-password"
            v-model="form.password"
            type="password"
            class="form-input"
            :class="{ 'form-input--error': errors.password }"
            placeholder="6-64 字符"
            autocomplete="new-password"
            @input="onPasswordInput"
          />
          <div v-if="errors.password" class="form-hint form-hint--error">{{ errors.password }}</div>
        </div>

        <div class="form-group">
          <label class="form-label" for="reg-confirm">确认密码</label>
          <input
            id="reg-confirm"
            v-model="form.confirmPassword"
            type="password"
            class="form-input"
            :class="{ 'form-input--error': errors.confirmPassword }"
            placeholder="请再次输入密码"
            autocomplete="new-password"
            @input="errors.confirmPassword = undefined"
          />
          <div v-if="errors.confirmPassword" class="form-hint form-hint--error">
            {{ errors.confirmPassword }}
          </div>
        </div>

        <div v-if="errors.form" class="form-error-bar">{{ errors.form }}</div>

        <button
          type="submit"
          class="btn btn--primary btn--block"
          :disabled="submitting || checkingUsername"
        >
          {{ submitting ? '注册中…' : '注册并登录' }}
        </button>
      </form>

      <p class="auth-card__foot">
        已有账号？
        <a class="auth-card__link" @click="goLogin">去登录</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
/* 复用与 LoginView 相同的样式结构 */
.auth-page {
  min-height: 100svh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: var(--color-bg-page);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 40px 32px;
}

.auth-card__brand {
  text-align: center;
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--color-primary);
  margin-bottom: 8px;
}

.auth-card__title {
  text-align: center;
  font-size: var(--text-h2);
  color: var(--color-text-primary);
  margin: 0 0 6px;
}

.auth-card__desc {
  text-align: center;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  margin: 0 0 28px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
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

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(139, 115, 85, 0.12);
}

.form-input--error {
  border-color: var(--color-error);
}

.form-hint {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}

.form-hint--error {
  color: var(--color-error);
}

.form-hint--success {
  color: var(--color-success);
}

.form-error-bar {
  padding: 10px 14px;
  background: rgba(198, 40, 40, 0.08);
  color: var(--color-error);
  font-size: var(--text-small);
  border-radius: var(--radius-sm);
  text-align: center;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 20px;
  font-size: var(--text-body);
  font-weight: 500;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    background 0.2s,
    opacity 0.2s;
}

.btn--primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn--primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn--block {
  width: 100%;
}

.auth-card__foot {
  text-align: center;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
  margin: 24px 0 0;
}

.auth-card__link {
  color: var(--color-primary);
  cursor: pointer;
  text-decoration: none;
}

.auth-card__link:hover {
  text-decoration: underline;
}
</style>
