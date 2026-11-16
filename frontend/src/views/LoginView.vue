<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { resolveLoginRedirect } from '@/utils/redirect'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  username: '',
  password: '',
})

const errors = reactive<{ username?: string; password?: string; form?: string }>({})
const submitting = ref(false)

function validate(): boolean {
  errors.username = undefined
  errors.password = undefined
  errors.form = undefined

  if (!form.username.trim()) {
    errors.username = '请输入用户名'
  }
  if (!form.password) {
    errors.password = '请输入密码'
  }
  return !errors.username && !errors.password
}

async function onSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    await userStore.login({ username: form.username.trim(), password: form.password })
    // 登录成功后跳回来源页或首页
    const redirect = resolveLoginRedirect(route.query.redirect)
    router.push(redirect)
  } catch {
    // 401 用户名或密码错误（后端统一提示，不区分）
    errors.form = '用户名或密码错误'
  } finally {
    submitting.value = false
  }
}

function goRegister() {
  router.push({
    path: '/register',
    query: route.query.redirect ? { redirect: route.query.redirect as string } : {},
  })
}

function onPasswordInput() {
  errors.password = undefined
  errors.form = undefined
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-card__brand">🫖 茶·图鉴</div>
      <h1 class="auth-card__title">登录</h1>
      <p class="auth-card__desc">欢迎回来，请登录您的账号</p>

      <form class="auth-form" @submit.prevent="onSubmit" novalidate>
        <div class="form-group">
          <label class="form-label" for="login-username">用户名</label>
          <input
            id="login-username"
            v-model.trim="form.username"
            type="text"
            class="form-input"
            :class="{ 'form-input--error': errors.username }"
            placeholder="请输入用户名"
            autocomplete="username"
            @input="errors.username = undefined"
          />
          <div v-if="errors.username" class="form-hint form-hint--error">{{ errors.username }}</div>
        </div>

        <div class="form-group">
          <label class="form-label" for="login-password">密码</label>
          <input
            id="login-password"
            v-model="form.password"
            type="password"
            class="form-input"
            :class="{ 'form-input--error': errors.password }"
            placeholder="请输入密码"
            autocomplete="current-password"
            @input="onPasswordInput"
          />
          <div v-if="errors.password" class="form-hint form-hint--error">{{ errors.password }}</div>
        </div>

        <div v-if="errors.form" class="form-error-bar">{{ errors.form }}</div>

        <button type="submit" class="btn btn--primary btn--block" :disabled="submitting">
          {{ submitting ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="auth-card__foot">
        还没有账号？
        <a class="auth-card__link" @click="goRegister">立即注册</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
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
