<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

onMounted(() => {
  // 已是管理员时直接进入后台（守卫之外的小优化）
  if (userStore.isAdmin) {
    router.replace({ name: 'admin-dashboard' })
  }
})

async function submit() {
  error.value = ''
  if (!form.username.trim() || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const res = await userStore.login({
      username: form.username.trim(),
      password: form.password,
    })
    if (res.data.role !== 'admin') {
      // 非管理员不留会话，避免普通用户误入后台
      await userStore.logout()
      error.value = '该账号没有管理员权限'
      return
    }
    router.replace({ name: 'admin-dashboard' })
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-login">
    <div class="login-card">
      <div class="login-brand">
        <h1 class="text-h1 font-display">茶 · 图鉴</h1>
        <p class="text-secondary">管理员后台</p>
      </div>

      <form class="login-form" @submit.prevent="submit">
        <label class="field-label" for="admin-username">用户名</label>
        <el-input
          id="admin-username"
          v-model="form.username"
          placeholder="请输入管理员用户名"
          autocomplete="username"
          size="large"
        />

        <label class="field-label" for="admin-password">密码</label>
        <el-input
          id="admin-password"
          v-model="form.password"
          type="password"
          show-password
          placeholder="请输入密码"
          autocomplete="current-password"
          size="large"
          @keyup.enter="submit"
        />

        <p v-if="error" class="text-error login-error">{{ error }}</p>

        <el-button
          type="primary"
          native-type="submit"
          size="large"
          :loading="loading"
          class="login-submit"
        >
          登录后台
        </el-button>
      </form>

      <p class="login-tip text-caption text-muted">
        后台仅限管理员账号访问，普通用户请返回前台登录。
      </p>
      <router-link class="login-back text-small" to="/">← 返回前台</router-link>
    </div>
  </div>
</template>

<style scoped>
.admin-login {
  min-height: 100svh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  background:
    radial-gradient(circle at 15% 20%, var(--color-bg-muted), transparent 45%), var(--color-bg-page);
}
.login-card {
  width: 100%;
  max-width: 420px;
  padding: 40px 36px 28px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
}
.login-brand {
  text-align: center;
  margin-bottom: 28px;
}
.login-brand h1 {
  margin: 0 0 8px;
  color: var(--color-primary-dark);
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.field-label {
  margin-top: 6px;
  font-size: var(--text-small);
  color: var(--color-text-secondary);
}
.login-error {
  margin: 4px 0 0;
  font-size: var(--text-small);
}
.login-submit {
  width: 100%;
  margin-top: 12px;
}
.login-tip {
  margin: 20px 0 8px;
  text-align: center;
}
.login-back {
  display: block;
  text-align: center;
}
</style>
