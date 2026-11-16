/**
 * 购买入口（PRD 2026-11-11 决策）：仅按茶名跳转淘宝搜索结果页，
 * 不接入商品、下单与支付，本站不参与交易（X10 边界外链）。
 */

const TAOBAO_SEARCH_BASE = 'https://s.taobao.com/search?q='

/** 搜索关键词上限，超长截断，避免 URL 过长被平台拒绝 */
export const PURCHASE_KEYWORD_MAX_LENGTH = 50

/**
 * 由茶名生成淘宝搜索 URL。
 * @returns 茶名为空（或纯空白）时返回 null，调用方应隐藏入口。
 */
export function buildTaobaoSearchUrl(name: string): string | null {
  const keyword = (name ?? '').trim().slice(0, PURCHASE_KEYWORD_MAX_LENGTH)
  if (!keyword) return null
  return `${TAOBAO_SEARCH_BASE}${encodeURIComponent(keyword)}`
}
