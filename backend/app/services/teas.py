"""茶品业务层：参数解析/校验、分页夹取、DTO 组装（不拼 SQL，不返回 ORM）

对齐 API_CONTRACT §4.2：
- 同维度多选 OR、跨维度 AND（PRD FR-1.2）
- 枚举非法、keyword 超 50 字符 → 40000
- page/page_size/limit 越界夹取（§1.6 / §4.2.4）
- 下架茶品：列表/计数/产地/热门/随机全部隐藏；详情 40401
"""

import random
from typing import Any

from sqlalchemy.orm import Session

from app.core.response import TeaGuideError, TeaNotFound, TeaOffShelf
from app.models.tea import Tea
from app.repositories import contribution_repo, favorite_repo, tea_repo
from app.schemas.tea import (
    CATEGORY_VALUES,
    FERMENTATION_VALUES,
    SEASON_VALUES,
    SORT_VALUES,
    CategoryCount,
    LatestTipItem,
    OriginCount,
    TeaArticleItem,
    TeaDetail,
    TeaListItem,
    TeaListResponse,
)
from app.services._common import split_csv

MAX_KEYWORD_LEN = 50
DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 50
MAX_HOT_LIMIT = 20
MAX_RELATED_LIMIT = 8
MAX_RECOMMEND_LIMIT = 8
MAX_TIPS_LIMIT = 6
FILTER_MODES = ("and", "or")
TIP_SUMMARY_LEN = 80


def _validate_enum(values: list[str], allowed: tuple[str, ...], field: str) -> None:
    invalid = [v for v in values if v not in allowed]
    if invalid:
        raise TeaGuideError(40000, f"{field} 取值非法")


