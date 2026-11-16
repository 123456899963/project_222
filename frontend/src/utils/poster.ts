/**
 * 分享海报（S8）：纯前端 canvas 绘制 + 二维码，不落服务端存储。
 * —— 颜色/字体全部读取 CSS 变量（style.css 是唯一 Token 文件）
 * —— 纯函数（取茶名、截断、文件名）抽出便于 Vitest 覆盖
 */

export const POSTER_WIDTH = 750
export const POSTER_HEIGHT = 1000
export const POSTER_MAX_TEAS = 6

export interface PosterTea {
  name: string
}

export interface PosterOptions {
  title: string
  shareUrl: string
  teaNames: string[]
  teaCount: number
  createdAt?: string
}

/** 取前 N 个非空茶名（保持原顺序，去重） */
export function pickPosterTeaNames(items: PosterTea[], max = POSTER_MAX_TEAS): string[] {
  const result: string[] = []
  for (const item of items) {
    const name = (item.name ?? '').trim()
    if (!name || result.includes(name)) continue
    result.push(name)
    if (result.length >= max) break
  }
  return result
}

/** 按字符截断（中文安全），超长补省略号 */
export function truncateText(text: string, max: number): string {
  const chars = Array.from(text.trim())
  if (chars.length <= max) return chars.join('')
  return `${chars.slice(0, Math.max(0, max - 1)).join('')}…`
}

/** 生成下载文件名：茶图鉴-清单名-YYYYMMDD.png */
export function buildPosterFilename(title: string, date: Date = new Date()): string {
  const safe =
    title
      .trim()
      .replace(/[\\/:*?"<>|\s]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 20) || '我的茶单'
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `茶图鉴-${safe}-${y}${m}${d}.png`
}

function cssVar(name: string): string {
  if (typeof window === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/** 在 750×1000 画布上绘制海报并返回 PNG Blob */
export async function renderSharePoster(options: PosterOptions): Promise<Blob> {
  const { default: QRCode } = await import('qrcode')

  const primary = cssVar('--color-primary')
  const primaryDark = cssVar('--color-primary-dark')
  const surface = cssVar('--color-bg-surface')
  const page = cssVar('--color-bg-page') || surface
  const muted = cssVar('--color-bg-muted')
  const textPrimary = cssVar('--color-text-primary')
  const textSecondary = cssVar('--color-text-secondary')
  const fontDisplay = cssVar('--font-display') || 'serif'
  const fontBody = cssVar('--font-body') || 'sans-serif'

  const qrOptions: Record<string, unknown> = { width: 320, margin: 1 }
  if (primary && surface) qrOptions.color = { dark: primary, light: surface }
  const qrDataUrl = await QRCode.toDataURL(options.shareUrl, qrOptions)

  const canvas = document.createElement('canvas')
  canvas.width = POSTER_WIDTH
  canvas.height = POSTER_HEIGHT
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('当前浏览器不支持 canvas')

  // 背景
  ctx.fillStyle = page
  ctx.fillRect(0, 0, POSTER_WIDTH, POSTER_HEIGHT)

  // 顶部色带
  ctx.fillStyle = primary
  ctx.fillRect(0, 0, POSTER_WIDTH, 10)

  // 装饰圆
  ctx.globalAlpha = 0.12
  ctx.fillStyle = primary
  ctx.beginPath()
  ctx.arc(POSTER_WIDTH - 70, 120, 120, 0, Math.PI * 2)
  ctx.fill()
  ctx.globalAlpha = 1

  // 站点名
  ctx.fillStyle = primaryDark || primary
  ctx.font = `500 24px ${fontBody}`
  ctx.textBaseline = 'top'
  ctx.fillText('茶 · 图 鉴', 64, 64)

  // 清单标题
  ctx.fillStyle = textPrimary
  ctx.font = `700 48px ${fontDisplay}`
  ctx.fillText(truncateText(options.title, 12), 64, 130)

  // 副标题
  ctx.fillStyle = textSecondary
  ctx.font = `400 22px ${fontBody}`
  const dateText = options.createdAt ? ` · 分享于 ${options.createdAt}` : ''
  ctx.fillText(`共 ${options.teaCount} 款茶${dateText}`, 64, 200)

  // 分隔线
  ctx.strokeStyle = muted
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(64, 258)
  ctx.lineTo(POSTER_WIDTH - 64, 258)
  ctx.stroke()

  // 茶名列表
  const names = pickPosterTeaNames(options.teaNames.map((name) => ({ name })))
  ctx.textBaseline = 'middle'
  names.forEach((name, index) => {
    const y = 320 + index * 76

    ctx.fillStyle = primary
    ctx.globalAlpha = 0.14
    ctx.beginPath()
    ctx.arc(88, y, 22, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalAlpha = 1

    ctx.fillStyle = primaryDark || primary
    ctx.font = `600 20px ${fontBody}`
    ctx.textAlign = 'center'
    ctx.fillText(String(index + 1), 88, y + 1)
    ctx.textAlign = 'left'

    ctx.fillStyle = textPrimary
    ctx.font = `500 30px ${fontDisplay}`
    ctx.fillText(truncateText(name, 16), 128, y + 1)
  })

  if (options.teaCount > names.length) {
    ctx.fillStyle = textSecondary
    ctx.font = `400 22px ${fontBody}`
    ctx.fillText(`等 ${options.teaCount} 款好茶`, 128, 320 + names.length * 76)
  }

  // 底部卡片
  const cardY = POSTER_HEIGHT - 260
  ctx.fillStyle = surface
  ctx.fillRect(48, cardY, POSTER_WIDTH - 96, 200)

  const qr = new Image()
  qr.src = qrDataUrl
  await new Promise<void>((resolve, reject) => {
    qr.onload = () => resolve()
    qr.onerror = () => reject(new Error('二维码绘制失败'))
  })
  ctx.drawImage(qr, 84, cardY + 22, 150, 150)

  ctx.fillStyle = textPrimary
  ctx.font = `600 28px ${fontBody}`
  ctx.textBaseline = 'top'
  ctx.fillText('扫码查看这份茶单', 268, cardY + 66)

  ctx.fillStyle = textSecondary
  ctx.font = `400 20px ${fontBody}`
  const host = safeHost(options.shareUrl)
  if (host) ctx.fillText(host, 268, cardY + 112)

  ctx.fillStyle = primary
  ctx.fillRect(0, POSTER_HEIGHT - 8, POSTER_WIDTH, 8)

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('海报生成失败'))
    }, 'image/png')
  })
}

function safeHost(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return ''
  }
}

/** 生成海报并触发浏览器下载 */
export async function downloadSharePoster(options: PosterOptions): Promise<void> {
  const blob = await renderSharePoster(options)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = buildPosterFilename(options.title)
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
