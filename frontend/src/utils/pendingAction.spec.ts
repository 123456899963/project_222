import { describe, expect, it } from 'vitest'
import { PENDING_ACTION_TTL_MS, parsePendingAction, serializePendingAction } from './pendingAction'

const NOW = 1_800_000_000_000

describe('pendingAction', () => {
  it('序列化后可被解析还原', () => {
    const raw = serializePendingAction({ type: 'note', teaId: 6, path: '/teas/6' }, NOW)
    expect(parsePendingAction(raw, NOW)).toEqual({ type: 'note', teaId: 6, path: '/teas/6' })
  })

  it('支持 share 类型', () => {
    const raw = serializePendingAction({ type: 'share', teaId: 3, path: '/teas/3' }, NOW)
    expect(parsePendingAction(raw, NOW)?.type).toBe('share')
  })

  it('超过 30 分钟视为过期', () => {
    const raw = serializePendingAction({ type: 'note', teaId: 1, path: '/teas/1' }, NOW)
    expect(parsePendingAction(raw, NOW + PENDING_ACTION_TTL_MS + 1)).toBeNull()
  })

  it('未知类型、非法茶品 ID、非法路径均返回 null', () => {
    expect(
      parsePendingAction(JSON.stringify({ type: 'favorite', teaId: 1, path: '/', ts: NOW }), NOW),
    ).toBeNull()
    expect(
      parsePendingAction(JSON.stringify({ type: 'note', teaId: 0, path: '/', ts: NOW }), NOW),
    ).toBeNull()
    expect(
      parsePendingAction(JSON.stringify({ type: 'note', teaId: 1, path: 'teas/1', ts: NOW }), NOW),
    ).toBeNull()
  })

  it('空值或损坏 JSON 返回 null', () => {
    expect(parsePendingAction(null, NOW)).toBeNull()
    expect(parsePendingAction('{', NOW)).toBeNull()
  })
})
