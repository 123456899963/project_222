import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'success' | 'warning' | 'error' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
}

const DURATION_MS = 3000

/**
 * Toast 通知 Store
 * —— 前台自研轻量提示（不依赖 Element Plus），由 AppToast 统一渲染
 */
export const useToastStore = defineStore('toast', () => {
  const items = ref<ToastItem[]>([])
  let seq = 0

  function remove(id: number) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  function push(type: ToastType, message: string) {
    const id = ++seq
    items.value.push({ id, type, message })
    window.setTimeout(() => remove(id), DURATION_MS)
  }

  function success(message: string) {
    push('success', message)
  }
  function warn(message: string) {
    push('warning', message)
  }
  function error(message: string) {
    push('error', message)
  }
  function info(message: string) {
    push('info', message)
  }

  return { items, remove, success, warn, error, info }
})
