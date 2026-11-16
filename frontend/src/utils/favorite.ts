/**
 * 收藏状态纯函数（供 FavoriteButton 乐观更新与 Vitest 使用）
 */

export interface FavoriteSnapshot {
  is_favorited: boolean
  favorite_count: number
}

/**
 * 计算乐观更新后的状态：
 * - 已收藏再次收藏、未收藏再次取消均保持原状态（与后端幂等一致）
 * - 取消收藏时计数不低于 0
 */
export function nextFavoriteState(
  current: FavoriteSnapshot,
  action: 'add' | 'remove',
): FavoriteSnapshot {
  if (action === 'add') {
    if (current.is_favorited) return current
    return { is_favorited: true, favorite_count: current.favorite_count + 1 }
  }
  if (!current.is_favorited) return current
  return { is_favorited: false, favorite_count: Math.max(0, current.favorite_count - 1) }
}

/**
 * S9 多清单：按清单维度切换收藏的乐观状态（含跨清单去重的计数联动）。
 * 计数仅在 is_favorited 翻转时变化：加入首个清单 +1，移出最后一个清单 -1，
 * 在已收藏基础上追加/移出非最后一个清单时计数不变（favorite_count 为「用户 × 茶品」去重口径）。
 */
export function nextListToggleState(
  current: FavoriteSnapshot & { list_ids: number[] },
  listId: number,
): {
  action: 'add' | 'remove'
  list_ids: number[]
  is_favorited: boolean
  favorite_count: number
} {
  const contained = current.list_ids.includes(listId)
  const list_ids = contained
    ? current.list_ids.filter((id) => id !== listId)
    : [...current.list_ids, listId]
  const is_favorited = list_ids.length > 0
  let favorite_count = current.favorite_count
  if (is_favorited && !current.is_favorited) favorite_count += 1
  if (!is_favorited && current.is_favorited) favorite_count = Math.max(0, favorite_count - 1)
  return { action: contained ? 'remove' : 'add', list_ids, is_favorited, favorite_count }
}

/** 拼装分享链接（origin 末尾斜杠容错） */
export function buildShareUrl(origin: string, token: string): string {
  return `${origin.replace(/\/+$/, '')}/c/${token}`
}
