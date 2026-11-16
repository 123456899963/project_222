import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCategories, getOrigins, getTeaList } from '@/api/teas'
import type { CategoryCount, OriginCount, TeaListItem, TeaListParams } from '@/types'

/**
 * 茶品数据 Store（只读）
 * —— 列表请求参数一律由后端处理（筛选/搜索/排序/分页），前端不做本地过滤
 * —— 茶类计数与产地选项为全站共享数据，首次加载后缓存
 */
export const useTeaStore = defineStore('tea', () => {
  const list = ref<TeaListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(12)
  const loading = ref(false)
  const error = ref('')

  const categories = ref<CategoryCount[]>([])
  const origins = ref<OriginCount[]>([])
  let categoriesLoaded = false
  let originsLoaded = false

  /** 拉取列表；并发请求只采纳最后一次，避免快速切换筛选时的竞态 */
  let requestSeq = 0

  async function fetchList(params: TeaListParams) {
    const seq = ++requestSeq
    loading.value = true
    error.value = ''
    try {
      const res = await getTeaList(params)
      if (seq !== requestSeq) return
      list.value = res.data?.items ?? []
      total.value = res.data?.total ?? 0
      page.value = res.data?.page ?? 1
      pageSize.value = res.data?.page_size ?? 12
    } catch (err) {
      if (seq !== requestSeq) return
      list.value = []
      total.value = 0
      error.value = err instanceof Error ? err.message : '加载失败'
    } finally {
      if (seq === requestSeq) loading.value = false
    }
  }

  async function fetchCategories(force = false) {
    if (categoriesLoaded && !force) return
    const res = await getCategories()
    categories.value = res.data ?? []
    categoriesLoaded = true
  }

  async function fetchOrigins(force = false) {
    if (originsLoaded && !force) return
    const res = await getOrigins()
    origins.value = res.data ?? []
    originsLoaded = true
  }

  return {
    list,
    total,
    page,
    pageSize,
    loading,
    error,
    categories,
    origins,
    fetchList,
    fetchCategories,
    fetchOrigins,
  }
})
