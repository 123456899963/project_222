/**
 * 清单导出工具（纯函数 + 浏览器下载封装）
 * —— CSV 带 UTF-8 BOM，避免 Excel 打开中文乱码
 */

export interface ExportColumn {
  key: string
  label: string
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  const text = String(value)
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`
  }
  return text
}

/** 生成 CSV 文本：首行表头，含逗号/双引号/换行的字段用双引号包裹并转义 */
export function toCsv(rows: Record<string, unknown>[], columns: ExportColumn[]): string {
  const lines = [
    columns.map((column) => csvCell(column.label)).join(','),
    ...rows.map((row) => columns.map((column) => csvCell(row[column.key])).join(',')),
  ]
  return `\uFEFF${lines.join('\r\n')}`
}

/** 生成导出文件名：{标题}-{YYYYMMDD}.{ext}，标题去除文件名非法字符 */
export function buildExportFilename(
  title: string,
  ext: 'csv' | 'json',
  date: Date = new Date(),
): string {
  const safe =
    title
      .trim()
      .replace(/[\\/:*?"<>|]/g, '')
      .trim() || '我的清单'
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${safe}-${y}${m}${d}.${ext}`
}

/** 用 Blob + a[download] 触发浏览器下载 */
export function downloadTextFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
