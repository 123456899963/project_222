import { describe, expect, it } from 'vitest'
import { buildShareUrl, nextFavoriteState, nextListToggleState } from './favorite'

describe('nextFavoriteState', () => {
  it('未收藏时收藏：+1 并置为已收藏', () => {
    expect(nextFavoriteState({ is_favorited: false, favorite_count: 10 }, 'add')).toEqual({
      is_favorited: true,
      favorite_count: 11,
    })
  })

  it('已收藏时重复收藏：幂等不变', () => {
    const state = { is_favorited: true, favorite_count: 11 }
    expect(nextFavoriteState(state, 'add')).toEqual(state)
  })

  it('已收藏时取消：-1 并置为未收藏', () => {
    expect(nextFavoriteState({ is_favorited: true, favorite_count: 1 }, 'remove')).toEqual({
      is_favorited: false,
      favorite_count: 0,
    })
  })

  it('未收藏时重复取消：幂等不变', () => {
    const state = { is_favorited: false, favorite_count: 0 }
    expect(nextFavoriteState(state, 'remove')).toEqual(state)
  })

  it('取消收藏计数不会低于 0', () => {
    expect(nextFavoriteState({ is_favorited: true, favorite_count: 0 }, 'remove')).toEqual({
      is_favorited: false,
      favorite_count: 0,
    })
  })
})

describe('nextListToggleState', () => {
  it('加入首个清单：+1 且置为已收藏', () => {
    expect(
      nextListToggleState({ is_favorited: false, favorite_count: 10, list_ids: [] }, 7),
    ).toEqual({ action: 'add', list_ids: [7], is_favorited: true, favorite_count: 11 })
  })

  it('追加第二个清单：计数不变（跨清单去重口径）', () => {
    const current = { is_favorited: true, favorite_count: 11, list_ids: [7] }
    expect(nextListToggleState(current, 9)).toEqual({
      action: 'add',
      list_ids: [7, 9],
      is_favorited: true,
      favorite_count: 11,
    })
  })

  it('移出其中一个清单：仍已收藏且计数不变', () => {
    const current = { is_favorited: true, favorite_count: 11, list_ids: [7, 9] }
    expect(nextListToggleState(current, 7)).toEqual({
      action: 'remove',
      list_ids: [9],
      is_favorited: true,
      favorite_count: 11,
    })
  })

  it('移出最后一个清单：-1 且置为未收藏', () => {
    const current = { is_favorited: true, favorite_count: 11, list_ids: [7] }
    expect(nextListToggleState(current, 7)).toEqual({
      action: 'remove',
      list_ids: [],
      is_favorited: false,
      favorite_count: 10,
    })
  })

  it('取消计数不会低于 0', () => {
    const current = { is_favorited: true, favorite_count: 0, list_ids: [7] }
    expect(nextListToggleState(current, 7).favorite_count).toBe(0)
  })
})

describe('buildShareUrl', () => {
  it('拼接 origin 与 token', () => {
    expect(buildShareUrl('http://localhost:5173', 'AbCd1234')).toBe(
      'http://localhost:5173/c/AbCd1234',
    )
  })

  it('容忍 origin 末尾斜杠', () => {
    expect(buildShareUrl('https://tea.example.com/', 'AbCd1234')).toBe(
      'https://tea.example.com/c/AbCd1234',
    )
  })
})
