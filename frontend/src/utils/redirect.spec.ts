import { describe, expect, it } from 'vitest'
import { buildLoginRedirect, resolveLoginRedirect } from './redirect'

describe('buildLoginRedirect', () => {
  it('保留 pathname 与 query，不做预编码', () => {
    expect(buildLoginRedirect('/teas/3', '?from=home')).toBe('/teas/3?from=home')
    expect(buildLoginRedirect('/my', '')).toBe('/my')
  })

  it('非站内路径回退首页', () => {
    expect(buildLoginRedirect('https://evil.test', '')).toBe('/')
  })
})

describe('resolveLoginRedirect', () => {
  it('接受站内路径（含 query / hash）', () => {
    expect(resolveLoginRedirect('/teas/3?from=home')).toBe('/teas/3?from=home')
    expect(resolveLoginRedirect('/my#list-2')).toBe('/my#list-2')
    expect(resolveLoginRedirect('/')).toBe('/')
  })

  it('拒绝双重编码遗留值（登录后不再 404）', () => {
    expect(resolveLoginRedirect('%2Fteas%2F3%3Ffrom%3Dhome')).toBe('/')
    expect(resolveLoginRedirect('%252Fteas%252F3')).toBe('/')
  })

  it('拒绝开放重定向与非字符串', () => {
    expect(resolveLoginRedirect('//evil.test')).toBe('/')
    expect(resolveLoginRedirect('https://evil.test')).toBe('/')
    expect(resolveLoginRedirect(undefined)).toBe('/')
    expect(resolveLoginRedirect(null)).toBe('/')
    expect(resolveLoginRedirect(['/my'])).toBe('/')
  })
})
