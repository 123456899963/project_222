/**
 * 清单相关纯函数（Vitest 覆盖）
 */

/** 标题规则：trim 后 2–20 个字符（与后端 services/lists.py 一致） */
export function isValidListTitle(title: string): boolean {
  const normalized = title.trim()
  return normalized.length >= 2 && normalized.length <= 20
}

/** 笔记字数展示（按字符计，最多 20,000） */
export function noteLength(text: string | null | undefined): number {
  return (text ?? '').length
}

export function isNoteWithinLimit(text: string | null | undefined): boolean {
  return noteLength(text) <= 20000
}
