import { describe, expect, it } from 'vitest'
import { PURCHASE_KEYWORD_MAX_LENGTH, buildTaobaoSearchUrl } from './purchase'

describe('buildTaobaoSearchUrl', () => {
  it('中文茶名按关键词拼接到淘宝搜索页', () => {
    expect(buildTaobaoSearchUrl('西湖龙井')).toBe(
      `https://s.taobao.com/search?q=${encodeURIComponent('西湖龙井')}`,
    )
  })

  it('特殊字符被完整转义，不会截断查询参数', () => {
    const url = buildTaobaoSearchUrl('白毫银针 & 特级 #1 100%') as string
    expect(url.startsWith('https://s.taobao.com/search?q=')).toBe(true)
    expect(url).not.toContain(' ')
    expect(url).toContain(encodeURIComponent('白毫银针 & 特级 #1 100%'))
  })

  it('首尾空白会被去除', () => {
    expect(buildTaobaoSearchUrl('  正山小种  ')).toBe(
      `https://s.taobao.com/search?q=${encodeURIComponent('正山小种')}`,
    )
  })

  it('空字符串或纯空白返回 null，入口应隐藏', () => {
    expect(buildTaobaoSearchUrl('')).toBeNull()
    expect(buildTaobaoSearchUrl('   ')).toBeNull()
  })

  it('超长茶名按上限截断', () => {
    const url = buildTaobaoSearchUrl('茶'.repeat(PURCHASE_KEYWORD_MAX_LENGTH + 20)) as string
    expect(decodeURIComponent(url.replace('https://s.taobao.com/search?q=', ''))).toHaveLength(
      PURCHASE_KEYWORD_MAX_LENGTH,
    )
  })
})
