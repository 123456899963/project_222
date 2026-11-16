import { describe, expect, it } from 'vitest'
import { buildCompareMatrix } from './compare'
import { TEA_CATEGORIES } from './teaQuery'
import type { Tea } from '@/types'

function makeTea(partial: Partial<Tea>): Tea {
  return {
    id: 1,
    name: '示例茶',
    category: 'green',
    origin: '浙江',
    shape_desc: '扁平挺直',
    soup_desc: '清澈明亮',
    aroma_desc: '清香',
    taste_desc: '鲜爽',
    water_temp: 85,
    tea_amount: 3,
    brew_time: 60,
    is_active: true,
    favorite_count: 0,
    created_at: '2026-11-09T00:00:00Z',
    updated_at: '2026-11-09T00:00:00Z',
    ...partial,
  }
}

describe('buildCompareMatrix', () => {
  it('列顺序固定为七大茶类，行结构完整', () => {
    const rows = buildCompareMatrix({})
    expect(rows.map((r) => r.label)).toEqual([
      '代表茶',
      '外形',
      '汤色',
      '香气',
      '滋味',
      '水温',
      '投茶量',
    ])
    for (const row of rows) {
      expect(row.values).toHaveLength(TEA_CATEGORIES.length)
    }
  })

  it('缺失茶类列全部为 null（展示为 —）', () => {
    const rows = buildCompareMatrix({ green: makeTea({ name: '西湖龙井' }) })
    const nameRow = rows.find((r) => r.label === '代表茶')!
    expect(nameRow.values[0]).toBe('西湖龙井')
    expect(nameRow.values[TEA_CATEGORIES.indexOf('white')]).toBeNull()
  })

  it('数值字段拼接单位，空文本归一化为 null', () => {
    const rows = buildCompareMatrix({
      oolong: makeTea({ category: 'oolong', water_temp: 95, tea_amount: 5, soup_desc: '  ' }),
    })
    const idx = TEA_CATEGORIES.indexOf('oolong')
    expect(rows.find((r) => r.label === '水温')!.values[idx]).toBe('95℃')
    expect(rows.find((r) => r.label === '投茶量')!.values[idx]).toBe('5g')
    expect(rows.find((r) => r.label === '汤色')!.values[idx]).toBeNull()
  })
})
