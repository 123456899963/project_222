"""为存量茶品生成冲泡教程草稿（ADR-0005）

幂等：只为还没有教程的茶品插入草稿，重复执行不会覆盖管理员已编辑的内容。
草稿 = 茶类通用手法模板 + 本茶水温/投茶量/浸泡时间；管理员可在后台逐款润色。

用法：
    python -m app.scripts.seed_brewing_guides [--dry-run]
"""

from __future__ import annotations

import argparse
from typing import Any

from app.core.database import SessionLocal
from app.models.tea import Tea, TeaBrewingGuide

# 各茶类默认参数：茶品未维护对应字段时兜底（页面标注为参考值）
CATEGORY_DEFAULTS: dict[str, tuple[float, float, float]] = {
    "green": (85.0, 3.0, 60.0),
    "white": (90.0, 5.0, 45.0),
    "yellow": (85.0, 3.0, 60.0),
    "red": (95.0, 5.0, 30.0),
    "oolong": (100.0, 7.0, 20.0),
    "dark": (100.0, 7.0, 20.0),
    "reprocessed": (90.0, 5.0, 30.0),
}

CATEGORY_INTRO: dict[str, str] = {
    "green": "绿茶重在鲜爽，用玻璃杯或盖碗，水温不宜过高，不闷盖、快出汤。",
    "white": "白茶工艺轻，新茶清甜、老茶醇厚，水温略高于绿茶，耐泡度好。",
    "yellow": "黄茶比绿茶多一道闷黄，香气清甜，水温稍高但要避免久闷。",
    "red": "红茶全发酵，甜香明显，水温 90–95℃、出汤要快，避免酸涩。",
    "oolong": "乌龙半发酵，香气高扬，必须沸水、快出汤，盖碗最合适。",
    "dark": "黑茶后发酵，醇厚耐泡，需沸水并先洗茶，泡淡后还可煮饮。",
    "reprocessed": "再加工茶以基础茶坯窨制或调配而成，香气突出，水温适中、出汤要快，避免香气散失。",
}

CATEGORY_CAUTION: dict[str, str] = {
    "green": "不要用刚烧开的沸水直冲，也不要盖盖子闷泡，否则容易苦涩发黄。",
    "white": "新白茶不要长时间闷泡；老白茶可先快速润茶一次再正式冲泡。",
    "yellow": "黄茶芽叶细嫩，不建议洗茶，水温控制在 85–90℃ 即可。",
    "red": "不要用持续沸腾的水猛冲茶叶，出汤后不留汤底，避免下一泡发酸。",
    "oolong": "水温不足香气出不来；每一泡都要出尽茶汤，不留汤底。",
    "dark": "务必用沸水；洗茶动作要快，避免滋味流失，泡淡后可加水煮饮。",
    "reprocessed": "水温过高或久闷都会让花香变闷、茶汤发苦，出汤要快，尽量不倒净后久置。",
}


