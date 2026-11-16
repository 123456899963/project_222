/**
 * 收藏接口（API_CONTRACT §4.3）
 */

import request from './request'
import type { ApiEnvelope, FavoriteState } from '@/types'

/** POST /favorites/{tea_id} 收藏（幂等）；不传 listId 时归入默认清单 */
export function addFavorite(teaId: number, listId?: number) {
  return request.post<unknown, ApiEnvelope<FavoriteState>>(
    `/favorites/${teaId}`,
    listId ? { list_id: listId } : undefined,
  )
}

/** DELETE /favorites/{tea_id} 取消收藏（幂等）；不传 listId 时移除所有清单中的该茶 */
export function removeFavorite(teaId: number, listId?: number) {
  return request.delete<unknown, ApiEnvelope<FavoriteState>>(`/favorites/${teaId}`, {
    params: listId ? { list_id: listId } : undefined,
  })
}

/** GET /favorites/{tea_id}/status 收藏状态 */
export function getFavoriteStatus(teaId: number) {
  return request.get<unknown, ApiEnvelope<FavoriteState>>(`/favorites/${teaId}/status`)
}