def list_teas(
    db: Session,
    *,
    category: str | None,
    origin: str | None,
    season: str | None,
    fermentation: str | None,
    price_min: int | None,
    price_max: int | None,
    filter_mode: str,
    keyword: str | None,
    sort: str,
    page: int,
    page_size: int,
) -> TeaListResponse:
    """茶品列表 + 筛选 + 排序 + 分页（FR-1.1 ~ FR-1.6 + S1/S2）"""
    categories = split_csv(category)
    _validate_enum(categories, CATEGORY_VALUES, "category")

    provinces = split_csv(origin)

    seasons = split_csv(season)
    _validate_enum(seasons, SEASON_VALUES, "season")

    fermentations = split_csv(fermentation)
    _validate_enum(fermentations, FERMENTATION_VALUES, "fermentation")

    if filter_mode not in FILTER_MODES:
        raise TeaGuideError(40000, "filter_mode 取值非法")

    if price_min is not None and price_min < 0:
        raise TeaGuideError(40000, "price_min 不能为负数")
    if price_max is not None and price_max < 0:
        raise TeaGuideError(40000, "price_max 不能为负数")
    if price_min is not None and price_max is not None and price_min > price_max:
        raise TeaGuideError(40000, "price_min 不能大于 price_max")

    if sort not in SORT_VALUES:
        raise TeaGuideError(40000, "sort 取值非法")

    kw = (keyword or "").strip() or None
    if kw and len(kw) > MAX_KEYWORD_LEN:
        raise TeaGuideError(40000, "keyword 长度不能超过 50 字符")

    # 越界夹取，返回实际生效值（API_CONTRACT §1.6）
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)

    items, total = tea_repo.list_teas(
        db,
        categories=categories or None,
        provinces=provinces or None,
        seasons=seasons or None,
        fermentations=fermentations or None,
        price_min=price_min,
        price_max=price_max,
        filter_mode=filter_mode,
        keyword=kw,
        sort=sort,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return TeaListResponse(
        items=[TeaListItem.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def related_teas(db: Session, tea_id: int, *, limit: int) -> list[TeaListItem]:
    """相关推荐（S6）：limit 夹取 1-8，默认 4。"""
    tea = tea_repo.get_by_id(db, tea_id, with_tips=False)
    if not tea:
        raise TeaNotFound
    if not tea.is_active:
        raise TeaOffShelf
    limit = min(max(1, limit), MAX_RELATED_LIMIT)
    items = tea_repo.list_related(
        db, tea_id=tea.id, category=tea.category, origin=tea.origin, limit=limit
    )
    return [TeaListItem.model_validate(t) for t in items]


def latest_tips(db: Session, *, limit: int) -> list[LatestTipItem]:
    """首页最新小贴士（S7）：limit 夹取 1-6，默认 3。"""
    limit = min(max(1, limit), MAX_TIPS_LIMIT)
    rows = tea_repo.list_latest_tips(db, limit)
    result: list[LatestTipItem] = []
    for tips, tea in rows:
        summary = _pick_tip_summary(tips)
        if not summary:
            continue
        result.append(
            LatestTipItem(
                tea_id=tea.id,
                tea_name=tea.name,
                category=tea.category,
                summary=summary,
                updated_at=tips.updated_at,
            )
        )
    return result


def _pick_tip_summary(tips: Any) -> str:
    """从四项小贴士中取第一段非空文本作为首页摘要（S7）。"""
    for value in (tips.official_note, tips.suitable, tips.history, tips.misconception):
        text = (value or "").strip()
        if text:
            return text if len(text) <= TIP_SUMMARY_LEN else f"{text[:TIP_SUMMARY_LEN]}…"
    return ""


def hot_teas(db: Session, *, limit: int) -> list[TeaListItem]:
    """热门推荐（FR-2.2）：limit 夹取 1-20，默认 8"""
    limit = min(max(1, limit), MAX_HOT_LIMIT)
    items = tea_repo.list_hot(db, limit)
    return [TeaListItem.model_validate(t) for t in items]


def random_tea(db: Session, *, exclude_id: int | None) -> TeaDetail | None:
    """随机发现（FR-2.3）：无可选茶品时返回 None"""
    tea = tea_repo.get_random(db, exclude_id=exclude_id)
    return TeaDetail.model_validate(tea) if tea else None


def recommended_teas(
    db: Session,
    *,
    user_id: int | None,
    limit: int,
    exclude_id: int | None = None,
) -> list[TeaListItem]:
    """个性化推荐（S16）。

    登录且已有收藏：按收藏茶类分布加权，从偏好茶类中随机取未收藏茶品；
    未登录 / 无收藏 / 偏好茶类已全部收藏：回退完全随机。
    exclude_id 用于首页“换一款”，避免返回当前展示的茶品。
    """
    limit = min(max(1, limit), MAX_RECOMMEND_LIMIT)

    if user_id is not None:
        prefs = favorite_repo.count_categories_by_user(db, user_id)
        if prefs:
            exclude_ids = favorite_repo.list_tea_ids(db, user_id)
            if exclude_id is not None:
                exclude_ids.add(exclude_id)
            picked = _pick_by_preference(db, prefs, exclude_ids, limit)
            if picked:
                return [TeaListItem.model_validate(t) for t in picked]

    tea = tea_repo.get_random(db, exclude_id=exclude_id)
    return [TeaListItem.model_validate(tea)] if tea else []


def _pick_by_preference(
    db: Session,
    prefs: list[tuple[str, int]],
    exclude_ids: set[int],
    limit: int,
) -> list[Tea]:
    """按茶类收藏权重抽样，并在已收藏集合上继续去重。"""
    categories = [category for category, _ in prefs]
    weights = [max(1, weight) for _, weight in prefs]
    seen = set(exclude_ids)
    picked: list[Tea] = []

    # 每轮至少能排除一个已收藏茶品；上限防止极端数据下死循环
    for _ in range(limit * 4):
        if len(picked) >= limit or not categories:
            break
        category = random.choices(categories, weights=weights, k=1)[0]
        tea = tea_repo.get_random_in_category(db, category, exclude_ids=seen)
        if tea is None:
            # 该茶类可选茶品已耗尽，从抽样池移除
            index = categories.index(category)
            categories.pop(index)
            weights.pop(index)
            continue
        picked.append(tea)
        seen.add(tea.id)
    return picked


def categories(db: Session) -> list[CategoryCount]:
    """七大茶类计数（FR-2.1）：固定七项、固定顺序、无收录返回 0"""
    count_map = tea_repo.count_by_category(db)
    return [CategoryCount(category=cat, count=count_map.get(cat, 0)) for cat in CATEGORY_VALUES]


def origins(db: Session) -> list[OriginCount]:
    """产地选项（省级 + 计数，count DESC, origin ASC）"""
    return [
        OriginCount(origin=province, count=cnt) for province, cnt in tea_repo.count_by_province(db)
    ]


def get_tea(db: Session, tea_id: int) -> TeaDetail:
    """茶品详情（FR-3.1）：不存在 40400，已下架 40401；附已通过科普投稿。"""
    tea = tea_repo.get_by_id(db, tea_id)
    if not tea:
        raise TeaNotFound
    if not tea.is_active:
        raise TeaOffShelf
    data = TeaDetail.model_validate(tea)
    data.contributed_articles = [
        TeaArticleItem(
            id=item.id,
            title=(item.payload or {}).get("title"),
            content=(item.payload or {}).get("content") or "",
            contributor=username,
            created_at=item.created_at,
        )
        for item, username in contribution_repo.list_approved_articles(db, tea.id)
    ]
    return data
