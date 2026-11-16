/**
 * 投稿审核结果已读标记（localStorage，纯前端）
 * —— 只记录已出结果（approved / rejected）的投稿状态
 * —— 状态变化或首次出现即视为「新结果」
 * —— localStorage 不可用或 JSON 损坏时一律安全降级为空记录
 */

import type { ContributionItem, ContributionStatus } from '@/types'

export const CONTRIBUTION_READ_KEY = 'tea-guide:contribution-read'

/** 已读记录：投稿 ID → 已读时的审核状态 */
export type ContributionReadMap = Record<string, ContributionStatus>

function isResultStatus(status: ContributionStatus): boolean {
  return status === 'approved' || status === 'rejected'
}

/** 解析已读记录；非对象、字段非法或 JSON 损坏时返回空记录 */
export function parseReadMap(raw: string | null): ContributionReadMap {
  if (!raw) return {}
  try {
    const data = JSON.parse(raw)
    if (!data || typeof data !== 'object' || Array.isArray(data)) return {}
    const map: ContributionReadMap = {}
    for (const [id, status] of Object.entries(data)) {
      if (!/^\d+$/.test(id)) continue
      if (status === 'approved' || status === 'rejected') map[id] = status
    }
    return map
  } catch {
    return {}
  }
}

/** 当前状态为已出结果、且未读过（或已读状态与当前不同）的投稿 */
export function diffUnread(
  items: ContributionItem[],
  readMap: ContributionReadMap,
): ContributionItem[] {
  return items.filter((item) => {
    if (!isResultStatus(item.status)) return false
    return readMap[String(item.id)] !== item.status
  })
}

/** 汇总当前所有已出结果的投稿状态，用于整体标记已读 */
export function buildReadMap(items: ContributionItem[]): ContributionReadMap {
  const map: ContributionReadMap = {}
  for (const item of items) {
    if (isResultStatus(item.status)) map[String(item.id)] = item.status
  }
  return map
}

function storage(): Storage | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage
  } catch {
    return null
  }
}

export function loadReadMap(): ContributionReadMap {
  try {
    return parseReadMap(storage()?.getItem(CONTRIBUTION_READ_KEY) ?? null)
  } catch {
    return {}
  }
}

export function saveReadMap(readMap: ContributionReadMap): void {
  const store = storage()
  if (!store) return
  try {
    store.setItem(CONTRIBUTION_READ_KEY, JSON.stringify(readMap))
  } catch {
    // 隐私模式或超出配额时静默失败，不影响页面展示
  }
}
