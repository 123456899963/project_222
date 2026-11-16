/**
 * 清单与品鉴笔记接口（API_CONTRACT §4.4，S9 多清单）
 */

import request from './request'
import type { ApiEnvelope, ListData, ListSummary, NoteUpdateData, TitleUpdateData } from '@/types'

/** GET /lists 我的全部清单摘要（默认清单置顶，首次访问自动创建） */
export function getMyLists() {
  return request.get<unknown, ApiEnvelope<ListSummary[]>>('/lists')
}

/** GET /lists/{list_id} 清单详情（含条目与当前分享） */
export function getListDetail(listId: number) {
  return request.get<unknown, ApiEnvelope<ListData>>(`/lists/${listId}`)
}

/** POST /lists 新建清单（最多 10 个） */
export function createList(title: string) {
  return request.post<unknown, ApiEnvelope<ListSummary>>('/lists', { title })
}

/** PUT /lists/{list_id} 修改清单标题 */
export function updateListTitle(listId: number, title: string) {
  return request.put<unknown, ApiEnvelope<TitleUpdateData>>(`/lists/${listId}`, { title })
}

/** DELETE /lists/{list_id} 删除清单（条目迁入默认清单，默认清单不可删） */
export function deleteList(listId: number) {
  return request.delete<unknown, ApiEnvelope<null>>(`/lists/${listId}`)
}

/** PUT /lists/{list_id}/notes/{tea_id} 保存/清空品鉴笔记 */
export function saveTastingNote(listId: number, teaId: number, content: string | null) {
  return request.put<unknown, ApiEnvelope<NoteUpdateData>>(`/lists/${listId}/notes/${teaId}`, {
    content,
  })
}
