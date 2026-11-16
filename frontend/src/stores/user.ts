import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'
import type { LoginPayload, RegisterPayload, User } from '@/types'

/**
 * 用户登录态 Store
 * —— 登录状态由后端 HttpOnly Cookie 维护，前端只读；
 * —— 页面刷新时调用 getMe() 校验 Cookie 是否仍然有效。
 */
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(payload: LoginPayload) {
    loading.value = true
    try {
      const res = await authApi.login(payload)
      user.value = res.data
      return res
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload) {
    loading.value = true
    try {
      const res = await authApi.register(payload)
      // 注册成功后端自动登录并下发 Cookie
      user.value = res.data
      return res
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
    }
  }

  /** 页面刷新时校验当前 Cookie 是否仍然有效（401 则清空本地态）。 */
  async function hydrate() {
    try {
      const res = await authApi.getMe()
      user.value = res.data
    } catch {
      user.value = null
    }
  }

  return { user, loading, isLoggedIn, isAdmin, login, register, logout, hydrate }
})
