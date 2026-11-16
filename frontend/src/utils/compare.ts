/**
 * 七大茶类摘要对比（S3）：纯函数组装对比矩阵，供 Vitest 覆盖。
 *
 * 数据来源：每个茶类取一款代表茶（收藏最多），再取其详情。
 * 列顺序固定为 TEA_CATEGORIES；某茶类无代表茶时该列全部为 null。
 */

import type { Tea, TeaCategory } from '@/types'
import { TEA_CATEGORIES } from './teaQuery'

export interface CompareRow {
  /** 行标题，如「汤色」 */
  label: string
  /** 与 TEA_CATEGORIES 一一对应的单元格文案，null 表示「—」 */
  values: Array<string | null>
}

export type CompareMap = Partial<Record<TeaCategory, Tea | null>>

function formatText(value: string | null | undefined): string | null {
  const text = (value ?? '').trim()
  return text || null
}

function formatNumber(value: number | null | undefined, unit: string): string | null {
  return value != null ? `${value}${unit}` : null
}

/** 组装七列对比矩阵（列顺序固定） */
export function buildCompareMatrix(teas: CompareMap): CompareRow[] {
  const columns = TEA_CATEGORIES.map((category) => teas[category] ?? null)
  const row = (label: string, pick: (tea: Tea | null) => string | null): CompareRow => ({
    label,
    values: columns.map(pick),
  })

  return [
    row('代表茶', (tea) => (tea ? tea.name : null)),
    row('外形', (tea) => formatText(tea?.shape_desc)),
    row('汤色', (tea) => formatText(tea?.soup_desc)),
    row('香气', (tea) => formatText(tea?.aroma_desc)),
    row('滋味', (tea) => formatText(tea?.taste_desc)),
    row('水温', (tea) => formatNumber(tea?.water_temp, '℃')),
    row('投茶量', (tea) => formatNumber(tea?.tea_amount, 'g')),
  ]
}
