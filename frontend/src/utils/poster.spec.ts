import { describe, expect, it } from 'vitest'
import { POSTER_MAX_TEAS, buildPosterFilename, pickPosterTeaNames, truncateText } from './poster'

describe('pickPosterTeaNames', () => {
  it('按顺序取非空茶名并默认最多 6 个', () => {
    const items = Array.from({ length: 9 }, (_, i) => ({ name: `茶${i + 1}` }))
    const names = pickPosterTeaNames(items)
    expect(names).toHaveLength(POSTER_MAX_TEAS)
    expect(names[0]).toBe('茶1')
    expect(names[5]).toBe('茶6')
  })

  it('过滤空名并去重', () => {
    const names = pickPosterTeaNames([
      { name: ' 西湖龙井 ' },
      { name: '' },
      { name: '西湖龙井' },
      { name: '白毫银针' },
    ])
    expect(names).toEqual(['西湖龙井', '白毫银针'])
  })

  it('支持自定义上限', () => {
    expect(pickPosterTeaNames([{ name: 'A' }, { name: 'B' }, { name: 'C' }], 2)).toEqual(['A', 'B'])
  })
})

describe('truncateText', () => {
  it('未超长时原样返回（去首尾空格）', () => {
    expect(truncateText('  我的茶单  ', 6)).toBe('我的茶单')
  })

  it('超长时按字符截断并补省略号', () => {
    expect(truncateText('一二三四五六七八', 5)).toBe('一二三四…')
  })
})

describe('buildPosterFilename', () => {
  it('包含清单名与日期', () => {
    const date = new Date(2026, 10, 9)
    expect(buildPosterFilename('我的茶单', date)).toBe('茶图鉴-我的茶单-20261109.png')
  })

  it('替换文件名非法字符并兜底默认名', () => {
    const date = new Date(2026, 0, 1)
    expect(buildPosterFilename('a/b:c*?', date)).toBe('茶图鉴-a-b-c-20260101.png')
    expect(buildPosterFilename('   ', date)).toBe('茶图鉴-我的茶单-20260101.png')
  })
})
