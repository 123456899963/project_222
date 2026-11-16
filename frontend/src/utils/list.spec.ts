import { describe, expect, it } from 'vitest'
import { isNoteWithinLimit, isValidListTitle, noteLength } from './list'

describe('isValidListTitle', () => {
  it('2–20 字有效（含 trim）', () => {
    expect(isValidListTitle('茶单')).toBe(true)
    expect(isValidListTitle('  我的私房茶单  ')).toBe(true)
    expect(isValidListTitle('茶'.repeat(20))).toBe(true)
  })

  it('边界外无效', () => {
    expect(isValidListTitle('')).toBe(false)
    expect(isValidListTitle('茶')).toBe(false)
    expect(isValidListTitle('   ')).toBe(false)
    expect(isValidListTitle('茶'.repeat(21))).toBe(false)
  })
})

describe('noteLength / isNoteWithinLimit', () => {
  it('空值按 0 处理', () => {
    expect(noteLength(null)).toBe(0)
    expect(noteLength(undefined)).toBe(0)
  })

  it('20,000 字以内有效，超出无效', () => {
    expect(isNoteWithinLimit('好'.repeat(20000))).toBe(true)
    expect(isNoteWithinLimit('好'.repeat(20001))).toBe(false)
  })
})
