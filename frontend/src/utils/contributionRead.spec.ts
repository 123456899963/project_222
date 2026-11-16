import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CONTRIBUTION_READ_KEY,
  buildReadMap,
  diffUnread,
  loadReadMap,
  parseReadMap,
  saveReadMap,
} from './contributionRead'
import type { ContributionItem, ContributionStatus } from '@/types'

function item(id: number, status: ContributionStatus): ContributionItem {
  return {
    id,
    type: 'new_tea',
    status,
    target_tea_id: null,
    target_tea_name: null,
    payload: {},
    reject_reason: null,
    reviewer_id: null,
    reviewed_at: null,
    created_at: '2026-11-11T10:00:00.000Z',
  }
}

function createStorage(): Storage {
  const map = new Map<string, string>()
  return {
    get length() {
      return map.size
    },
    clear: () => map.clear(),
    getItem: (key: string) => map.get(key) ?? null,
    key: (index: number) => Array.from(map.keys())[index] ?? null,
    removeItem: (key: string) => {
      map.delete(key)
    },
    setItem: (key: string, value: string) => {
      map.set(key, value)
    },
  } as Storage
}

describe('diffUnread', () => {
  it('无记录时，所有已出结果的投稿都是新结果，待审核不计入', () => {
    const items = [item(1, 'approved'), item(2, 'rejected'), item(3, 'pending')]
    expect(diffUnread(items, {}).map((row) => row.id)).toEqual([1, 2])
  })

  it('已读状态与当前状态不同时视为新结果', () => {
    const items = [item(1, 'approved'), item(2, 'rejected')]
    const unread = diffUnread(items, { '1': 'rejected', '2': 'rejected' })
    expect(unread.map((row) => row.id)).toEqual([1])
  })

  it('全部标记已读后没有新结果', () => {
    const items = [item(1, 'approved'), item(2, 'rejected'), item(3, 'pending')]
    const readMap = buildReadMap(items)
    expect(diffUnread(items, readMap)).toEqual([])
  })
})

describe('buildReadMap', () => {
  it('只记录已出结果的投稿，待审核忽略', () => {
    const items = [item(1, 'approved'), item(2, 'pending'), item(3, 'rejected')]
    expect(buildReadMap(items)).toEqual({ '1': 'approved', '3': 'rejected' })
  })
})

describe('parseReadMap', () => {
  it('空值与损坏 JSON 返回空记录', () => {
    expect(parseReadMap(null)).toEqual({})
    expect(parseReadMap('')).toEqual({})
    expect(parseReadMap('{not json')).toEqual({})
    expect(parseReadMap('[]')).toEqual({})
  })

  it('过滤非法键与非法状态', () => {
    const raw = JSON.stringify({
      '1': 'approved',
      '2': 'pending',
      abc: 'rejected',
      '3': 'unknown',
    })
    expect(parseReadMap(raw)).toEqual({ '1': 'approved' })
  })
})

describe('localStorage 读写', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', createStorage())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('saveReadMap 写入后 loadReadMap 可还原', () => {
    saveReadMap({ '1': 'approved', '2': 'rejected' })
    expect(localStorage.getItem(CONTRIBUTION_READ_KEY)).toBe(
      JSON.stringify({ '1': 'approved', '2': 'rejected' }),
    )
    expect(loadReadMap()).toEqual({ '1': 'approved', '2': 'rejected' })
  })

  it('存储内容损坏时 loadReadMap 返回空记录，不抛错', () => {
    localStorage.setItem(CONTRIBUTION_READ_KEY, 'broken-json')
    expect(loadReadMap()).toEqual({})
  })
})
