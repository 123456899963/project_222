/**
 * 茶品只读接口（API_CONTRACT §4.2.1 ~ §4.2.6）
 * —— 全部对游客开放，本阶段无任何写操作。
 */

import request from './request'
import type {
  ApiEnvelope,
  CategoryCount,
  LatestTipItem,
  OriginCount,
  Tea,
  TeaListData,
  TeaListItem,
  TeaListParams,
  TeaMediaItem,
} from '@/types'

/** GET /teas 茶品列表（筛选 + 排序 + 分页） */
export function getTeaList(params: TeaListParams) {
  return request.get<unknown, ApiEnvelope<TeaListData>>('/teas', { params })
}

/** GET /teas/categories 七大茶类计数（固定七项顺序） */
export function getCategories() {
  return request.get<unknown, ApiEnvelope<CategoryCount[]>>('/teas/categories')
}

/** GET /teas/origins 产地选项（省级 + 计数） */
export function getOrigins() {
  return request.get<unknown, ApiEnvelope<OriginCount[]>>('/teas/origins')
}

/** GET /teas/hot 热门推荐（limit 1-20，默认 8） */
export function getHotTeas(limit = 8) {
  return request.get<unknown, ApiEnvelope<TeaListItem[]>>('/teas/hot', {
    params: { limit },
  })
}

/** GET /teas/random 随机发现（exclude_id 排除当前，避免“换一批”重复） */
export function getRandomTea(excludeId?: number) {
  return request.get<unknown, ApiEnvelope<Tea | null>>('/teas/random', {
    params: excludeId ? { exclude_id: excludeId } : {},
  })
}

/** GET /teas/{id} 茶品详情（下架返回 40401） */
export function getTeaDetail(id: number) {
  return request.get<unknown, ApiEnvelope<Tea>>(`/teas/${id}`)
}

/** GET /teas/{id}/images 茶品图片集（ADR-0003 S4）：按 sort_order 升序 */
export function getTeaImages(id: number) {
  return request.get<unknown, ApiEnvelope<TeaMediaItem[]>>(`/teas/${id}/images`)
}

/** GET /teas/{id}/related 相关推荐（S6 / API_CONTRACT §4.2.8）：limit 1-8，默认 4 */
export function getRelatedTeas(id: number, limit = 4) {
  return request.get<unknown, ApiEnvelope<TeaListItem[]>>(`/teas/${id}/related`, {
    params: { limit },
  })
}

/** GET /teas/recommended 个性化推荐（S16 / API_CONTRACT §4.2.10）：limit 1-8，默认 1 */
export function getRecommendedTeas(limit = 1, excludeId?: number) {
  return request.get<unknown, ApiEnvelope<TeaListItem[]>>('/teas/recommended', {
    params: excludeId ? { limit, exclude_id: excludeId } : { limit },
  })
}

/** GET /tips/latest 首页最新小贴士（S7 / API_CONTRACT §4.2.9）：limit 1-6，默认 3 */
export function getLatestTips(limit = 3) {
  return request.get<unknown, ApiEnvelope<LatestTipItem[]>>('/tips/latest', {
    params: { limit },
  })
}
