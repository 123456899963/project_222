/**
 * 登录回跳地址处理。
 *
 * Vue Router 会对 query 自动编解码；调用方只传原始站内路径，
 * 若提前 encodeURIComponent 会造成双重编码，登录后跳到 /%2F... 触发 404。
 */

/** 从浏览器地址栏取当前站内路径（pathname + search），作为 401 后的回跳目标。 */
export function buildLoginRedirect(pathname: string, search: string): string {
  const target = `${pathname}${search}`
  return target.startsWith('/') ? target : '/'
}

/**
 * 校验登录/注册页 query 中的 redirect。
 *
 * 仅接受以单个 `/` 开头的站内路径；协议相对地址（`//evil.com`）、
 * 绝对 URL、历史遗留的双重编码值一律回退首页，避免开放重定向与 404。
 */
export function resolveLoginRedirect(raw: unknown): string {
  if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) {
    return '/'
  }
  return raw
}
