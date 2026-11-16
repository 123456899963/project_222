/**
 * 用户贡献接口（API_CONTRACT §4.8，S10–S13）
 */

import request from './request'
import type { ApiEnvelope, ContributionCreatePayload, ContributionItem } from '@/types'

/** POST /contributions 提交新茶 / 科普投稿（落库待审核） */
export function submitContribution(payload: ContributionCreatePayload) {
  return request.post<unknown, ApiEnvelope<ContributionItem>>('/contributions', payload)
}

/** GET /contributions/mine 我的提交记录（含状态与拒绝理由） */
export function getMyContributions() {
  return request.get<unknown, ApiEnvelope<ContributionItem[]>>('/contributions/mine')
}

/** DELETE /contributions/{id} 删除待审核提交 */
export function deleteContribution(id: number) {
  return request.delete<unknown, ApiEnvelope<null>>(`/contributions/${id}`)
}
