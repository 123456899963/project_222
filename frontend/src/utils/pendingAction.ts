/**
 * 登录前暂存的待执行动作（T1-02 pending_action）。
 *
 * 场景：游客在茶品详情页点击「写笔记」或「分享」→ 跳转登录 →
 * 登录成功回到原页面后自动继续原动作。
 *
 * 仅存于 sessionStorage，30 分钟过期；解析失败一律视为无动作。
 */

export type PendingActionType = 'note' | 'share'

export interface PendingAction {
  type: PendingActionType
  teaId: number
  path: string
}

const STORAGE_KEY = 'pending_action'
export const PENDING_ACTION_TTL_MS = 30 * 60 * 1000

export function serializePendingAction(action: PendingAction, now = Date.now()): string {
  return JSON.stringify({ ...action, ts: now })
}

export function parsePendingAction(raw: string | null, now = Date.now()): PendingAction | null {
  if (!raw) return null
  try {
    const data = JSON.parse(raw) as Partial<PendingAction> & { ts?: unknown }
    if (data.type !== 'note' && data.type !== 'share') return null
    if (!Number.isInteger(data.teaId) || (data.teaId as number) < 1) return null
    if (typeof data.path !== 'string' || !data.path.startsWith('/')) return null
    if (typeof data.ts !== 'number' || now - data.ts > PENDING_ACTION_TTL_MS) return null
    return { type: data.type, teaId: data.teaId as number, path: data.path }
  } catch {
    return null
  }
}

function storage(): Storage | null {
  try {
    return typeof sessionStorage === 'undefined' ? null : sessionStorage
  } catch {
    return null
  }
}

export function savePendingAction(action: PendingAction): void {
  storage()?.setItem(STORAGE_KEY, serializePendingAction(action))
}

export function loadPendingAction(): PendingAction | null {
  return parsePendingAction(storage()?.getItem(STORAGE_KEY) ?? null)
}

export function clearPendingAction(): void {
  storage()?.removeItem(STORAGE_KEY)
}