def _num(value: float) -> str:
    """数值展示：整数去掉小数点，其余保留一位。"""
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def _steps(category: str, temp: float, amount: float, seconds: float) -> list[dict[str, Any]]:
    t, a, s = _num(temp), _num(amount), _num(seconds)
    common_head = {
        "title": "温杯洁具",
        "detail": "先用热水把茶具烫洗一遍并倒掉，既清洁又能提升杯温，便于闻香。",
        "tip": "玻璃杯、盖碗或紫砂壶都可以，新手优先用玻璃杯或白瓷盖碗。",
    }

    if category == "green":
        body = [
            common_head,
            {
                "title": "投茶",
                "detail": f"取 {a}g 绿茶放入杯中，约占杯底薄薄一层即可。",
                "tip": "口味偏淡可从 2g 开始，觉得太淡再逐次增加。",
            },
            {
                "title": "注水",
                "detail": f"用 {t}℃ 热水沿杯壁缓慢注入至七分满，不要直冲茶叶。",
                "tip": "水烧开后开盖晾 2–3 分钟，大约就是 85℃。",
            },
            {
                "title": "出汤品饮",
                "detail": f"静置约 {s} 秒即可饮用，喝到剩三分之一时再续水。",
                "tip": "不要盖盖子闷，绿茶闷久了会发黄发苦。",
            },
            {
                "title": "继续续水",
                "detail": "每次续水后比上一泡多等 10–15 秒，一般可续 2–3 次。",
                "tip": "茶汤明显变淡、香气变弱时就可以换茶了。",
            },
            {
                "title": "细品滋味",
                "detail": "小口慢饮，先闻香再入口，感受鲜爽与回甘。",
                "tip": "茶汤降到 50–60℃ 时甜味更容易被尝出来。",
            },
        ]
    elif category == "white":
        body = [
            common_head,
            {
                "title": "投茶",
                "detail": f"取 {a}g 白茶放入盖碗，芽叶蓬松时约占碗身三分之一。",
                "tip": "白毫银针可少放，寿眉、贡眉可适当多放。",
            },
            {
                "title": "注水",
                "detail": f"用 {t}℃ 热水沿碗壁注入至八分满，新茶可略低、老茶可用沸水。",
                "tip": "老白茶用 100℃ 沸水更能泡出枣香和药香。",
            },
            {
                "title": "出汤",
                "detail": f"第一泡约 {s} 秒出汤，尽量把茶汤倒干净。",
                "tip": "出汤后打开碗盖，避免闷出涩味。",
            },
            {
                "title": "续泡",
                "detail": "之后每泡在上一次基础上增加 10 秒，通常可泡 5–6 次。",
                "tip": "老白茶泡到味淡后，还可以加水煮 3–5 分钟。",
            },
            {
                "title": "品饮",
                "detail": "先闻毫香或陈香，再小口品尝，感受清甜与喉韵。",
                "tip": "新茶偏清甜，老茶偏醇厚，可以对比着喝。",
            },
        ]
    elif category == "yellow":
        body = [
            common_head,
            {
                "title": "投茶",
                "detail": f"取 {a}g 黄茶放入玻璃杯或盖碗，芽叶细嫩不必放太多。",
                "tip": "黄芽茶投茶量可略少，黄大茶可略多。",
            },
            {
                "title": "注水",
                "detail": f"用 {t}℃ 热水沿杯壁注入至七分满，让茶叶自然舒展。",
                "tip": "水温比绿茶略高一点，但不要用沸水直冲。",
            },
            {
                "title": "出汤",
                "detail": f"静置约 {s} 秒后饮用，不要长时间闷泡。",
                "tip": "黄茶不建议洗茶，第一泡就是精华。",
            },
            {
                "title": "续泡",
                "detail": "每次续水比上一泡多等 10 秒左右，可续 2–3 次。",
                "tip": "茶汤变淡后不必强求，及时换茶口感更好。",
            },
            {
                "title": "品饮",
                "detail": "闻清甜香气，小口感受柔和汤感与回甘。",
                "tip": "黄茶香气内敛，杯温稍高时闻香更明显。",
            },
        ]
    elif category == "red":
        body = [
            common_head,
            {
                "title": "投茶",
                "detail": f"取 {a}g 红茶放入盖碗，约占碗底三分之一。",
                "tip": "喜欢浓一点可加到 6g，但出汤时间要相应缩短。",
            },
            {
                "title": "注水",
                "detail": f"用 {t}℃ 热水沿碗壁环绕注入至八分满，避免直冲。",
                "tip": "水沸后稍等片刻再冲，持续沸腾的水容易让茶发酸。",
            },
            {
                "title": "出汤",
                "detail": f"约 {s} 秒后出汤，尽量一次倒净，不留汤底。",
                "tip": "红茶出汤要快，久泡会苦涩。",
            },
            {
                "title": "续泡",
                "detail": "之后每泡增加 5–10 秒，通常可泡 4–5 次。",
                "tip": "小种、金骏眉偏嫩，出汤可更快；滇红可稍慢。",
            },
            {
                "title": "品饮",
                "detail": "闻蜜香或花果香，小口感受甜醇与顺滑。",
                "tip": "清饮最能体会红茶本味，加奶加糖按个人喜好。",
            },
        ]
    elif category == "oolong":
        body = [
            {
                "title": "温杯烫盏",
                "detail": "用沸水把盖碗和公道杯彻底烫热，倒掉水后趁热投茶。",
                "tip": "盖碗容量建议 110–130ml，新手更好控制出汤。",
            },
            {
                "title": "投茶",
                "detail": f"取 {a}g 乌龙茶放入盖碗，约占碗身三分之一到二分之一。",
                "tip": "球型乌龙可少放，条索型乌龙可适当多放。",
            },
            {
                "title": "润茶醒香",
                "detail": f"用 {t}℃ 沸水高冲注满，刮去浮沫后立即倒掉，唤醒茶香。",
                "tip": "润茶动作要快，1–2 秒即可，不必久留。",
            },
            {
                "title": "正式出汤",
                "detail": f"再次注满沸水，约 {s} 秒后出汤，务必倒尽。",
                "tip": "每泡都留汤底会闷苦，影响下一泡。",
            },
            {
                "title": "续泡",
                "detail": "每泡比上一泡增加 5 秒左右，优质乌龙可泡 6–8 次。",
                "tip": "香气变弱、汤感变薄时再考虑换茶。",
            },
            {
                "title": "闻香品饮",
                "detail": "出汤后先闻盖香，再小口品尝，感受花香与喉韵。",
                "tip": "趁热闻盖香，凉了香气会散。",
            },
        ]
    elif category == "reprocessed":
        body = [
            common_head,
            {
                "title": "投茶",
                "detail": f"取 {a}g 再加工茶放入盖碗或玻璃杯，花茶可略少，调味茶按口味调整。",
                "tip": "花茶投茶量过多容易发苦，建议从少量开始。",
            },
            {
                "title": "注水",
                "detail": f"用 {t}℃ 热水沿杯壁注入至七分满，让香气缓慢释放。",
                "tip": "花茶不宜用持续沸腾的水猛冲，避免花香被烫散。",
            },
            {
                "title": "出汤",
                "detail": f"静置约 {s} 秒即可出汤，尽量一次倒净，不留汤底。",
                "tip": "再加工茶久泡易苦涩，出汤要比基础茶更快。",
            },
            {
                "title": "续泡",
                "detail": "之后每泡增加 10 秒左右，通常可续 2–3 次。",
                "tip": "花香明显变淡后即可换茶，不必强求多泡。",
            },
            {
                "title": "闻香品饮",
                "detail": "先闻杯中或盖上的香气，再小口品尝，感受花香与茶底的融合。",
                "tip": "茶汤温度降到 60℃ 左右时花香更清晰。",
            },
        ]
    else:  # dark
        body = [
            {
                "title": "温壶洁具",
                "detail": "用沸水把紫砂壶或盖碗彻底烫热，倒掉水后趁热投茶。",
                "tip": "黑茶耐高温，紫砂壶保温性更好。",
            },
            {
                "title": "投茶",
                "detail": f"取 {a}g 黑茶放入壶中，约占壶身五分之一到三分之一。",
                "tip": "砖茶、饼茶先撬散，块太大不易出味。",
            },
            {
                "title": "洗茶",
                "detail": f"用 {t}℃ 沸水注满后立即倒掉，重复 1–2 次。",
                "tip": "洗茶要快，久留会流失滋味。",
            },
            {
                "title": "冲泡出汤",
                "detail": f"再次注满沸水，约 {s} 秒后出汤，尽量倒净。",
                "tip": "前几泡出汤要快，后面再逐步延长时间。",
            },
            {
                "title": "续泡",
                "detail": "每泡增加 10 秒左右，通常可泡 8–10 次。",
                "tip": "泡到汤色变浅、味道变淡后可转煮饮。",
            },
            {
                "title": "煮饮收尾",
                "detail": "把叶底加水煮沸后转小火煮 3–5 分钟，别有一番醇厚。",
                "tip": "煮饮时水不要放太多，避免过淡。",
            },
        ]

    return body


