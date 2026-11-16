/** 内容板块 API（批次五 R1–R5 / API_CONTRACT §4.2.10–11） */

import request from './request'
import type { ContentItem, ContentListData, ContentListParams, ContentTypeItem } from '@/types'

/** 板块分类列表（游客，无认证） */
export function getContentTypes(): Promise<ContentTypeItem[]> {
  return request.get<ContentTypeItem[]>('/content-types').then((res) => res.data ?? [])
}

/** 内容列表（游客，无认证） */
export function getContentList(params?: ContentListParams): Promise<ContentListData> {
  return request
    .get<ContentListData>('/contents', { params })
    .then((res) => res.data ?? { items: [], total: 0, page: 1, page_size: 12 })
}

/** 内容详情（游客，无认证） */
export function getContentDetail(id: number): Promise<ContentItem> {
  return request.get<ContentItem>(`/contents/${id}`).then((res) => res.data as ContentItem)
}
