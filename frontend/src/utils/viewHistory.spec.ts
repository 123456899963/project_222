import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  VIEW_HISTORY_KEY,
  VIEW_HISTORY_LIMIT,
  addHistory,
  clearHistory,
  getHistory,
  mergeHistory,
  parseHistory,
  type ViewHistoryItem,
} from './viewHistory'

function item(teaId: number, viewedAt = '2026-11-11T10:00:00.000Z'): ViewHistoryItem {
  return {
    tea_id: teaId,
    name: `茶${teaId}`,
    category: 'green',
    cover_image: null,
    viewed_at: viewedAt,
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

describe('mergeHistory', () => {
  it('同 tea_id 去重，最新记录排在最前', () => {
    const merged = mergeHistory([item(1), item(2)], item(1, '2026-11-12T10:00:00.000Z'))
    expect(merged.map((row) => row.tea_id)).toEqual([1, 2])
    expect(merged[0].viewed_at).toBe('2026-11-12T10:00:00.000Z')
  })

  it('最多保留 50 条，超出时丢弃最旧记录', () => {
    const list = Array.from({ length: VIEW_HISTORY_LIMIT }, (_, i) => item(i + 1))
    const merged = mergeHistory(list, item(999))
    expect(merged).toHaveLength(VIEW_HISTORY_LIMIT)
    expect(merged[0].tea_id).toBe(999)
    expect(merged.some((row) => row.tea_id === VIEW_HISTORY_LIMIT)).toBe(false)
  })
})

describe('parseHistory', () => {
  it('空值与损坏 JSON 返回空数组', () => {
    expect(parseHistory(null)).toEqual([])
    expect(parseHistory('')).toEqual([])
    expect(parseHistory('{not json')).toEqual([])
    expect(parseHistory('{"a":1}')).toEqual([])
  })

  it('过滤结构非法的条目', () => {
    const raw = JSON.stringify([
      item(1),
      { tea_id: '2', name: '坏数据', category: 'red', cover_image: null, viewed_at: 'x' },
      { tea_id: 3, name: '缺字段' },
    ])
    expect(parseHistory(raw).map((row) => row.tea_id)).toEqual([1])
  })
})

describe('localStorage 读写', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', createStorage())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('addHistory 写入并按 tea_id 去重、最新在前', () => {
    addHistory(item(1, '2026-11-10T10:00:00.000Z'))
    addHistory(item(2, '2026-11-11T10:00:00.000Z'))
    addHistory(item(1, '2026-11-11T12:00:00.000Z'))

    const history = getHistory()
    expect(history.map((row) => row.tea_id)).toEqual([1, 2])
    expect(history[0].viewed_at).toBe('2026-11-11T12:00:00.000Z')
  })

  it('存储内容损坏时 getHistory 返回空数组，不抛错', () => {
    localStorage.setItem(VIEW_HISTORY_KEY, 'broken-json')
    expect(getHistory()).toEqual([])
  })

  it('clearHistory 清空记录', () => {
    addHistory(item(1))
    clearHistory()
    expect(getHistory()).toEqual([])
    expect(localStorage.getItem(VIEW_HISTORY_KEY)).toBeNull()
  })
})
