/**
 * 浏览历史（localStorage，纯前端）
 * —— 按 tea_id 去重、最新在前、最多 50 条
 * —— localStorage 不可用或 JSON 损坏时一律安全降级为空数组
 */

export const VIEW_HISTORY_KEY = 'tea-guide:view-history'
export const VIEW_HISTORY_LIMIT = 50

export interface ViewHistoryItem {
  tea_id: number
  name: string
  category: string
  cover_image: string | null
  viewed_at: string
}

function isHistoryItem(value: unknown): value is ViewHistoryItem {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  return (
    Number.isInteger(item.tea_id) &&
    (item.tea_id as number) > 0 &&
    typeof item.name === 'string' &&
    typeof item.category === 'string' &&
    typeof item.viewed_at === 'string' &&
    (item.cover_image === null || typeof item.cover_image === 'string')
  )
}

/** 解析原始存储内容；非数组或 JSON 损坏时返回空数组 */
export function parseHistory(raw: string | null): ViewHistoryItem[] {
  if (!raw) return []
  try {
    const data = JSON.parse(raw)
    if (!Array.isArray(data)) return []
    return data.filter(isHistoryItem).slice(0, VIEW_HISTORY_LIMIT)
  } catch {
    return []
  }
}

/** 插入一条记录：同 tea_id 去重、最新在最前、最多 limit 条 */
export function mergeHistory(
  list: ViewHistoryItem[],
  item: ViewHistoryItem,
  limit: number = VIEW_HISTORY_LIMIT,
): ViewHistoryItem[] {
  const rest = list.filter((row) => row.tea_id !== item.tea_id)
  return [item, ...rest].slice(0, limit)
}

function storage(): Storage | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage
  } catch {
    return null
  }
}

export function getHistory(): ViewHistoryItem[] {
  try {
    return parseHistory(storage()?.getItem(VIEW_HISTORY_KEY) ?? null)
  } catch {
    return []
  }
}

export function addHistory(item: ViewHistoryItem): void {
  const store = storage()
  if (!store) return
  try {
    store.setItem(VIEW_HISTORY_KEY, JSON.stringify(mergeHistory(getHistory(), item)))
  } catch {
    // 隐私模式或超出配额时静默失败，不影响详情页展示
  }
}

export function clearHistory(): void {
  try {
    storage()?.removeItem(VIEW_HISTORY_KEY)
  } catch {
    // 同上：存储不可写时忽略
  }
}
