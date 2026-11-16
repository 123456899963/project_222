import { describe, expect, it } from 'vitest'
import { buildBrewingDraft } from './brewing'
import type { TeaCategory } from '@/types'

const CATEGORIES: TeaCategory[] = [
  'green',
  'white',
  'yellow',
  'red',
  'oolong',
  'dark',
  'reprocessed',
]

describe('buildBrewingDraft', () => {
  it('七大茶类都生成 6 步且字段非空', () => {
    for (const category of CATEGORIES) {
      const guide = buildBrewingDraft({ category, water_temp: 90, tea_amount: 5, brew_time: 30 })
      expect(guide.steps).toHaveLength(6)
      expect(guide.intro).toBeTruthy()
      expect(guide.caution).toBeTruthy()
      for (const step of guide.steps) {
        expect(step.title.trim()).not.toBe('')
        expect(step.detail.trim()).not.toBe('')
      }
    }
  })

  it('使用本茶参数生成注水与出汤文案', () => {
    const guide = buildBrewingDraft({
      category: 'green',
      water_temp: 82.5,
      tea_amount: 3.5,
      brew_time: 75,
    })
    expect(guide.steps[1].detail).toContain('3.5g')
    expect(guide.steps[2].detail).toContain('82.5℃')
    expect(guide.steps[3].detail).toContain('75 秒')
  })

  it('参数缺失时使用茶类默认值', () => {
    const guide = buildBrewingDraft({
      category: 'oolong',
      water_temp: null,
      tea_amount: null,
      brew_time: null,
    })
    expect(guide.steps[1].detail).toContain('7g')
    expect(guide.steps[2].detail).toContain('100℃')
    expect(guide.steps[3].detail).toContain('20 秒')
  })

  it('整数参数不出现多余小数', () => {
    const guide = buildBrewingDraft({
      category: 'red',
      water_temp: 95,
      tea_amount: 5,
      brew_time: 30,
    })
    expect(guide.steps[2].detail).toContain('95℃')
    expect(guide.steps[1].detail).toContain('5g')
  })
})
