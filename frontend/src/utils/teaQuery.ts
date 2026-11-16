/**
 * 茶品列表筛选状态与 URL 参数的双向同步（纯函数，供 Vitest 覆盖）
 *
 * URL 参数约定（PAGE_SPECS §4.2 + PRD S1/S2）：
 * category / origin / season / fermentation（均逗号分隔多值）、
 * price_min / price_max（元/斤）、mode（and|or）、q（关键词）、
 * sort（newest|favorite）、page（页码）。
 * API 参数见 API_CONTRACT §4.2.1（关键词参数名为 keyword）。
 */

import type { TeaCategory, TeaListParams, TeaSort } from '@/types'

export const TEA_CATEGORIES = [
  'green',
  'white',
  'yellow',
  'red',
  'oolong',
  'dark',
  'reprocessed',
] as const

export const TEA_SEASONS = ['明前', '雨前', '春茶', '夏茶', '秋茶', '冬茶'] as const

/** 发酵程度（S2）：与后端 FERMENTATION_VALUES 保持一致 */
export const TEA_FERMENTATIONS = ['不发酵', '微发酵', '半发酵', '全发酵', '后发酵'] as const

/** 茶类展示名（API_CONTRACT §1.8 字典） */
export const CATEGORY_LABELS: Record<TeaCategory, string> = {
  green: '绿茶',
  white: '白茶',
  yellow: '黄茶',
  red: '红茶',
  oolong: '乌龙茶',
  dark: '黑茶',
  reprocessed: '再加工茶',
}

export const DEFAULT_PAGE_SIZE = 12
export const MAX_KEYWORD_LEN = 50

/** 列表页筛选状态（与 URL 参数一一对应） */
export interface TeaFilterState {
  categories: TeaCategory[]
  origins: string[]
  seasons: string[]
  fermentations: string[]
  /** 价格下限（元/斤），null 表示不限 */
  priceMin: number | null
  /** 价格上限（元/斤），null 表示不限 */
  priceMax: number | null
  /** 跨维度组合方式（S1）：and 同时满足 / or 任一满足 */
  filterMode: 'and' | 'or'
  keyword: string
  sort: TeaSort
  page: number
}

export function defaultTeaFilterState(): TeaFilterState {
  return {
    categories: [],
    origins: [],
    seasons: [],
    fermentations: [],
    priceMin: null,
    priceMax: null,
    filterMode: 'and',
    keyword: '',
    sort: 'newest',
    page: 1,
  }
}

type RawQueryValue = string | null | undefined | Array<string | null | undefined>

function firstValue(raw: RawQueryValue): string {
  if (Array.isArray(raw)) return raw[0] ?? ''
  return raw ?? ''
}

function splitCsv(raw: RawQueryValue): string[] {
  return firstValue(raw)
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

function dedupe<T>(list: T[]): T[] {
  return [...new Set(list)]
}

/** 解析非负整数；非法值返回 null（价格区间降级为「不限」） */
function parseNonNegativeInt(raw: string): number | null {
  if (!raw) return null
  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value >= 0 ? value : null
}

/** 解析路由 query → 筛选状态（非法值静默丢弃，与后端校验解耦） */
export function parseRouteQuery(query: Record<string, RawQueryValue>): TeaFilterState {
  const state = defaultTeaFilterState()

  state.categories = dedupe(
    splitCsv(query.category).filter((c): c is TeaCategory =>
      (TEA_CATEGORIES as readonly string[]).includes(c),
    ),
  )
  state.origins = dedupe(splitCsv(query.origin))
  state.seasons = dedupe(
    splitCsv(query.season).filter((s) => (TEA_SEASONS as readonly string[]).includes(s)),
  )
  state.fermentations = dedupe(
    splitCsv(query.fermentation).filter((f) =>
      (TEA_FERMENTATIONS as readonly string[]).includes(f),
    ),
  )

  const priceMin = parseNonNegativeInt(firstValue(query.price_min))
  const priceMax = parseNonNegativeInt(firstValue(query.price_max))
  // 上下限倒置时交换，避免把非法区间下发给后端
  if (priceMin != null && priceMax != null && priceMin > priceMax) {
    state.priceMin = priceMax
    state.priceMax = priceMin
  } else {
    state.priceMin = priceMin
    state.priceMax = priceMax
  }

  state.filterMode = firstValue(query.mode) === 'or' ? 'or' : 'and'
  state.keyword = firstValue(query.q).trim().slice(0, MAX_KEYWORD_LEN)
  state.sort = firstValue(query.sort) === 'favorite' ? 'favorite' : 'newest'

  const page = Number.parseInt(firstValue(query.page), 10)
  state.page = Number.isFinite(page) && page >= 1 ? page : 1

  return state
}

/** 筛选状态 → 路由 query（默认值省略，保持 URL 干净） */
export function serializeFilterState(state: TeaFilterState): Record<string, string> {
  const query: Record<string, string> = {}
  if (state.categories.length) query.category = state.categories.join(',')
  if (state.origins.length) query.origin = state.origins.join(',')
  if (state.seasons.length) query.season = state.seasons.join(',')
  if (state.fermentations.length) query.fermentation = state.fermentations.join(',')
  if (state.priceMin != null) query.price_min = String(state.priceMin)
  if (state.priceMax != null) query.price_max = String(state.priceMax)
  if (state.filterMode !== 'and') query.mode = state.filterMode
  if (state.keyword) query.q = state.keyword
  if (state.sort !== 'newest') query.sort = state.sort
  if (state.page > 1) query.page = String(state.page)
  return query
}

/** 筛选状态 → API 请求参数（API_CONTRACT §4.2.1，关键词参数名 keyword） */
export function buildListParams(
  state: TeaFilterState,
  pageSize: number = DEFAULT_PAGE_SIZE,
): TeaListParams {
  const params: TeaListParams = {
    sort: state.sort,
    page: state.page,
    page_size: pageSize,
  }
  if (state.categories.length) params.category = state.categories.join(',')
  if (state.origins.length) params.origin = state.origins.join(',')
  if (state.seasons.length) params.season = state.seasons.join(',')
  if (state.fermentations.length) params.fermentation = state.fermentations.join(',')
  if (state.priceMin != null) params.price_min = state.priceMin
  if (state.priceMax != null) params.price_max = state.priceMax
  if (state.filterMode !== 'and') params.filter_mode = state.filterMode
  if (state.keyword) params.keyword = state.keyword
  return params
}

/** 已选条件标签（用于 pill 展示与单独移除） */
export interface ActiveFilter {
  dimension: 'categories' | 'origins' | 'seasons' | 'fermentations'
  value: string
  label: string
}

export function listActiveFilters(state: TeaFilterState): ActiveFilter[] {
  return [
    ...state.categories.map((v) => ({
      dimension: 'categories' as const,
      value: v,
      label: CATEGORY_LABELS[v],
    })),
    ...state.origins.map((v) => ({ dimension: 'origins' as const, value: v, label: v })),
    ...state.seasons.map((v) => ({ dimension: 'seasons' as const, value: v, label: v })),
    ...state.fermentations.map((v) => ({
      dimension: 'fermentations' as const,
      value: v,
      label: v,
    })),
  ]
}
