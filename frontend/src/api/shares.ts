/**
 * 分享接口（API_CONTRACT §4.5）
 */

import request from './request'
import type {
  ApiEnvelope,
  CopyResult,
  ShareGenerateData,
  ShareRevokeData,
  ShareViewData,
} from '@/types'

/** POST /shares/generate 生成或复用分享令牌；不传 listId 时分享默认清单 */
export function generateShare(listId?: number) {
  return request.post<unknown, ApiEnvelope<ShareGenerateData>>(
    '/shares/generate',
    listId ? { list_id: listId } : undefined,
  )
}

/** POST /shares/revoke/{token} 撤销分享（不可逆） */
export function revokeShare(token: string) {
  return request.post<unknown, ApiEnvelope<ShareRevokeData>>(`/shares/revoke/${token}`)
}

/** GET /shares/{token} 公开查看分享清单（游客可访问） */
export function getShareView(token: string) {
  return request.get<unknown, ApiEnvelope<ShareViewData>>(`/shares/${token}`)
}

/** POST /shares/{token}/copy 一键收藏全部 */
export function copyShare(token: string) {
  return request.post<unknown, ApiEnvelope<CopyResult>>(`/shares/${token}/copy`)
}
