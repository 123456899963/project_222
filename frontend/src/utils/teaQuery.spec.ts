import { describe, expect, it } from 'vitest'
import {
  buildListParams,
  defaultTeaFilterState,
  listActiveFilters,
  parseRouteQuery,
  serializeFilterState,
} from './teaQuery'
import type { TeaFilterState } from './teaQuery'

describe('parseRouteQuery', () => {
  it('解析逗号分隔的多选维度', () => {
    const state = parseRouteQuery({ category: 'green,white', origin: '浙江,福建', season: '明前' })
    expect(state.categories).toEqual(['green', 'white'])
    expect(state.origins).toEqual(['浙江', '福建'])
    expect(state.seasons).toEqual(['明前'])
  })

  it('丢弃非法茶类、非法季节与重复值', () => {
    const state = parseRouteQuery({ category: 'green,black,green', season: '明前,不明' })
    expect(state.categories).toEqual(['green'])
    expect(state.seasons).toEqual(['明前'])
  })

  it('sort 仅接受 favorite，其余回退 newest', () => {
    expect(parseRouteQuery({ sort: 'favorite' }).sort).toBe('favorite')
    expect(parseRouteQuery({ sort: 'hot' }).sort).toBe('newest')
    expect(parseRouteQuery({}).sort).toBe('newest')
  })

  it('page 非法时回退 1', () => {
    expect(parseRouteQuery({ page: '3' }).page).toBe(3)
    expect(parseRouteQuery({ page: '0' }).page).toBe(1)
    expect(parseRouteQuery({ page: '-2' }).page).toBe(1)
    expect(parseRouteQuery({ page: 'abc' }).page).toBe(1)
  })

  it('关键词去空格并截断到 50 字符', () => {
    expect(parseRouteQuery({ q: '  龙井  ' }).keyword).toBe('龙井')
    expect(parseRouteQuery({ q: 'a'.repeat(60) }).keyword).toHaveLength(50)
  })

  it('数组型 query 取第一个值', () => {
    expect(parseRouteQuery({ q: ['龙井', '白茶'] }).keyword).toBe('龙井')
  })

  it('解析发酵程度与价格区间', () => {
    const state = parseRouteQuery({
      fermentation: '不发酵,半发酵,不明',
      price_min: '300',
      price_max: '1000',
    })
    expect(state.fermentations).toEqual(['不发酵', '半发酵'])
    expect(state.priceMin).toBe(300)
    expect(state.priceMax).toBe(1000)
  })

  it('价格上下限倒置时自动交换', () => {
    const state = parseRouteQuery({ price_min: '1000', price_max: '300' })
    expect(state.priceMin).toBe(300)
    expect(state.priceMax).toBe(1000)
  })

  it('价格非法时降级为不限，mode 仅接受 or', () => {
    const state = parseRouteQuery({ price_min: '-1', price_max: 'abc', mode: 'or' })
    expect(state.priceMin).toBeNull()
    expect(state.priceMax).toBeNull()
    expect(state.filterMode).toBe('or')
    expect(parseRouteQuery({ mode: 'xor' }).filterMode).toBe('and')
  })
})

describe('serializeFilterState', () => {
  it('默认状态不产出任何参数（保持 URL 干净）', () => {
    expect(serializeFilterState(defaultTeaFilterState())).toEqual({})
  })

  it('多选维度以逗号拼接', () => {
    const state: TeaFilterState = { ...defaultTeaFilterState(), categories: ['green', 'red'] }
    expect(serializeFilterState(state)).toEqual({ category: 'green,red' })
  })

  it('非默认排序与页码写入 URL', () => {
    const state = { ...defaultTeaFilterState(), sort: 'favorite' as const, page: 2 }
    expect(serializeFilterState(state)).toEqual({ sort: 'favorite', page: '2' })
  })

  it('与 parseRouteQuery 往返一致', () => {
    const state: TeaFilterState = {
      ...defaultTeaFilterState(),
      categories: ['green', 'white'],
      origins: ['浙江'],
      seasons: ['明前'],
      fermentations: ['不发酵'],
      priceMin: 300,
      priceMax: 1000,
      filterMode: 'or',
      keyword: '龙井',
      sort: 'favorite',
      page: 3,
    }
    expect(parseRouteQuery(serializeFilterState(state))).toEqual(state)
  })
})

describe('buildListParams', () => {
  it('默认每页 12 条并保留排序与页码', () => {
    expect(buildListParams(defaultTeaFilterState())).toEqual({
      sort: 'newest',
      page: 1,
      page_size: 12,
    })
  })

  it('关键词映射为 API 字段 keyword，空值不下发', () => {
    const params = buildListParams({
      ...defaultTeaFilterState(),
      keyword: '龙井',
    })
    expect(params.keyword).toBe('龙井')
    expect(params.category).toBeUndefined()
    expect(params.origin).toBeUndefined()
    expect(params.season).toBeUndefined()
  })

  it('多选维度以逗号拼接交给后端', () => {
    const params = buildListParams({
      ...defaultTeaFilterState(),
      categories: ['green', 'red'],
      origins: ['浙江', '福建'],
      seasons: ['明前'],
    })
    expect(params.category).toBe('green,red')
    expect(params.origin).toBe('浙江,福建')
    expect(params.season).toBe('明前')
  })

  it('发酵/价格/组合模式映射到 API 字段', () => {
    const params = buildListParams({
      ...defaultTeaFilterState(),
      fermentations: ['不发酵'],
      priceMin: 300,
      priceMax: 1000,
      filterMode: 'or',
    })
    expect(params.fermentation).toBe('不发酵')
    expect(params.price_min).toBe(300)
    expect(params.price_max).toBe(1000)
    expect(params.filter_mode).toBe('or')
  })

  it('默认组合模式不下发 filter_mode', () => {
    const params = buildListParams(defaultTeaFilterState())
    expect(params.filter_mode).toBeUndefined()
    expect(params.price_min).toBeUndefined()
    expect(params.price_max).toBeUndefined()
  })
})

describe('listActiveFilters', () => {
  it('输出已选条件标签，茶类使用中文名', () => {
    const filters = listActiveFilters({
      ...defaultTeaFilterState(),
      categories: ['green'],
      origins: ['浙江'],
      seasons: ['明前'],
      fermentations: ['不发酵'],
    })
    expect(filters).toEqual([
      { dimension: 'categories', value: 'green', label: '绿茶' },
      { dimension: 'origins', value: '浙江', label: '浙江' },
      { dimension: 'seasons', value: '明前', label: '明前' },
      { dimension: 'fermentations', value: '不发酵', label: '不发酵' },
    ])
  })
})
