import { describe, expect, it } from 'vitest'
import { buildExportFilename, toCsv, type ExportColumn } from './export'

const columns: ExportColumn[] = [
  { key: 'name', label: '茶名' },
  { key: 'origin', label: '产地' },
]

function stripBom(text: string): string {
  return text.replace(/^\uFEFF/, '')
}

describe('toCsv', () => {
  it('首行为表头，并以 BOM 开头', () => {
    const csv = toCsv([{ name: '西湖龙井', origin: '浙江杭州' }], columns)
    expect(csv.startsWith('\uFEFF')).toBe(true)
    expect(stripBom(csv).split('\r\n')).toEqual(['茶名,产地', '西湖龙井,浙江杭州'])
  })

  it('字段含逗号时用双引号包裹', () => {
    const csv = toCsv([{ name: '拼配茶', origin: '杭州,西湖' }], columns)
    expect(stripBom(csv).split('\r\n')[1]).toBe('拼配茶,"杭州,西湖"')
  })

  it('字段含双引号时转义为两个双引号', () => {
    const csv = toCsv([{ name: '称"特级"的茶', origin: '福建' }], columns)
    expect(stripBom(csv).split('\r\n')[1]).toBe('"称""特级""的茶",福建')
  })

  it('字段含换行时用双引号包裹', () => {
    const csv = toCsv([{ name: '第一行\n第二行', origin: '云南' }], columns)
    expect(stripBom(csv).split('\r\n')[1]).toBe('"第一行\n第二行",云南')
  })

  it('空值输出空字符串（不加引号）', () => {
    const csv = toCsv([{ name: '白茶', origin: null }], columns)
    expect(stripBom(csv).split('\r\n')[1]).toBe('白茶,')
    const csvUndefined = toCsv([{ name: '黄茶' }], columns)
    expect(stripBom(csvUndefined).split('\r\n')[1]).toBe('黄茶,')
  })

  it('无数据时仅输出表头', () => {
    const csv = toCsv([], columns)
    expect(stripBom(csv)).toBe('茶名,产地')
  })
})

describe('buildExportFilename', () => {
  it('包含标题与 YYYYMMDD 日期', () => {
    const date = new Date(2026, 10, 9)
    expect(buildExportFilename('我的私房茶单', 'csv', date)).toBe('我的私房茶单-20261109.csv')
    expect(buildExportFilename('我的私房茶单', 'json', date)).toBe('我的私房茶单-20261109.json')
  })

  it('去除文件名非法字符，空标题兜底', () => {
    const date = new Date(2026, 0, 1)
    expect(buildExportFilename('a/b:c*?"<>|', 'csv', date)).toBe('abc-20260101.csv')
    expect(buildExportFilename('   ', 'json', date)).toBe('我的清单-20260101.json')
  })
})
