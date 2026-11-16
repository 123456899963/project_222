/**
 * 冲泡教程草稿生成（ADR-0005）
 *
 * 仅用于管理后台「按茶类生成草稿」按钮：把本茶的水温/投茶量/时间套进茶类通用步骤，
 * 管理员再逐条润色。正式展示内容一律以数据库中的教程为准。
 */

import type { BrewingGuide, Tea, TeaCategory } from '@/types'

type DraftSource = Pick<Tea, 'category' | 'water_temp' | 'tea_amount' | 'brew_time'>

const CATEGORY_DEFAULTS: Record<TeaCategory, [number, number, number]> = {
  green: [85, 3, 60],
  white: [90, 5, 45],
  yellow: [85, 3, 60],
  red: [95, 5, 30],
  oolong: [100, 7, 20],
  dark: [100, 7, 20],
  reprocessed: [90, 5, 30],
}

const CATEGORY_INTRO: Record<TeaCategory, string> = {
  green: '绿茶重在鲜爽，用玻璃杯或盖碗，水温不宜过高，不闷盖、快出汤。',
  white: '白茶工艺轻，新茶清甜、老茶醇厚，水温略高于绿茶，耐泡度好。',
  yellow: '黄茶比绿茶多一道闷黄，香气清甜，水温稍高但要避免久闷。',
  red: '红茶全发酵，甜香明显，水温 90–95℃、出汤要快，避免酸涩。',
  oolong: '乌龙半发酵，香气高扬，必须沸水、快出汤，盖碗最合适。',
  dark: '黑茶后发酵，醇厚耐泡，需沸水并先洗茶，泡淡后还可煮饮。',
  reprocessed: '再加工茶以基础茶坯窨制或调配而成，香气突出，水温适中、出汤要快，避免香气散失。',
}

const CATEGORY_CAUTION: Record<TeaCategory, string> = {
  green: '不要用刚烧开的沸水直冲，也不要盖盖子闷泡，否则容易苦涩发黄。',
  white: '新白茶不要长时间闷泡；老白茶可先快速润茶一次再正式冲泡。',
  yellow: '黄茶芽叶细嫩，不建议洗茶，水温控制在 85–90℃ 即可。',
  red: '不要用持续沸腾的水猛冲茶叶，出汤后不留汤底，避免下一泡发酸。',
  oolong: '水温不足香气出不来；每一泡都要出尽茶汤，不留汤底。',
  dark: '务必用沸水；洗茶动作要快，避免滋味流失，泡淡后可加水煮饮。',
  reprocessed: '水温过高或久闷都会让花香变闷、茶汤发苦，出汤要快，尽量不倒净后久置。',
}

const POUR_HINT: Record<TeaCategory, string> = {
  green: '水烧开后开盖晾 2–3 分钟，大约就是 85℃。',
  white: '新茶用 90℃ 左右，老白茶可以用 100℃ 沸水激发陈香。',
  yellow: '水温比绿茶略高一点，但不要用沸水直冲。',
  red: '水沸后稍等片刻再冲，持续沸腾的水容易让茶发酸。',
  oolong: '必须用沸水高冲，水温不足香气出不来。',
  dark: '必须用沸水，洗茶 1–2 次后再正式冲泡。',
  reprocessed: '花茶用 85–90℃ 热水更护花香，调味茶可用 90℃ 左右。',
}

const BREW_HINT: Record<TeaCategory, string> = {
  green: '不要盖盖子闷，绿茶闷久了会发黄发苦。',
  white: '出汤后打开碗盖，避免闷出涩味。',
  yellow: '黄茶不建议洗茶，第一泡就是精华。',
  red: '红茶出汤要快，久泡会苦涩。',
  oolong: '每泡都出尽，留汤底会闷苦，影响下一泡。',
  dark: '洗茶要快，久留会流失滋味。',
  reprocessed: '出汤要比基础茶更快，久泡容易苦涩、花香发闷。',
}

function formatNumber(value: number | null | undefined, fallback: number): string {
  const num = value ?? fallback
  return Number.isInteger(num) ? String(num) : num.toFixed(1)
}

export function buildBrewingDraft(tea: DraftSource): BrewingGuide {
  const [defaultTemp, defaultAmount, defaultTime] = CATEGORY_DEFAULTS[tea.category]
  const temp = formatNumber(tea.water_temp, defaultTemp)
  const amount = formatNumber(tea.tea_amount, defaultAmount)
  const seconds = formatNumber(tea.brew_time, defaultTime)

  return {
    intro: CATEGORY_INTRO[tea.category],
    steps: [
      {
        title: '温杯洁具',
        detail: '先用热水把茶具烫洗一遍并倒掉，既清洁又能提升杯温，便于闻香。',
        tip: '玻璃杯、盖碗或紫砂壶都可以，新手优先用玻璃杯或白瓷盖碗。',
      },
      {
        title: '投茶',
        detail: `取 ${amount}g 茶叶放入茶具，约占杯底或碗底薄薄一层。`,
        tip: '口味偏淡可先少放一点，觉得太淡再逐次增加。',
      },
      {
        title: '注水',
        detail: `用 ${temp}℃ 热水沿杯壁缓慢注入至七分满，不要直冲茶叶。`,
        tip: POUR_HINT[tea.category],
      },
      {
        title: '出汤',
        detail: `静置约 ${seconds} 秒即可出汤，尽量把茶汤倒干净。`,
        tip: BREW_HINT[tea.category],
      },
      {
        title: '继续续泡',
        detail: '每次比上一泡多等 5–10 秒，通常可续 3–5 次。',
        tip: '茶汤明显变淡、香气变弱时就可以换茶了。',
      },
      {
        title: '细品滋味',
        detail: '小口慢饮，先闻香再入口，感受回甘与喉韵。',
        tip: '茶汤降到 50–60℃ 时甜味更容易被尝出来。',
      },
    ],
    caution: CATEGORY_CAUTION[tea.category],
  }
}