def build_guide(tea: Tea) -> dict[str, Any]:
    default_temp, default_amount, default_time = CATEGORY_DEFAULTS.get(tea.category, (90, 5, 60))
    temp = float(tea.water_temp) if tea.water_temp is not None else default_temp
    amount = float(tea.tea_amount) if tea.tea_amount is not None else default_amount
    seconds = float(tea.brew_time) if tea.brew_time is not None else default_time
    return {
        "intro": CATEGORY_INTRO.get(tea.category, "按步骤操作，新手也能稳定泡出好喝的茶。"),
        "steps": _steps(tea.category, temp, amount, seconds),
        "caution": CATEGORY_CAUTION.get(tea.category, "水温与出汤时间按本茶参数调整。"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="为存量茶品生成冲泡教程草稿")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        teas = (
            db.query(Tea)
            .outerjoin(TeaBrewingGuide, TeaBrewingGuide.tea_id == Tea.id)
            .filter(TeaBrewingGuide.id.is_(None))
            .order_by(Tea.id.asc())
            .all()
        )
        print(f"待生成教程的茶品：{len(teas)} 款")
        if args.dry_run or not teas:
            return

        for tea in teas:
            db.add(TeaBrewingGuide(tea_id=tea.id, **build_guide(tea)))
        db.commit()
        print(f"已生成教程草稿：{len(teas)} 款（已有教程的茶品未覆盖）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
