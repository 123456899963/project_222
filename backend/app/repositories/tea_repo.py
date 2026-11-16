"""茶品仓储层：仅封装 SQLAlchemy 查询，不做业务判断（ARCHITECTURE §3 红线）

参数解析、枚举校验、分页夹取均在 Service 层完成；
本层只接收已解析好的结构化条件。
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, or_, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.favorite import FavoriteItem
from app.models.tea import Tea, TeaTips
from app.repositories._common import escape_like


def list_teas(
    db: Session,
    *,
    categories: list[str] | None = None,
    provinces: list[str] | None = None,
    seasons: list[str] | None = None,
    fermentations: list[str] | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    filter_mode: str = "and",
    keyword: str | None = None,
    sort: str = "newest",
    offset: int = 0,
    limit: int = 12,
) -> tuple[list[Tea], int]:
    """公开列表查询：仅 is_active=1；返回 (当前页数据, 过滤后总数)。

    筛选模式（S1）：and = 跨维度全部满足；or = 任一维度满足。
    价格（S2）：茶品价格区间与查询区间有交集即命中；未维护价格的茶品不参与价格筛选。
    """
    query = db.query(Tea).filter(Tea.is_active.is_(True))

    conditions = []
    if categories:
        conditions.append(Tea.category.in_(categories))
    if provinces:
        # 省级前缀匹配（API_CONTRACT §4.2.1：如 "浙江%"）；
        # 转义通配符，避免输入 % / _ 使筛选退化为全表
        conditions.append(
            or_(*[Tea.origin.like(f"{escape_like(p)}%", escape="\\") for p in provinces])
        )
    if seasons:
        conditions.append(Tea.season.in_(seasons))
    if fermentations:
        conditions.append(Tea.fermentation.in_(fermentations))
    if price_min is not None:
        conditions.append(Tea.price_max >= price_min)
    if price_max is not None:
        conditions.append(Tea.price_min <= price_max)

    if conditions:
        query = query.filter(or_(*conditions) if filter_mode == "or" else and_(*conditions))

    # 关键词始终 AND 叠加（S1 的 OR 仅作用于三个筛选维度）
    if keyword:
        kw = f"%{escape_like(keyword)}%"
        query = query.filter(
            or_(
                Tea.name.like(kw, escape="\\"),
                Tea.origin.like(kw, escape="\\"),
            )
        )

    # 排序必须带稳定次级键 id DESC（API_CONTRACT §1.6）
    if sort == "favorite":
        query = query.order_by(Tea.favorite_count.desc(), Tea.created_at.desc(), Tea.id.desc())
    else:
        query = query.order_by(Tea.created_at.desc(), Tea.id.desc())

    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total


def list_hot(db: Session, limit: int) -> list[Tea]:
    """热门推荐（S17）：7 天收藏数 ×3 + 累计收藏数，稳定次级键兜底。"""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    recent = (
        db.query(FavoriteItem.tea_id.label("tea_id"), func.count().label("cnt"))
        .filter(FavoriteItem.created_at >= since)
        .group_by(FavoriteItem.tea_id)
        .subquery()
    )
    score = func.coalesce(recent.c.cnt, 0) * 3 + Tea.favorite_count
    return (
        db.query(Tea)
        .outerjoin(recent, recent.c.tea_id == Tea.id)
        .filter(Tea.is_active.is_(True))
        .order_by(score.desc(), Tea.favorite_count.desc(), Tea.created_at.desc(), Tea.id.desc())
        .limit(limit)
        .all()
    )


def list_related(db: Session, *, tea_id: int, category: str, origin: str, limit: int) -> list[Tea]:
    """相关推荐（S6）：同茶类优先 → 同产地补足 → 热门兜底；排除自身与下架。"""
    same_category = case((Tea.category == category, 1), else_=0)
    same_origin = case((Tea.origin == origin, 1), else_=0)
    return (
        db.query(Tea)
        .filter(Tea.is_active.is_(True), Tea.id != tea_id)
        .order_by(
            same_category.desc(),
            same_origin.desc(),
            Tea.favorite_count.desc(),
            Tea.created_at.desc(),
            Tea.id.desc(),
        )
        .limit(limit)
        .all()
    )


def list_latest_tips(db: Session, limit: int) -> list[tuple[TeaTips, Tea]]:
    """最新小贴士（S7）：仅上架茶品，按 tea_tips.updated_at 倒序。"""
    return (
        db.query(TeaTips, Tea)
        .join(Tea, Tea.id == TeaTips.tea_id)
        .filter(Tea.is_active.is_(True))
        .order_by(TeaTips.updated_at.desc(), TeaTips.tea_id.desc())
        .limit(limit)
        .all()
    )


def get_random(
    db: Session,
    exclude_id: int | None = None,
    exclude_ids: set[int] | None = None,
) -> Tea | None:
    """随机发现：仅 is_active=1 中取 1 条（FR-2.3 完全随机）。"""
    query = db.query(Tea).filter(Tea.is_active.is_(True))
    if exclude_id is not None:
        query = query.filter(Tea.id != exclude_id)
    if exclude_ids:
        query = query.filter(Tea.id.notin_(exclude_ids))
    # 数据量 < 1000 行，ORDER BY RAND() 成本可接受
    return query.options(joinedload(Tea.tips)).order_by(text("RAND()")).limit(1).first()


def get_random_in_category(
    db: Session, category: str, *, exclude_ids: set[int] | None = None
) -> Tea | None:
    """指定茶类内随机取 1 条（S16 个性化推荐）。"""
    query = db.query(Tea).filter(Tea.is_active.is_(True), Tea.category == category)
    if exclude_ids:
        query = query.filter(Tea.id.notin_(exclude_ids))
    return query.order_by(text("RAND()")).limit(1).first()


def count_by_category(db: Session) -> dict[str, int]:
    """各茶类已上架数量（仅 is_active=1）。"""
    rows = (
        db.query(Tea.category, func.count(Tea.id))
        .filter(Tea.is_active.is_(True))
        .group_by(Tea.category)
        .all()
    )
    return dict(rows)


def count_by_province(db: Session) -> list[tuple[str, int]]:
    """各省份已上架数量：省级名由 origin 第一个空格前片段派生（API_CONTRACT §4.2.3）。

    返回按 count DESC, origin ASC 排序的 (province, count) 列表。
    """
    province_col = func.substring_index(Tea.origin, " ", 1)
    rows = (
        db.query(province_col.label("province"), func.count(Tea.id).label("cnt"))
        .filter(Tea.is_active.is_(True))
        .group_by("province")
        .order_by(text("cnt DESC"), text("province ASC"))
        .all()
    )
    return [(row.province, row.cnt) for row in rows]


def get_by_id(db: Session, tea_id: int, *, with_tips: bool = True) -> Tea | None:
    """按主键查询；with_tips=False 时跳过小贴士/图片集联表（收藏等无需详情场景）。"""
    query = db.query(Tea)
    if with_tips:
        query = query.options(
            joinedload(Tea.tips),
            joinedload(Tea.brewing_guide),
            selectinload(Tea.media_images),
        )
    return query.filter(Tea.id == tea_id).first()


def get_by_id_for_update(db: Session, tea_id: int) -> Tea | None:
    """按主键加排他锁（收藏/取消时串行化计数，避免 FK 共享锁死锁）。"""
    return db.query(Tea).filter(Tea.id == tea_id).with_for_update().first()


def lock_by_ids(db: Session, tea_ids: list[int]) -> None:
    """按 id 升序批量加锁，统一加锁顺序避免多茶品并发 copy 死锁。"""
    if not tea_ids:
        return
    db.query(Tea.id).filter(Tea.id.in_(sorted(tea_ids))).order_by(
        Tea.id.asc()
    ).with_for_update().all()
